"""Pacote Apache Beam para transformações analíticas da camada Gold (RF25)."""
from src.beam.comparador_runtimes import executar_comparacao_runtimes_beam
from src.beam.pipeline_gold import executar_pipeline_gold_beam
from src.beam.transformacoes import (
    ConsolidarMetricasCategoria,
    ExtrairChaveCategoriaMes,
    FormatarRegistroGoldCategoria,
)

__all__ = [
    "ExtrairChaveCategoriaMes",
    "ConsolidarMetricasCategoria",
    "FormatarRegistroGoldCategoria",
    "executar_pipeline_gold_beam",
    "executar_comparacao_runtimes_beam",
]
