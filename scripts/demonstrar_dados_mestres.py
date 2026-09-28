"""Módulo de Demonstração e Reconciliação de Dados Mestres (RF30 - MDM).

Demonstra:
1. Correspondência de registros duplicados com divergências (Matching).
2. Regras de Sobrevivência de atributos (Survivorship Rules).
3. Geração de Identificador Mestre único determinístico (Master ID).
4. Tabela de Correspondência Cruzada (Cross-Reference / XREF).
"""
from __future__ import annotations

import difflib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NAMESPACE_MDM = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def calcular_similaridade(texto1: str, texto2: str) -> float:
    """Calcula taxa de similaridade textual normalizada entre dois títulos."""
    t1 = texto1.lower().strip()
    t2 = texto2.lower().strip()
    return round(difflib.SequenceMatcher(None, t1, t2).ratio(), 3)


def reconciliar_registros_conflitantes(
    registro_a: dict[str, Any],
    registro_b: dict[str, Any],
) -> dict[str, Any]:
    """Aplica as regras de matching e survivorship para produzir o Golden Record."""
    sim = calcular_similaridade(registro_a["titulo"], registro_b["titulo"])
    if sim < 0.80:
        raise ValueError(f"Registros não são correspondentes (similaridade={sim} < 0.80)")

    # 1. Gera Identificador Mestre determinístico baseado no slug do título principal normalizado
    titulo_base = str(registro_b.get("titulo") or registro_a.get("titulo", "")).strip()
    slug_base = "conteudo_" + titulo_base.lower().replace(" ", "_")
    master_id = f"MDM_CONTEUDO_{uuid.uuid5(NAMESPACE_MDM, slug_base).hex[:16]}"

    # 2. Regras de Sobrevivência (Survivorship):
    # - Titulo: Prevalece versão com acentuação e caixa mista curada
    tit_a = str(registro_a.get("titulo", "")).strip()
    tit_b = str(registro_b.get("titulo", "")).strip()
    if any(c in "áéíóúãõçÁÉÍÓÚÃÕÇ" for c in tit_b) and not any(c in "áéíóúãõçÁÉÍÓÚÃÕÇ" for c in tit_a):
        titulo_curado = tit_b
    elif tit_b.istitle() and not tit_a.istitle():
        titulo_curado = tit_b
    elif tit_a.istitle() and not tit_b.istitle():
        titulo_curado = tit_a
    else:
        titulo_curado = tit_a or tit_b

    # - Nivel: Vocabulário formal ('Básico', 'Intermediário', 'Avançado') prevalece sobre termos informais
    niveis_formais = {"Básico", "Intermediário", "Avançado"}
    niv_a = str(registro_a.get("nivel", "")).strip()
    niv_b = str(registro_b.get("nivel", "")).strip()
    if niv_a in niveis_formais and niv_b not in niveis_formais:
        nivel_curado = niv_a
    elif niv_b in niveis_formais and niv_a not in niveis_formais:
        nivel_curado = niv_b
    else:
        nivel_curado = niv_b if int(registro_b.get("carga_horaria_min", 0)) >= int(registro_a.get("carga_horaria_min", 0)) else niv_a

    # - Carga Horaria: Prevalece a maior carga horária (edição estendida / completa)
    ch_a = int(registro_a.get("carga_horaria_min", 0))
    ch_b = int(registro_b.get("carga_horaria_min", 0))
    carga_curada = max(ch_a, ch_b)

    # - Autor: Prevalece o nome mais completo ou registro de coautoria/revisão
    aut_a = str(registro_a.get("autor", "")).strip()
    aut_b = str(registro_b.get("autor", "")).strip()
    if aut_a and aut_b:
        if aut_a == aut_b:
            autor_curado = aut_a
        elif aut_a in aut_b:
            autor_curado = aut_b
        elif aut_b in aut_a:
            autor_curado = aut_a
        else:
            autor_curado = f"{aut_a} (Original) / {aut_b} (Revisão)"
    else:
        autor_curado = aut_a or aut_b or "Não informado"

    golden_record = {
        "master_id": master_id,
        "titulo": titulo_curado,
        "tipo": str(registro_a.get("tipo") or registro_b.get("tipo") or "Artigo"),
        "categoria": str(registro_b.get("categoria") or registro_a.get("categoria") or "Geral"),
        "nivel": nivel_curado,
        "carga_horaria_min": carga_curada,
        "autor": autor_curado,
        "status_mdm": "GOLDEN_RECORD_UNIFICADO",
        "data_reconciliacao": datetime.now(timezone.utc).isoformat(),
    }

    # 3. Tabela de Correspondência (XREF)
    xref_table = [
        {
            "master_id": master_id,
            "sistema_origem": registro_a.get("sistema_origem", "silver.catalogo"),
            "id_origem": str(registro_a.get("conteudo_id", "")),
            "score_matching": sim,
            "regra_aplicada": "MATCH_TITULO_NORMALIZADO_SURVIVORSHIP_CURADO",
        },
        {
            "master_id": master_id,
            "sistema_origem": registro_b.get("sistema_origem", "silver.catalogo"),
            "id_origem": str(registro_b.get("conteudo_id", "")),
            "score_matching": 1.0,
            "regra_aplicada": "MATCH_ORIGEM_HOMOLOGADA_SURVIVORSHIP_RECENTE",
        },
    ]

    return {
        "similaridade_detectada": sim,
        "golden_record": golden_record,
        "tabela_xref": xref_table,
    }


def main() -> None:
    print("=================================================================")
    print("DEMONSTRAÇÃO DE GOVERNANÇA DE DADOS MESTRES — MDM (RF30)")
    print("=================================================================")

    # 1. Carrega os dois registros conflitantes DIRETAMENTE do banco PostgreSQL (silver.catalogo)
    reg_a = None
    reg_b = None
    fonte_usada = ""

    try:
        import os
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        variaveis_obrigatorias = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT"]
        ausentes = [v for v in variaveis_obrigatorias if not os.environ.get(v)]
        if ausentes:
            raise KeyError(f"Variáveis obrigatórias ausentes no .env: {ausentes}. Fallbacks desabilitados (RF15).")
        conn = psycopg2.connect(
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ["POSTGRES_PORT"]),
        )

        cur = conn.cursor()
        cur.execute(
            """
            SELECT conteudo_id, titulo, tipo, categoria, nivel, carga_horaria_min, autor, data_publicacao
            FROM silver.catalogo
            WHERE conteudo_id IN (588, 919)
            ORDER BY conteudo_id;
            """
        )
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        conn.close()

        if len(rows) >= 2:
            reg_a = rows[0]
            reg_b = rows[1]
            reg_a["sistema_origem"] = "POSTGRES_SILVER_CATALOGO_ID588"
            reg_b["sistema_origem"] = "POSTGRES_SILVER_CATALOGO_ID919"
            fonte_usada = "Banco PostgreSQL Real (tabela silver.catalogo)"
    except Exception as err:
        print(f"[Aviso] Conexão direta com PostgreSQL não disponível ({err}). Usando arquivo oficial dados/brutos/catalogo.csv.")

    # Fallback caso o PostgreSQL não esteja acessível: lê do catálogo CSV oficial
    if not reg_a or not reg_b:
        caminho_catalogo = Path("dados/brutos/catalogo.csv")
        if caminho_catalogo.exists():
            import pandas as pd
            df_real = pd.read_csv(caminho_catalogo)
            r1 = df_real[df_real["conteudo_id"] == 588].iloc[0]
            r2 = df_real[df_real["conteudo_id"] == 919].iloc[0]
            reg_a = {
                "sistema_origem": "CATALOGO_CSV_ID588",
                "conteudo_id": int(r1["conteudo_id"]),
                "titulo": str(r1["titulo"]),
                "tipo": str(r1["tipo"]),
                "categoria": str(r1["categoria"]),
                "nivel": str(r1["nivel"]),
                "carga_horaria_min": int(r1["carga_horaria_min"]),
                "autor": str(r1["autor"]),
                "data_publicacao": str(r1.get("data_publicacao", "2024-01-23")),
            }
            reg_b = {
                "sistema_origem": "CATALOGO_CSV_ID919",
                "conteudo_id": int(r2["conteudo_id"]),
                "titulo": str(r2["titulo"]),
                "tipo": str(r2["tipo"]),
                "categoria": str(r2["categoria"]),
                "nivel": str(r2["nivel"]),
                "carga_horaria_min": int(r2["carga_horaria_min"]),
                "autor": str(r2["autor"]),
                "data_publicacao": str(r2.get("data_publicacao", "2026-06-10")),
            }
            fonte_usada = "Arquivo de Catálogo Oficial (dados/brutos/catalogo.csv)"

    print(f"\n[Fonte de Dados Utilizada]: {fonte_usada}")
    print("\n--- 1. Registros Conflitantes de Origem (Extraídos da Base Real) ---")
    print(f"Registro A (ID {reg_a['conteudo_id']} - Origem: {reg_a['sistema_origem']}):")
    print(f"  Título: {reg_a['titulo']}")
    print(f"  Categoria: {reg_a['categoria']} | Tipo: {reg_a['tipo']} | Nível: {reg_a['nivel']} | Carga: {reg_a['carga_horaria_min']} min")
    print(f"  Autor: {reg_a['autor']}")

    print(f"\nRegistro B (ID {reg_b['conteudo_id']} - Origem: {reg_b['sistema_origem']}):")
    print(f"  Título: {reg_b['titulo']}")
    print(f"  Categoria: {reg_b['categoria']} | Tipo: {reg_b['tipo']} | Nível: {reg_b['nivel']} | Carga: {reg_b['carga_horaria_min']} min")
    print(f"  Autor: {reg_b['autor']}")

    resultado = reconciliar_registros_conflitantes(reg_a, reg_b)

    print("\n--- 2. Resultado da Reconciliação MDM ---")
    print(f"Taxa de Correspondência (Matching): {resultado['similaridade_detectada'] * 100:.1f}%")
    print(f"Master ID Gerado: {resultado['golden_record']['master_id']}")
    print("\nGolden Record Unificado (Sobrevivência de Atributos):")
    for k, v in resultado["golden_record"].items():
        print(f"  - {k}: {v}")

    print("\n--- 3. Tabela de Correspondência Cruzada (XREF) ---")
    for xref in resultado["tabela_xref"]:
        print(f"  Origem: {xref['sistema_origem']:<35} | ID Origem: {xref['id_origem']:<5} -> Master ID: {xref['master_id']} (Score: {xref['score_matching']})")

    # Persiste evidência JSON
    saida = Path("dados/processados/resultado_dados_mestres.json")
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Evidência técnica gravada em: {saida}")
    print("=================================================================")


if __name__ == "__main__":
    main()

