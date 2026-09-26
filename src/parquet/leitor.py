"""Módulo de leitura otimizada de Parquet com suporte a projeção e poda de partição (RF24)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.config import caminho_absoluto


def ler_parquet_como_dataset(caminho: Path | str, particionado: bool = True) -> ds.Dataset:
    """Abre o Parquet como PyArrow Dataset para operações lazy e pushdown."""
    caminho_p = Path(caminho)
    if not caminho_p.is_absolute():
        caminho_p = caminho_absoluto(str(caminho))

    if not caminho_p.exists():
        raise FileNotFoundError(f"Caminho Parquet não encontrado: {caminho_p}")

    if particionado and caminho_p.is_dir():
        return ds.dataset(str(caminho_p), format="parquet", partitioning="hive")
    return ds.dataset(str(caminho_p), format="parquet")


def ler_parquet_interacoes(
    caminho: Path | str,
    colunas: list[str] | None = None,
    ano: int | None = None,
    mes: int | None = None,
    como_dataframe: bool = True,
) -> pd.DataFrame | Any:
    """Lê interações em Parquet com suporte a projeção de colunas e partition pruning."""
    dataset = ler_parquet_como_dataset(caminho, particionado=Path(caminho).is_dir())

    filtro = None
    if ano is not None and mes is not None:
        filtro = (ds.field("ano") == ano) & (ds.field("mes") == mes)
    elif ano is not None:
        filtro = ds.field("ano") == ano
    elif mes is not None:
        filtro = ds.field("mes") == mes

    tabela = dataset.to_table(columns=colunas, filter=filtro)

    if como_dataframe:
        return tabela.to_pandas()
    return tabela


def obter_metadados_parquet(caminho_arquivo: Path | str) -> dict[str, Any]:
    """Extrai metadados estruturais de um arquivo Parquet."""
    caminho_p = Path(caminho_arquivo)
    if not caminho_p.is_absolute():
        caminho_p = caminho_absoluto(str(caminho_arquivo))

    if caminho_p.is_dir():
        # Pega o primeiro arquivo parquet encontrado no diretório
        arquivos = list(caminho_p.rglob("*.parquet"))
        if not arquivos:
            raise ValueError(f"Nenhum arquivo Parquet encontrado no diretório: {caminho_p}")
        arquivo_alvo = arquivos[0]
    else:
        arquivo_alvo = caminho_p

    metadados = pq.read_metadata(arquivo_alvo)
    esquema = pq.read_schema(arquivo_alvo)

    return {
        "arquivo": str(arquivo_alvo),
        "total_linhas": metadados.num_rows,
        "total_colunas": metadados.num_columns,
        "num_row_groups": metadados.num_row_groups,
        "nomes_colunas": esquema.names,
        "tamanho_bytes": arquivo_alvo.stat().st_size,
    }
