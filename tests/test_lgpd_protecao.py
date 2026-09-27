"""Testes unitários automatizados para as técnicas de proteção da LGPD (RF33)."""
import os
import pytest
from src.lgpd.protecao import (
    mascarar_nome,
    pseudonimizar_id,
    gerar_hash_salted,
    verificar_hash,
)

def test_mascaramento_nome_padrao():
    assert mascarar_nome("João Silva") == "J*** S****"
    assert mascarar_nome("Carlos Eduardo Santos") == "C***** E****** S*****"
    assert mascarar_nome("A B") == "* *"
    assert mascarar_nome("Li") == "L*"

def test_mascaramento_nome_nulo_ou_vazio():
    assert mascarar_nome(None) == "[ANÔNIMO]"
    assert mascarar_nome("") == "[ANÔNIMO]"
    assert mascarar_nome("   ") == "[ANÔNIMO]"

def test_pseudonimizacao_consistente_para_joins():
    # O mesmo ID deve produzir sempre o mesmo identificador determinístico
    id1 = pseudonimizar_id(1001)
    id2 = pseudonimizar_id(1001)
    id3 = pseudonimizar_id(1002)

    assert id1 == id2
    assert id1 != id3
    assert id1.startswith("USR_PSEUDO_")

def test_hash_salted_com_salt_customizado():
    salt_a = "segredo_salt_alpha"
    salt_b = "segredo_salt_beta"
    
    hash_a1 = gerar_hash_salted(1050, salt_override=salt_a)
    hash_a2 = gerar_hash_salted(1050, salt_override=salt_a)
    hash_b = gerar_hash_salted(1050, salt_override=salt_b)

    # Determinístico com o mesmo salt
    assert hash_a1 == hash_a2
    assert len(hash_a1) == 64
    
    # Diferente se o salt mudar (proteção contra rainbow table)
    assert hash_a1 != hash_b
    
    # Verificação de hash
    assert verificar_hash(1050, hash_a1, salt_override=salt_a) is True
    assert verificar_hash(1050, hash_a1, salt_override=salt_b) is False
    assert verificar_hash(9999, hash_a1, salt_override=salt_a) is False

def test_hash_salted_com_variavel_ambiente(monkeypatch):
    monkeypatch.setenv("HASH_SALT", "meu_salt_super_secreto_2026")
    h = gerar_hash_salted("estudante_teste")
    assert len(h) == 64
    assert verificar_hash("estudante_teste", h) is True
