"""Módulo de validação e publicação da camada Gold no PostgreSQL (RF26 e RF31)."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from src.config import caminho_absoluto, carregar_config, obter_parametros_conexao_postgres
from src.beam.pipeline_gold import executar_pipeline_gold_beam
from src.parquet.leitor import ler_parquet_interacoes
from src.qualidade.avaliador import avaliar_qualidade_dados, persistir_historico_qualidade


class FalhaQualidadeDadosCriticaError(Exception):
    """Exceção levantada quando uma regra crítica de qualidade bloqueia a publicação na Gold."""


def criar_estrutura_gold(config: dict[str, Any] | None = None) -> None:
    """Executa o script DDL da camada Gold no PostgreSQL."""
    if config is None:
        config = carregar_config()

    caminho_script = caminho_absoluto("sql/camada_gold.sql")
    sql_script = caminho_script.read_text(encoding="utf-8")

    params = obter_parametros_conexao_postgres(config)
    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_script)
        conn.commit()


def _calcular_desempenho_conteudos(
    interacoes_df: pd.DataFrame,
    catalogo_df: pd.DataFrame,
    lote_id: str,
    data_carga: str,
) -> list[dict[str, Any]]:
    """Calcula métricas agregadas por conteúdo para a tabela gold.desempenho_conteudos."""
    agrupado = interacoes_df.groupby("conteudo_id")

    metricas_por_conteudo = {}
    for cid, grupo in agrupado:
        vis = (grupo["tipo_interacao"] == "visualização").sum()
        ini = (grupo["tipo_interacao"] == "início").sum()
        conc = (grupo["tipo_interacao"] == "conclusão").sum()
        curt = (grupo["tipo_interacao"] == "curtida").sum()
        taxa = round((conc / ini) * 100.0, 2) if ini > 0 else 0.0
        tempo = round(float(grupo["tempo_consumido_min"].sum()), 2)
        aval_series = grupo["avaliacao"].dropna()
        aval_media = round(float(aval_series.mean()), 2) if not aval_series.empty else None

        metricas_por_conteudo[cid] = {
            "total_visualizacoes": int(vis),
            "total_inicios": int(ini),
            "total_conclusoes": int(conc),
            "total_curtidas": int(curt),
            "taxa_conclusao_pct": taxa,
            "tempo_total_min": tempo,
            "avaliacao_media": aval_media,
        }

    linhas_gold_conteudos = []
    for _, row in catalogo_df.iterrows():
        cid = int(row["conteudo_id"])
        mets = metricas_por_conteudo.get(cid, {
            "total_visualizacoes": 0,
            "total_inicios": 0,
            "total_conclusoes": 0,
            "total_curtidas": 0,
            "taxa_conclusao_pct": 0.0,
            "tempo_total_min": 0.0,
            "avaliacao_media": None,
        })
        linhas_gold_conteudos.append({
            "conteudo_id": cid,
            "titulo": str(row["titulo"]),
            "tipo": str(row["tipo"]),
            "categoria": str(row["categoria"]),
            "nivel": str(row["nivel"]),
            **mets,
            "_data_carga_gold": data_carga,
            "_lote_processamento": lote_id,
        })
    return linhas_gold_conteudos


def publicar_camada_gold(
    config: dict[str, Any] | None = None,
    forcar_sem_qualidade: bool = False,
    logger: Any = None,
) -> dict[str, Any]:
    """Orquestra a barreira de qualidade, pipeline Beam e carga idempotente na Gold."""
    inicio = perf_counter()
    if config is None:
        config = carregar_config()

    if logger:
        logger.info("Iniciando processo de publicação da camada Gold (RF26)...")

    # 1. Carrega dados de entrada para a barreira de qualidade
    dir_parquet_interacoes = caminho_absoluto(config.get("parquet", {}).get("diretorio_saida", "dados/parquet")) / "interacoes" / "particionado"
    origem_catalogo = caminho_absoluto(config.get("dados", {}).get("processados", {}).get("catalogo", "dados/processados/catalogo_processado.csv"))

    interacoes_df = ler_parquet_interacoes(dir_parquet_interacoes)
    catalogo_df = pd.read_csv(origem_catalogo)

    # 2. Executa a Barreira de Qualidade de Dados (RF31)
    relatorio_qualidade = avaliar_qualidade_dados(interacoes_df, catalogo_df, logger=logger)
    persistir_historico_qualidade(relatorio_qualidade)

    if relatorio_qualidade["bloquear_publicacao_gold"] and not forcar_sem_qualidade:
        motivo = (
            f"Publicação da Gold abortada devido a falhas críticas de qualidade: {relatorio_qualidade['status_geral']}. "
            f"Consulte documentacao/qualidade_dados.md para detalhes."
        )
        if logger:
            logger.error(motivo)
        raise FalhaQualidadeDadosCriticaError(motivo)

    # 3. Garante estrutura no PostgreSQL
    criar_estrutura_gold(config)

    # 4. Executa o Pipeline Apache Beam para obter KPIs mensais por categoria
    resultado_beam = executar_pipeline_gold_beam(config, runner="DirectRunner", logger=logger)
    caminho_parquet_kpis = Path(resultado_beam["caminho_parquet_saida"])

    # Lê os KPIs gerados pelo Beam do Parquet
    df_kpis = pd.read_parquet(caminho_parquet_kpis)
    registros_kpis = df_kpis.to_dict(orient="records")

    # 5. Calcula desempenho agregado por conteúdo
    registros_conteudos = _calcular_desempenho_conteudos(
        interacoes_df,
        catalogo_df,
        lote_id=resultado_beam["lote_id"],
        data_carga=resultado_beam["data_execucao"],
    )

    # 6. Carga idempotente no PostgreSQL
    params = obter_parametros_conexao_postgres(config)
    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            # 6.1 Carga gold.kpis_mensais_categoria
            sql_upsert_kpis = """
            INSERT INTO gold.kpis_mensais_categoria (
                ano, mes, categoria, total_interacoes, usuarios_ativos,
                total_visualizacoes, total_inicios, total_conclusoes, total_curtidas,
                taxa_conclusao_pct, tempo_total_consumido_min, tempo_medio_min,
                avaliacao_media, _data_carga_gold, _lote_processamento
            ) VALUES %s
            ON CONFLICT (ano, mes, categoria) DO UPDATE SET
                total_interacoes = EXCLUDED.total_interacoes,
                usuarios_ativos = EXCLUDED.usuarios_ativos,
                total_visualizacoes = EXCLUDED.total_visualizacoes,
                total_inicios = EXCLUDED.total_inicios,
                total_conclusoes = EXCLUDED.total_conclusoes,
                total_curtidas = EXCLUDED.total_curtidas,
                taxa_conclusao_pct = EXCLUDED.taxa_conclusao_pct,
                tempo_total_consumido_min = EXCLUDED.tempo_total_consumido_min,
                tempo_medio_min = EXCLUDED.tempo_medio_min,
                avaliacao_media = EXCLUDED.avaliacao_media,
                _data_carga_gold = EXCLUDED._data_carga_gold,
                _lote_processamento = EXCLUDED._lote_processamento;
            """
            valores_kpis = [
                (
                    int(r["ano"]),
                    int(r["mes"]),
                    str(r["categoria"]),
                    int(r["total_interacoes"]),
                    int(r["usuarios_ativos"]),
                    int(r["total_visualizacoes"]),
                    int(r["total_inicios"]),
                    int(r["total_conclusoes"]),
                    int(r["total_curtidas"]),
                    float(r["taxa_conclusao_pct"]),
                    float(r["tempo_total_consumido_min"]),
                    float(r["tempo_medio_min"]),
                    float(r["avaliacao_media"]) if pd.notnull(r.get("avaliacao_media")) else None,
                    r["_data_carga_gold"],
                    r["_lote_processamento"],
                )
                for r in registros_kpis
            ]
            execute_values(cur, sql_upsert_kpis, valores_kpis)

            # 6.2 Carga gold.desempenho_conteudos
            sql_upsert_conteudos = """
            INSERT INTO gold.desempenho_conteudos (
                conteudo_id, titulo, tipo, categoria, nivel,
                total_visualizacoes, total_inicios, total_conclusoes, total_curtidas,
                taxa_conclusao_pct, tempo_total_min, avaliacao_media,
                _data_carga_gold, _lote_processamento
            ) VALUES %s
            ON CONFLICT (conteudo_id) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo,
                categoria = EXCLUDED.categoria,
                nivel = EXCLUDED.nivel,
                total_visualizacoes = EXCLUDED.total_visualizacoes,
                total_inicios = EXCLUDED.total_inicios,
                total_conclusoes = EXCLUDED.total_conclusoes,
                total_curtidas = EXCLUDED.total_curtidas,
                taxa_conclusao_pct = EXCLUDED.taxa_conclusao_pct,
                tempo_total_min = EXCLUDED.tempo_total_min,
                avaliacao_media = EXCLUDED.avaliacao_media,
                _data_carga_gold = EXCLUDED._data_carga_gold,
                _lote_processamento = EXCLUDED._lote_processamento;
            """
            valores_conteudos = [
                (
                    int(r["conteudo_id"]),
                    str(r["titulo"]),
                    str(r["tipo"]),
                    str(r["categoria"]),
                    str(r["nivel"]),
                    int(r["total_visualizacoes"]),
                    int(r["total_inicios"]),
                    int(r["total_conclusoes"]),
                    int(r["total_curtidas"]),
                    float(r["taxa_conclusao_pct"]),
                    float(r["tempo_total_min"]),
                    float(r["avaliacao_media"]) if pd.notnull(r.get("avaliacao_media")) else None,
                    r["_data_carga_gold"],
                    r["_lote_processamento"],
                )
                for r in registros_conteudos
            ]
            execute_values(cur, sql_upsert_conteudos, valores_conteudos)
        conn.commit()

    duracao_seg = round(perf_counter() - inicio, 4)

    resultado = {
        "status": "PUBLICADO_COM_SUCESSO",
        "qualidade_status": relatorio_qualidade["status_geral"],
        "total_kpis_mensais_carregados": len(valores_kpis),
        "total_conteudos_carregados": len(valores_conteudos),
        "duracao_segundos": duracao_seg,
        "lote_id": resultado_beam["lote_id"],
    }

    if logger:
        logger.info(
            "Camada Gold publicada com sucesso no PostgreSQL | kpis=%d | conteudos=%d | duracao=%.4fs",
            resultado["total_kpis_mensais_carregados"],
            resultado["total_conteudos_carregados"],
            duracao_seg,
        )

    return resultado
