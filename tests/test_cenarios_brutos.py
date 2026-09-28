"""Testes automatizados que validam os cenários de teste criados em dados/brutos/cenarios_de_teste/."""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import pytest

from src.lgpd.protecao import mascarar_nome, pseudonimizar_id, gerar_hash_salted
from src.qualidade.avaliador import avaliar_qualidade_dados


DIR_CENARIOS = Path(__file__).resolve().parent.parent / "dados" / "brutos" / "cenarios_de_teste"


def test_cenarios_arquivos_existem():
    assert (DIR_CENARIOS / "catalogo_cenarios.csv").exists()
    assert (DIR_CENARIOS / "interacoes_cenarios.json").exists()
    assert (DIR_CENARIOS / "comentarios_cenarios.json").exists()
    assert (DIR_CENARIOS / "README.md").exists()


def test_cenarios_mascaramento_lgpd():
    df_cat = pd.read_csv(DIR_CENARIOS / "catalogo_cenarios.csv")
    autores_mascarados = [mascarar_nome(a) for a in df_cat["autor"]]
    
    assert "G****** M****** B*****" in autores_mascarados
    assert "A** B****** C****" in autores_mascarados


def test_cenarios_pseudonimizacao_e_hashing_lgpd(monkeypatch):
    monkeypatch.setenv("HASH_SALT", "segredo_teste_2026")
    
    with open(DIR_CENARIOS / "interacoes_cenarios.json", "r", encoding="utf-8") as f:
        interacoes = json.load(f)
    
    item_lgpd = next(i for i in interacoes if i.get("cenario", "").startswith("Caminho Feliz (Inicio e Demonstracao LGPD"))
    uid = item_lgpd["usuario_id"]
    
    pseudo = pseudonimizar_id(uid)
    assert pseudo.startswith("USR_PSEUDO_")
    
    hash_salt = gerar_hash_salted(uid)
    assert len(hash_salt) == 64


def test_cenarios_motor_qualidade_detecta_todas_as_falhas():
    df_cat = pd.read_csv(DIR_CENARIOS / "catalogo_cenarios.csv")
    with open(DIR_CENARIOS / "interacoes_cenarios.json", "r", encoding="utf-8") as f:
        interacoes = json.load(f)
    
    df_interacoes = pd.DataFrame(interacoes)
    
    # Avaliando qualidade com o motor oficial (RF31)
    relatorio = avaliar_qualidade_dados(df_interacoes, df_cat)
    
    # Deve identificar que há falhas críticas e bloquear a publicação da Gold
    assert relatorio["bloquear_publicacao_gold"] is True
    assert relatorio["status_geral"] == "REPROVADO_CRITICO"
    
    detalhes_por_id = {t["id_regra"]: t for t in relatorio["detalhes_testes"]}
    
    # Q01 Completude: falhou devido a usuario_id nulo
    assert detalhes_por_id["Q01_COMPLETUDE"]["status"] == "FALHOU"
    
    # Q02 Validade: falhou devido a nota 7.5 e conclusao 150%
    assert detalhes_por_id["Q02_VALIDADE"]["status"] == "FALHOU"
    
    # Q03 Unicidade: falhou devido a interacao_id 101 repetido
    assert detalhes_por_id["Q03_UNICIDADE"]["status"] == "FALHOU"
    
    # Q04 Consistência: gerou ALERTA devido a tipo conclusao com 25% de progresso
    assert detalhes_por_id["Q04_CONSISTENCIA"]["status"] == "ALERTA"
    
    # Q05 Integridade Referencial: falhou devido a conteudo_id 99999 orfao
    assert detalhes_por_id["Q05_INTEGRIDADE_REFERENCIAL"]["status"] == "FALHOU"
