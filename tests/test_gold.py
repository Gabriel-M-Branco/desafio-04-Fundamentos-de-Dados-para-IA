"""Testes automatizados para publicação, idempotência e views da camada Gold (RF26 e RF31)."""
from __future__ import annotations

import psycopg2
import pytest

from src.config import carregar_config, obter_parametros_conexao_postgres
from src.gold.publicador import (
    FalhaQualidadeDadosCriticaError,
    criar_estrutura_gold,
    publicar_camada_gold,
)


@pytest.fixture(scope="module")
def config_teste():
    return carregar_config()


def test_criar_estrutura_gold(config_teste):
    criar_estrutura_gold(config_teste)

    params = obter_parametros_conexao_postgres(config_teste)
    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            # Verifica schema gold
            cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'gold';")
            assert cur.fetchone() is not None

            # Verifica tabelas
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'gold' AND table_name IN ('kpis_mensais_categoria', 'desempenho_conteudos');
            """)
            tabelas = [row[0] for row in cur.fetchall()]
            assert "kpis_mensais_categoria" in tabelas
            assert "desempenho_conteudos" in tabelas


def test_publicar_camada_gold_sucesso(config_teste):
    resultado = publicar_camada_gold(config_teste)
    assert resultado["status"] == "PUBLICADO_COM_SUCESSO"
    assert resultado["total_kpis_mensais_carregados"] > 0
    assert resultado["total_conteudos_carregados"] > 0

    params = obter_parametros_conexao_postgres(config_teste)
    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM gold.kpis_mensais_categoria;")
            total_kpis = cur.fetchone()[0]
            assert total_kpis > 0

            cur.execute("SELECT COUNT(*) FROM gold.desempenho_conteudos;")
            total_conteudos = cur.fetchone()[0]
            assert total_conteudos == 1000


def test_views_gold_consultaveis(config_teste):
    params = obter_parametros_conexao_postgres(config_teste)
    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            # Consulta view executiva de KPIs temporais
            cur.execute("SELECT data_referencia, categoria, taxa_conclusao_pct FROM gold.vw_kpis_executivos LIMIT 5;")
            linhas_kpis = cur.fetchall()
            assert len(linhas_kpis) > 0
            assert linhas_kpis[0][0] is not None  # data_referencia válida para série temporal

            # Consulta view de ranking de conteúdos
            cur.execute("SELECT conteudo_id, titulo, ranking_categoria FROM gold.vw_ranking_conteudos_engajamento LIMIT 5;")
            linhas_ranking = cur.fetchall()
            assert len(linhas_ranking) > 0


def test_idempotencia_carga_gold(config_teste):
    # Segunda execução consecutiva
    res2 = publicar_camada_gold(config_teste)
    assert res2["status"] == "PUBLICADO_COM_SUCESSO"

    params = obter_parametros_conexao_postgres(config_teste)
    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM gold.desempenho_conteudos;")
            total_conteudos = cur.fetchone()[0]
            # Não pode ter duplicado (deve continuar sendo exatamente 1000)
            assert total_conteudos == 1000


def test_bloqueio_publicacao_gold_em_falha_critica(tmp_path, config_teste, monkeypatch):
    # Simula diretório com dados corrompidos (ex: campo mandatório nulo)
    from src.parquet.exportador import exportar_interacoes_parquet
    import json

    dados_invalidos = [
        {
            "interacao_id": 999,
            "usuario_id": 1,
            "conteudo_id": 1,
            "tipo_interacao": None,  # NULO CRÍTICO
            "data_hora": "2026-03-01T10:00:00",
            "tempo_consumido_min": 10.0,
            "percentual_conclusao": 50.0,
            "avaliacao": 4.0,
        }
    ]
    origem_mock = tmp_path / "mock_invalid.json"
    origem_mock.write_text(json.dumps(dados_invalidos), encoding="utf-8")

    cfg_mock = dict(config_teste)
    cfg_mock["parquet"] = dict(config_teste.get("parquet", {}))
    cfg_mock["parquet"]["origem_silver_interacoes"] = str(origem_mock)
    cfg_mock["parquet"]["diretorio_saida"] = str(tmp_path / "parquet_mock")

    # Exporta o parquet corrompido
    exportar_interacoes_parquet(cfg_mock, particionado=True)

    # Tenta publicar na Gold -> DEVE LEVANTAR FalhaQualidadeDadosCriticaError
    with pytest.raises(FalhaQualidadeDadosCriticaError) as exc_info:
        publicar_camada_gold(cfg_mock)

    assert "falhas críticas de qualidade" in str(exc_info.value)
