"""Testes automatizados para o pipeline Apache Beam e transformações analíticas (RF25)."""
from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from src.beam.comparador_runtimes import executar_comparacao_runtimes_beam
from src.beam.pipeline_gold import executar_pipeline_gold_beam
from src.beam.transformacoes import ConsolidarMetricasCategoria


def test_consolidar_metricas_categoria_unitario():
    fn = ConsolidarMetricasCategoria()
    acc = fn.create_accumulator()

    # Evento 1: Visualização
    acc = fn.add_input(acc, {
        "usuario_id": 1,
        "tipo_interacao": "visualização",
        "tempo_consumido_min": 10.0,
        "avaliacao": None,
    })

    # Evento 2: Início
    acc = fn.add_input(acc, {
        "usuario_id": 1,
        "tipo_interacao": "início",
        "tempo_consumido_min": 5.0,
        "avaliacao": None,
    })

    # Evento 3: Conclusão
    acc = fn.add_input(acc, {
        "usuario_id": 2,
        "tipo_interacao": "conclusão",
        "tempo_consumido_min": 30.0,
        "avaliacao": 5.0,
    })

    res = fn.extract_output(acc)
    assert res["total_interacoes"] == 3
    assert res["usuarios_ativos"] == 2
    assert res["total_visualizacoes"] == 1
    assert res["total_inicios"] == 1
    assert res["total_conclusoes"] == 1
    assert res["taxa_conclusao_pct"] == 100.0
    assert res["tempo_total_consumido_min"] == 45.0
    assert res["tempo_medio_min"] == 15.0
    assert res["avaliacao_media"] == 5.0


def test_pipeline_beam_directrunner():
    res = executar_pipeline_gold_beam(runner="DirectRunner", lote_id="LOTE_TESTE_BEAM_01")
    assert res["runner"] == "DirectRunner"
    assert res["registros_lidos"] == 1000
    assert res["registros_gold_gerados"] > 0
    assert res["duracao_segundos"] > 0
    assert Path(res["caminho_parquet_saida"]).exists()


def test_leitura_arquivo_parquet_gold():
    caminho_gold = Path("dados/parquet/gold/kpis_mensais_categoria.parquet").resolve()
    assert caminho_gold.exists()

    tabela = pq.read_table(caminho_gold)
    assert tabela.num_rows > 0
    colunas_esperadas = {
        "ano",
        "mes",
        "categoria",
        "total_interacoes",
        "usuarios_ativos",
        "total_visualizacoes",
        "total_inicios",
        "total_conclusoes",
        "total_curtidas",
        "taxa_conclusao_pct",
        "tempo_total_consumido_min",
        "tempo_medio_min",
        "avaliacao_media",
        "_data_carga_gold",
        "_lote_processamento",
    }
    assert colunas_esperadas.issubset(set(tabela.schema.names))


def test_comparador_runtimes_beam():
    relatorio = executar_comparacao_runtimes_beam(tentar_spark=True)
    assert "direct_runner" in relatorio
    assert relatorio["direct_runner"]["status"] == "SUCESSO"
    assert "spark_runner" in relatorio
    assert "diagnostico_infraestrutura" in relatorio

    # Valida arquivos gerados
    assert Path("dados/processados/resultado_execucao_beam.json").exists()
    assert Path("documentacao/execucao_beam_spark.md").exists()
