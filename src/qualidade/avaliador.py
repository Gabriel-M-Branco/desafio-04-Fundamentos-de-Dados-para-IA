"""Motor avaliador de qualidade de dados com bloqueio de publicação da Gold (RF31)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

import pandas as pd

from src.config import agora_iso as obter_agora_iso, agora_projeto, caminho_absoluto, carregar_config
from src.qualidade.regras import REGRAS_QUALIDADE, Severidade


def avaliar_qualidade_dados(
    interacoes_df: pd.DataFrame,
    catalogo_df: pd.DataFrame,
    lote_id: str | None = None,
    logger: Any = None,
) -> dict[str, Any]:
    """Aplica os 5 testes de qualidade nas dimensões exigidas pelo RF31."""
    lote = lote_id or f"LOTE_DQ_{agora_projeto().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    agora_iso = obter_agora_iso()
    total_interacoes = len(interacoes_df)
    total_catalogo = len(catalogo_df)

    if total_interacoes == 0 or total_catalogo == 0:
        raise ValueError("Os conjuntos de dados para avaliação de qualidade não podem estar vazios.")

    resultados_testes = []
    bloquear_publicacao = False

    # -------------------------------------------------------------------------
    # 1. COMPLETUDE (Q01)
    # -------------------------------------------------------------------------
    candidatas_int = ["usuario_id", "conteudo_id", "tipo_interacao", "data_hora"]
    if "interacao_id" in interacoes_df.columns:
        candidatas_int.insert(0, "interacao_id")
    colunas_obrigatorias_int = candidatas_int
    nulos_interacoes = interacoes_df[colunas_obrigatorias_int].isnull().sum().sum()
    nulos_catalogo = catalogo_df[["conteudo_id", "titulo", "categoria"]].isnull().sum().sum()
    total_campos_verificados = (len(colunas_obrigatorias_int) * total_interacoes) + (3 * total_catalogo)
    taxa_completude_pct = round((1.0 - ((nulos_interacoes + nulos_catalogo) / total_campos_verificados)) * 100.0, 4)
    passou_q01 = (nulos_interacoes + nulos_catalogo) == 0

    if not passou_q01:
        bloquear_publicacao = True

    resultados_testes.append({
        "id_regra": "Q01_COMPLETUDE",
        "nome": REGRAS_QUALIDADE["Q01_COMPLETUDE"].nome,
        "dimensao": "Completude",
        "severidade": REGRAS_QUALIDADE["Q01_COMPLETUDE"].severidade.value,
        "status": "PASSOU" if passou_q01 else "FALHOU",
        "metrica_valor": taxa_completude_pct,
        "metrica_descricao": f"Taxa de completude de atributos: {taxa_completude_pct}% (nulos={nulos_interacoes + nulos_catalogo})",
        "limite_esperado": "100.0%",
        "bloqueante": True,
    })

    # -------------------------------------------------------------------------
    # 2. VALIDADE (Q02)
    # -------------------------------------------------------------------------
    tipos_validos = {"visualização", "início", "conclusão", "curtida", "avaliação", "compartilhamento"}
    tipos_invalidos = (~interacoes_df["tipo_interacao"].isin(tipos_validos)).sum()

    aval_mask = interacoes_df["avaliacao"].notnull()
    aval_fora = (~interacoes_df.loc[aval_mask, "avaliacao"].between(1.0, 5.0)).sum()

    conclusao_fora = (~interacoes_df["percentual_conclusao"].between(0.0, 100.0)).sum()
    tempo_negativo = (interacoes_df["tempo_consumido_min"] < 0.0).sum()

    total_invalidezes = int(tipos_invalidos + aval_fora + conclusao_fora + tempo_negativo)
    taxa_validade_pct = round((1.0 - (total_invalidezes / (total_interacoes * 4))) * 100.0, 4)
    passou_q02 = total_invalidezes == 0

    if not passou_q02:
        bloquear_publicacao = True

    resultados_testes.append({
        "id_regra": "Q02_VALIDADE",
        "nome": REGRAS_QUALIDADE["Q02_VALIDADE"].nome,
        "dimensao": "Validade",
        "severidade": REGRAS_QUALIDADE["Q02_VALIDADE"].severidade.value,
        "status": "PASSOU" if passou_q02 else "FALHOU",
        "metrica_valor": taxa_validade_pct,
        "metrica_descricao": f"Taxa de validade de domínios: {taxa_validade_pct}% (invalidezes={total_invalidezes})",
        "limite_esperado": "100.0%",
        "bloqueante": True,
    })

    # -------------------------------------------------------------------------
    # 3. UNICIDADE (Q03)
    # -------------------------------------------------------------------------
    dup_interacoes = interacoes_df["interacao_id"].duplicated().sum()
    dup_catalogo = catalogo_df["conteudo_id"].duplicated().sum()
    total_duplicatas = int(dup_interacoes + dup_catalogo)
    taxa_unicidade_pct = round((1.0 - (total_duplicatas / (total_interacoes + total_catalogo))) * 100.0, 4)
    passou_q03 = total_duplicatas == 0

    if not passou_q03:
        bloquear_publicacao = True

    resultados_testes.append({
        "id_regra": "Q03_UNICIDADE",
        "nome": REGRAS_QUALIDADE["Q03_UNICIDADE"].nome,
        "dimensao": "Unicidade",
        "severidade": REGRAS_QUALIDADE["Q03_UNICIDADE"].severidade.value,
        "status": "PASSOU" if passou_q03 else "FALHOU",
        "metrica_valor": taxa_unicidade_pct,
        "metrica_descricao": f"Taxa de unicidade de identificadores: {taxa_unicidade_pct}% (duplicatas={total_duplicatas})",
        "limite_esperado": "100.0%",
        "bloqueante": True,
    })

    # -------------------------------------------------------------------------
    # 4. CONSISTÊNCIA (Q04 - Severidade AVISO)
    # -------------------------------------------------------------------------
    eventos_conclusao = interacoes_df[interacoes_df["tipo_interacao"] == "conclusão"]
    total_conclusoes = len(eventos_conclusao)
    if total_conclusoes > 0:
        inconsistencias_conclusao = (eventos_conclusao["percentual_conclusao"] < 100.0).sum()
        pct_inconsistencia = (inconsistencias_conclusao / total_conclusoes) * 100.0
    else:
        inconsistencias_conclusao = 0
        pct_inconsistencia = 0.0

    taxa_consistencia_pct = round(100.0 - pct_inconsistencia, 4)
    # Tolerância de até 1.0% para severidade AVISO
    passou_q04 = pct_inconsistencia <= 1.0

    resultados_testes.append({
        "id_regra": "Q04_CONSISTENCIA",
        "nome": REGRAS_QUALIDADE["Q04_CONSISTENCIA"].nome,
        "dimensao": "Consistência",
        "severidade": REGRAS_QUALIDADE["Q04_CONSISTENCIA"].severidade.value,
        "status": "PASSOU" if passou_q04 else "ALERTA",
        "metrica_valor": taxa_consistencia_pct,
        "metrica_descricao": f"Taxa de consistência de conclusão: {taxa_consistencia_pct}% (inconsistências={inconsistencias_conclusao})",
        "limite_esperado": ">= 99.0% (Tolerância <= 1.0% de ressalva)",
        "bloqueante": False,
    })

    # -------------------------------------------------------------------------
    # 5. INTEGRIDADE REFERENCIAL (Q05)
    # -------------------------------------------------------------------------
    conteudos_validos_set = set(catalogo_df["conteudo_id"].unique())
    interacoes_orfas = (~interacoes_df["conteudo_id"].isin(conteudos_validos_set)).sum()
    taxa_integridade_pct = round((1.0 - (interacoes_orfas / total_interacoes)) * 100.0, 4)
    passou_q05 = interacoes_orfas == 0

    if not passou_q05:
        bloquear_publicacao = True

    resultados_testes.append({
        "id_regra": "Q05_INTEGRIDADE_REFERENCIAL",
        "nome": REGRAS_QUALIDADE["Q05_INTEGRIDADE_REFERENCIAL"].nome,
        "dimensao": "Integridade Referencial",
        "severidade": REGRAS_QUALIDADE["Q05_INTEGRIDADE_REFERENCIAL"].severidade.value,
        "status": "PASSOU" if passou_q05 else "FALHOU",
        "metrica_valor": taxa_integridade_pct,
        "metrica_descricao": f"Taxa de integridade referencial: {taxa_integridade_pct}% (órfãos={interacoes_orfas})",
        "limite_esperado": "100.0%",
        "bloqueante": True,
    })

    status_geral = "REPROVADO_CRITICO" if bloquear_publicacao else (
        "APROVADO_COM_RESSALVAS" if not passou_q04 else "APROVADO_INTEGRAL"
    )

    relatorio = {
        "lote_id": lote,
        "data_hora_avaliacao": agora_iso,
        "total_registros_interacoes": total_interacoes,
        "total_registros_catalogo": total_catalogo,
        "status_geral": status_geral,
        "bloquear_publicacao_gold": bloquear_publicacao,
        "metricas_chave_evolucao": {
            "taxa_completude_pct": taxa_completude_pct,
            "taxa_validade_pct": taxa_validade_pct,
            "taxa_unicidade_pct": taxa_unicidade_pct,
            "taxa_consistencia_pct": taxa_consistencia_pct,
            "taxa_integridade_referencial_pct": taxa_integridade_pct,
        },
        "detalhes_testes": resultados_testes,
    }

    if logger:
        logger.info(
            "Avaliação de Qualidade de Dados concluída | Status: %s | Bloquear Gold: %s",
            status_geral,
            bloquear_publicacao,
        )
        for t in resultados_testes:
            logger.info("  [%-6s] %-30s | %s", t["status"], t["nome"], t["metrica_descricao"])

    return relatorio


def persistir_historico_qualidade(
    relatorio: dict[str, Any],
    caminho_arquivo: Path | str = "dados/processados/historico_qualidade.json",
) -> None:
    """Registra a avaliação no histórico acumulado para rastreamento da evolução das métricas."""
    caminho = Path(caminho_arquivo)
    if not caminho.is_absolute():
        caminho = caminho_absoluto(str(caminho_arquivo))

    caminho.parent.mkdir(parents=True, exist_ok=True)

    historico = []
    if caminho.exists():
        try:
            with caminho.open("r", encoding="utf-8") as f:
                conteudo = json.load(f)
                if isinstance(conteudo, list):
                    historico = conteudo
        except Exception:
            historico = []

    # Salva apenas o resumo da execução no histórico acumulado
    item_historico = {
        "lote_id": relatorio["lote_id"],
        "data_hora": relatorio["data_hora_avaliacao"],
        "status_geral": relatorio["status_geral"],
        "bloquear_publicacao_gold": relatorio["bloquear_publicacao_gold"],
        "metricas": relatorio["metricas_chave_evolucao"],
    }
    historico.append(item_historico)

    with caminho.open("w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)
