"""Módulo de qualidade de dados com 5 dimensões e barreira de bloqueio (RF31)."""
from src.qualidade.avaliador import (
    avaliar_qualidade_dados,
    persistir_historico_qualidade,
)
from src.qualidade.regras import REGRAS_QUALIDADE, AcaoFalha, RegraQualidade, Severidade

__all__ = [
    "REGRAS_QUALIDADE",
    "Severidade",
    "AcaoFalha",
    "RegraQualidade",
    "avaliar_qualidade_dados",
    "persistir_historico_qualidade",
]
