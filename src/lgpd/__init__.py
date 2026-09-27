"""Módulo de proteção de dados e conformidade LGPD."""
from src.lgpd.protecao import (
    mascarar_nome,
    pseudonimizar_id,
    gerar_hash_salted,
    verificar_hash,
)

__all__ = [
    "mascarar_nome",
    "pseudonimizar_id",
    "gerar_hash_salted",
    "verificar_hash",
]
