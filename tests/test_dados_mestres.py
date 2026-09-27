"""Testes automatizados de Governança de Dados Mestres (RF30 - MDM)."""
from __future__ import annotations

import pytest

from scripts.demonstrar_dados_mestres import (
    calcular_similaridade,
    reconciliar_registros_conflitantes,
)


def test_calcular_similaridade_titulos() -> None:
    t1 = "Fundamentos de Banco de Dados"
    t2 = "fundamentos de banco de dados"
    assert calcular_similaridade(t1, t2) == 1.0

    t3 = "fundamentos de banco de dados para inteligencia artificial"
    t4 = "Fundamentos de Banco de Dados para Inteligência Artificial"
    assert calcular_similaridade(t3, t4) >= 0.90


def test_reconciliacao_registros_conflitantes() -> None:
    reg_a = {
        "sistema_origem": "CATALOGO_LEGADO",
        "conteudo_id": 101,
        "titulo": "curso de python basico",
        "tipo": "curso",
        "categoria": "Programação",
        "nivel": "Básico",
        "carga_horaria_min": 60,
    }
    reg_b = {
        "sistema_origem": "PORTAL_WEB",
        "conteudo_id": 905,
        "titulo": "Curso de Python Básico",
        "tipo": "Curso",
        "categoria": "Python",
        "nivel": "Iniciante",
        "carga_horaria_min": 120,
        "autor": "Guilherme",
    }

    res = reconciliar_registros_conflitantes(reg_a, reg_b)

    assert res["similaridade_detectada"] >= 0.85
    golden = res["golden_record"]
    assert golden["master_id"].startswith("MDM_CONTEUDO_")
    assert golden["titulo"] == "Curso de Python Básico"
    assert golden["nivel"] == "Básico"
    assert golden["carga_horaria_min"] == 120
    assert len(res["tabela_xref"]) == 2


def test_reconciliacao_rejeita_registros_distintos() -> None:
    reg_a = {"titulo": "Curso de Python"}
    reg_b = {"titulo": "Introdução a Redes de Computadores"}

    with pytest.raises(ValueError, match="não são correspondentes"):
        reconciliar_registros_conflitantes(reg_a, reg_b)
