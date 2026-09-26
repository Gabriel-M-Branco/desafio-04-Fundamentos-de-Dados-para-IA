"""Pacote de exportação, leitura e benchmark em Parquet (RF24)."""
from src.parquet.benchmark import executar_benchmark_comparativo
from src.parquet.esquema import ESQUEMA_INTERACOES_PARQUET, obter_esquema_interacoes
from src.parquet.exportador import exportar_interacoes_parquet
from src.parquet.leitor import (
    ler_parquet_como_dataset,
    ler_parquet_interacoes,
    obter_metadados_parquet,
)

__all__ = [
    "ESQUEMA_INTERACOES_PARQUET",
    "obter_esquema_interacoes",
    "exportar_interacoes_parquet",
    "ler_parquet_como_dataset",
    "ler_parquet_interacoes",
    "obter_metadados_parquet",
    "executar_benchmark_comparativo",
]
