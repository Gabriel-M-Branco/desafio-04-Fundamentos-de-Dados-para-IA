"""Testes automatizados para exportação, particionamento e leitura Parquet (RF24)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pyarrow as pa
import pytest

from src.parquet.benchmark import executar_benchmark_comparativo
from src.parquet.esquema import ESQUEMA_INTERACOES_PARQUET, obter_esquema_interacoes
from src.parquet.exportador import (
    carregar_dados_silver_interacoes,
    exportar_interacoes_parquet,
    preparar_tabela_interacoes_arrow,
)
from src.parquet.leitor import (
    ler_parquet_como_dataset,
    ler_parquet_interacoes,
    obter_metadados_parquet,
)


@pytest.fixture
def amostra_interacoes() -> list[dict]:
    return [
        {
            "interacao_id": 1,
            "usuario_id": 10,
            "conteudo_id": 100,
            "tipo_interacao": "visualização",
            "data_hora": "2026-03-15T14:30:00",
            "tempo_consumido_min": 15.5,
            "percentual_conclusao": 50.0,
            "avaliacao": 4.5,
        },
        {
            "interacao_id": 2,
            "usuario_id": 20,
            "conteudo_id": 200,
            "tipo_interacao": "conclusão",
            "data_hora": "2026-04-20T18:00:00",
            "tempo_consumido_min": 45.0,
            "percentual_conclusao": 100.0,
            "avaliacao": None,
        },
    ]


def test_esquema_arrow():
    esquema = obter_esquema_interacoes()
    assert isinstance(esquema, pa.Schema)
    nomes_esperados = {
        "interacao_id",
        "usuario_id",
        "conteudo_id",
        "tipo_interacao",
        "data_hora",
        "tempo_consumido_min",
        "percentual_conclusao",
        "avaliacao",
        "_data_ingestao",
        "_lote_id",
        "_origem",
        "ano",
        "mes",
    }
    assert set(esquema.names) == nomes_esperados


def test_preparar_tabela_interacoes_arrow(amostra_interacoes):
    tabela = preparar_tabela_interacoes_arrow(amostra_interacoes, lote_id="LOTE_TESTE_01")
    assert tabela.num_rows == 2
    assert tabela.column("_lote_id")[0].as_py() == "LOTE_TESTE_01"
    assert tabela.column("_origem")[0].as_py() == "silver/interacoes"
    assert tabela.column("ano")[0].as_py() == 2026
    assert tabela.column("mes")[0].as_py() == 3
    assert tabela.column("ano")[1].as_py() == 2026
    assert tabela.column("mes")[1].as_py() == 4


def test_exportacao_e_leitura_particionada(tmp_path, amostra_interacoes):
    origem_temp = tmp_path / "interacoes_mock.json"
    import json
    origem_temp.write_text(json.dumps(amostra_interacoes), encoding="utf-8")

    cfg = {
        "parquet": {
            "origem_silver_interacoes": str(origem_temp),
            "diretorio_saida": str(tmp_path / "parquet"),
            "compressao": "snappy",
            "particionar_por": ["ano", "mes"],
        }
    }

    resultado = exportar_interacoes_parquet(cfg, particionado=True, lote_id="LOTE_TESTE_02")
    assert resultado["total_registros"] == 2
    assert resultado["total_arquivos"] >= 2  # Pelo menos duas partições (mes=3 e mes=4)

    # Valida estrutura de diretórios Hive
    dir_part = Path(resultado["caminho_destino"])
    particoes_ano = list(dir_part.glob("ano=*"))
    assert len(particoes_ano) >= 1

    # Leitura total
    df_lido = ler_parquet_interacoes(dir_part)
    assert len(df_lido) == 2

    # Leitura com filtro de partição (apenas mes=3)
    df_mes3 = ler_parquet_interacoes(dir_part, mes=3)
    assert len(df_mes3) == 1
    assert df_mes3["interacao_id"].iloc[0] == 1


def test_leitura_projecao_colunas(tmp_path, amostra_interacoes):
    origem_temp = tmp_path / "interacoes_mock.json"
    import json
    origem_temp.write_text(json.dumps(amostra_interacoes), encoding="utf-8")

    cfg = {
        "parquet": {
            "origem_silver_interacoes": str(origem_temp),
            "diretorio_saida": str(tmp_path / "parquet"),
            "compressao": "snappy",
        }
    }

    resultado = exportar_interacoes_parquet(cfg, particionado=False)
    caminho_arquivo = resultado["caminho_destino"]

    # Lê apenas duas colunas
    df_proj = ler_parquet_interacoes(caminho_arquivo, colunas=["usuario_id", "tipo_interacao"])
    assert list(df_proj.columns) == ["usuario_id", "tipo_interacao"]
    assert len(df_proj) == 2


def test_benchmark_executa_e_gera_arquivos(tmp_path):
    origem_real = Path("dados/processados/interacoes_processadas.json").resolve()
    assert origem_real.exists(), "Base real de interações deve existir para o benchmark"

    cfg = {
        "parquet": {
            "origem_silver_interacoes": str(origem_real),
            "benchmark_saida": str(tmp_path / "benchmark.json"),
            "benchmark_doc": str(tmp_path / "benchmark.md"),
        }
    }

    relatorio = executar_benchmark_comparativo(config=cfg, repeticoes=2)
    assert "metricas" in relatorio
    assert "parquet_consolidado" in relatorio["metricas"]
    assert "csv" in relatorio["metricas"]
    assert "json" in relatorio["metricas"]

    # Confirma que os arquivos foram gerados no disco
    assert (tmp_path / "benchmark.json").exists()
    assert (tmp_path / "benchmark.md").exists()
