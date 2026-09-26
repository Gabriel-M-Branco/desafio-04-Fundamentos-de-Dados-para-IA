"""Pacote da camada Gold para persistência analítica e barreira de qualidade (RF26)."""
from src.gold.publicador import (
    FalhaQualidadeDadosCriticaError,
    criar_estrutura_gold,
    publicar_camada_gold,
)

__all__ = [
    "criar_estrutura_gold",
    "publicar_camada_gold",
    "FalhaQualidadeDadosCriticaError",
]
