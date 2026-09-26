"""Testes automatizados para o motor de qualidade de dados e barreira da Gold (RF31)."""
from __future__ import annotations

import pandas as pd
import pytest

from src.qualidade.avaliador import (
    avaliar_qualidade_dados,
    persistir_historico_qualidade,
)


@pytest.fixture
def datasets_validos() -> tuple[pd.DataFrame, pd.DataFrame]:
    catalogo = pd.DataFrame([
        {"conteudo_id": 1, "titulo": "Curso de Python", "categoria": "Programação"},
        {"conteudo_id": 2, "titulo": "Curso de SQL", "categoria": "Banco de Dados"},
    ])
    interacoes = pd.DataFrame([
        {
            "interacao_id": 101,
            "usuario_id": 1,
            "conteudo_id": 1,
            "tipo_interacao": "visualização",
            "data_hora": "2026-03-01T10:00:00",
            "tempo_consumido_min": 20.0,
            "percentual_conclusao": 50.0,
            "avaliacao": 4.5,
        },
        {
            "interacao_id": 102,
            "usuario_id": 2,
            "conteudo_id": 2,
            "tipo_interacao": "conclusão",
            "data_hora": "2026-03-02T11:00:00",
            "tempo_consumido_min": 60.0,
            "percentual_conclusao": 100.0,
            "avaliacao": 5.0,
        },
    ])
    return interacoes, catalogo


def test_qualidade_dados_perfeitos(datasets_validos):
    interacoes, catalogo = datasets_validos
    relatorio = avaliar_qualidade_dados(interacoes, catalogo)

    assert relatorio["bloquear_publicacao_gold"] is False
    assert relatorio["status_geral"] == "APROVADO_INTEGRAL"
    assert relatorio["metricas_chave_evolucao"]["taxa_completude_pct"] == 100.0
    assert relatorio["metricas_chave_evolucao"]["taxa_integridade_referencial_pct"] == 100.0


def test_bloqueio_por_completude(datasets_validos):
    interacoes, catalogo = datasets_validos
    # Insere nulo em campo mandatório
    interacoes.loc[0, "tipo_interacao"] = None

    relatorio = avaliar_qualidade_dados(interacoes, catalogo)
    assert relatorio["bloquear_publicacao_gold"] is True
    assert relatorio["status_geral"] == "REPROVADO_CRITICO"

    teste_q01 = next(t for t in relatorio["detalhes_testes"] if t["id_regra"] == "Q01_COMPLETUDE")
    assert teste_q01["status"] == "FALHOU"


def test_bloqueio_por_validade(datasets_validos):
    interacoes, catalogo = datasets_validos
    # Insere avaliação inválida (ex: 8.0)
    interacoes.loc[0, "avaliacao"] = 8.0

    relatorio = avaliar_qualidade_dados(interacoes, catalogo)
    assert relatorio["bloquear_publicacao_gold"] is True

    teste_q02 = next(t for t in relatorio["detalhes_testes"] if t["id_regra"] == "Q02_VALIDADE")
    assert teste_q02["status"] == "FALHOU"


def test_bloqueio_por_unicidade(datasets_validos):
    interacoes, catalogo = datasets_validos
    # Duplica ID de interação
    interacoes.loc[1, "interacao_id"] = 101

    relatorio = avaliar_qualidade_dados(interacoes, catalogo)
    assert relatorio["bloquear_publicacao_gold"] is True

    teste_q03 = next(t for t in relatorio["detalhes_testes"] if t["id_regra"] == "Q03_UNICIDADE")
    assert teste_q03["status"] == "FALHOU"


def test_aviso_por_consistencia_nao_bloqueia_gold(datasets_validos):
    interacoes, catalogo = datasets_validos
    # Conclusão com percentual < 100% (gera alerta não crítico)
    interacoes.loc[1, "percentual_conclusao"] = 80.0

    relatorio = avaliar_qualidade_dados(interacoes, catalogo)
    # Severidade AVISO não deve bloquear publicação da Gold
    assert relatorio["bloquear_publicacao_gold"] is False
    assert relatorio["status_geral"] == "APROVADO_COM_RESSALVAS"

    teste_q04 = next(t for t in relatorio["detalhes_testes"] if t["id_regra"] == "Q04_CONSISTENCIA")
    assert teste_q04["status"] == "ALERTA"


def test_bloqueio_por_integridade_referencial(datasets_validos):
    interacoes, catalogo = datasets_validos
    # Interação referenciando conteúdo inexistente (órfão)
    interacoes.loc[0, "conteudo_id"] = 9999

    relatorio = avaliar_qualidade_dados(interacoes, catalogo)
    assert relatorio["bloquear_publicacao_gold"] is True

    teste_q05 = next(t for t in relatorio["detalhes_testes"] if t["id_regra"] == "Q05_INTEGRIDADE_REFERENCIAL")
    assert teste_q05["status"] == "FALHOU"


def test_persistencia_historico_qualidade(tmp_path, datasets_validos):
    interacoes, catalogo = datasets_validos
    relatorio = avaliar_qualidade_dados(interacoes, catalogo)

    caminho_hist = tmp_path / "historico.json"
    persistir_historico_qualidade(relatorio, caminho_hist)

    assert caminho_hist.exists()
    import json
    with caminho_hist.open("r", encoding="utf-8") as f:
        dados = json.load(f)
        assert len(dados) == 1
        assert "taxa_completude_pct" in dados[0]["metricas"]
