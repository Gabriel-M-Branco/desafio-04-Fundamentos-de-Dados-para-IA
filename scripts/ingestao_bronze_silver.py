#!/usr/bin/env python3
"""Parte do Estudante 1: Bronze, Silver, auditoria, quarentena e reprocessamento.

Uso:
  python scripts/estudante1_pipeline.py --stage all --source-dir ../desafio-03-pipeline-recomendacao/dados/brutos
  python scripts/estudante1_pipeline.py --stage bronze --source-dir ...
  python scripts/estudante1_pipeline.py --stage silver --source-dir ...
  python scripts/estudante1_pipeline.py --reprocess-quarantine dados/quarentena/corrigidos.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import psycopg
    from psycopg import sql
except Exception:  # permite rodar com --skip-db sem psycopg
    psycopg = None
    sql = None


def utc_now() -> str:
    from zoneinfo import ZoneInfo
    tz_name = os.environ.get("TZ", "America/Cuiaba")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/Cuiaba")
    return datetime.now(tz).isoformat()


def log_event(log_file: Path, run_id: str, etapa: str, status: str, **extras: Any) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    row = {"run_id": run_id, "etapa": etapa, "status": status, "timestamp": utc_now(), **extras}
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def read_json(path: Path) -> pd.DataFrame:
    return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))


def add_audit(df: pd.DataFrame, origem: str, run_id: str) -> pd.DataFrame:
    out = df.copy()
    out["_origem"] = origem
    out["_ingestao_em"] = utc_now()
    out["_run_id"] = run_id
    return out


def normalize_nulls(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    return value


def db_connect():
    if psycopg is None:
        raise RuntimeError("psycopg não está instalado. Rode pip install -r requirements.txt")
    from dotenv import load_dotenv
    load_dotenv()
    variaveis_obrigatorias = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    ausentes = [v for v in variaveis_obrigatorias if not os.environ.get(v)]
    if ausentes:
        raise KeyError(f"Variáveis de ambiente obrigatórias não configuradas no .env: {ausentes}. Fallbacks desabilitados (RF15).")
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )



DDL = {
    ("bronze", "catalogo"): """
      conteudo_id bigint, titulo text, tipo text, categoria text, nivel text,
      carga_horaria_min integer, data_publicacao date, descricao text, autor text,
      _origem text, _ingestao_em timestamptz, _run_id uuid
    """,
    ("bronze", "interacoes"): """
      usuario_id bigint, conteudo_id bigint, tipo_interacao text, data_hora timestamp,
      tempo_consumido integer, percentual_conclusao numeric(6,2), avaliacao_atribuida numeric(3,1),
      _origem text, _ingestao_em timestamptz, _run_id uuid
    """,
    ("bronze", "comentarios"): """
      usuario_id bigint, conteudo_id bigint, avaliacao numeric(3,1), comentario text,
      tags jsonb, data date, _origem text, _ingestao_em timestamptz, _run_id uuid
    """,
    ("silver", "catalogo"): """
      conteudo_id bigint, titulo text, tipo text, categoria text, nivel text,
      carga_horaria_min integer, data_publicacao date, descricao text, autor text,
      _origem text, _ingestao_em timestamptz, _run_id uuid
    """,
    ("silver", "interacoes"): """
      usuario_id bigint, conteudo_id bigint, tipo_interacao text, data_hora timestamp,
      tempo_consumido_min numeric(12,2), percentual_conclusao numeric(6,2), avaliacao numeric(3,1),
      _origem text, _ingestao_em timestamptz, _run_id uuid
    """,
    ("silver", "comentarios"): """
      usuario_id bigint, conteudo_id bigint, avaliacao numeric(3,1), comentario text,
      tags jsonb, data date, _origem text, _ingestao_em timestamptz, _run_id uuid
    """,
}


def ensure_table(conn, schema: str, table: str) -> None:
    ddl = DDL[(schema, table)]
    with conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        cur.execute(
            sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
                sql.Identifier(schema), sql.Identifier(table), sql.SQL(ddl)
            )
        )
    conn.commit()


def load_df(conn, df: pd.DataFrame, schema: str, table: str) -> int:
    ensure_table(conn, schema, table)
    ddl_str = DDL.get((schema, table), "")
    allowed_cols = [c.strip().split()[0] for c in ddl_str.strip().split(",") if c.strip()]
    if allowed_cols:
        cols = [c for c in allowed_cols if c in df.columns]
        df_to_load = df[cols]
    else:
        cols = list(df.columns)
        df_to_load = df

    values = [[normalize_nulls(v) for v in row] for row in df_to_load.itertuples(index=False, name=None)]
    if not values:
        return 0
    stmt = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(",").join(map(sql.Identifier, cols)),
        sql.SQL(",").join(sql.Placeholder() for _ in cols),
    )
    with conn.cursor() as cur:
        cur.executemany(stmt, values)
    conn.commit()
    return len(values)


def salvar_quarentena_db(conn, quarentena_records: list[dict]) -> int:
    if not quarentena_records:
        return 0
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS quarentena;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quarentena.registros (
              quarentena_id BIGSERIAL PRIMARY KEY,
              entidade TEXT NOT NULL, id_registro TEXT, origem TEXT NOT NULL,
              regra_violada TEXT NOT NULL, mensagem_erro TEXT NOT NULL,
              data_erro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              id_execucao TEXT NOT NULL, payload TEXT NOT NULL,
              reprocessado BOOLEAN NOT NULL DEFAULT FALSE,
              data_reprocessamento TIMESTAMP, novo_id_execucao TEXT
            );
        """)
        stmt = sql.SQL("""
            INSERT INTO quarentena.registros (
                entidade, id_registro, origem, regra_violada, mensagem_erro, data_erro, id_execucao, payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """)
        values = [
            (
                r.get("tipo", "desconhecido"),
                str(r.get("registro_id")) if r.get("registro_id") is not None else None,
                r.get("origem", "desconhecido"),
                r.get("regra", "invalido"),
                r.get("mensagem", "Erro de validacao"),
                r.get("data_erro", utc_now()),
                r.get("run_id", "manual"),
                json.dumps(r.get("registro", {}), ensure_ascii=False, default=str),
            )
            for r in quarentena_records
        ]
        cur.executemany(stmt, values)
    conn.commit()
    return len(values)


def bronze(source_dir: Path, output_dir: Path, run_id: str, skip_db: bool) -> dict[str, int]:
    bronze_dir = output_dir / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    sources = {
        "catalogo": source_dir / "catalogo.csv",
        "interacoes": source_dir / "interacoes.json",
        "comentarios": source_dir / "comentarios.json",
    }
    for p in sources.values():
        if not p.exists():
            raise FileNotFoundError(f"Fonte obrigatória não encontrada: {p}")

    # Preserva cópia exata para auditoria/reprocessamento.
    shutil.copy2(sources["catalogo"], bronze_dir / "catalogo.csv")
    shutil.copy2(sources["interacoes"], bronze_dir / "interacoes.json")
    shutil.copy2(sources["comentarios"], bronze_dir / "comentarios.json")

    catalogo = add_audit(pd.read_csv(sources["catalogo"]), "catalogo.csv", run_id)
    interacoes = add_audit(read_json(sources["interacoes"]), "interacoes.json", run_id)
    comentarios = add_audit(read_json(sources["comentarios"]), "comentarios.json", run_id)

    # Incorpora cenários de teste se disponíveis no diretório brutos/cenarios_de_teste
    cenarios_dir = source_dir / "cenarios_de_teste"
    if cenarios_dir.exists():
        cat_cen = cenarios_dir / "catalogo_cenarios.csv"
        int_cen = cenarios_dir / "interacoes_cenarios.json"
        com_cen = cenarios_dir / "comentarios_cenarios.json"
        if cat_cen.exists():
            df_cat_cen = add_audit(pd.read_csv(cat_cen), "cenarios_de_teste/catalogo_cenarios.csv", run_id)
            catalogo = pd.concat([catalogo, df_cat_cen], ignore_index=True)
        if int_cen.exists():
            df_int_cen = add_audit(read_json(int_cen), "cenarios_de_teste/interacoes_cenarios.json", run_id)
            interacoes = pd.concat([interacoes, df_int_cen], ignore_index=True)
        if com_cen.exists():
            df_com_cen = add_audit(read_json(com_cen), "cenarios_de_teste/comentarios_cenarios.json", run_id)
            comentarios = pd.concat([comentarios, df_com_cen], ignore_index=True)

    catalogo.to_parquet(bronze_dir / "catalogo.parquet", index=False)
    interacoes.to_parquet(bronze_dir / "interacoes.parquet", index=False)
    comentarios.to_parquet(bronze_dir / "comentarios.parquet", index=False)

    if not skip_db:
        with db_connect() as conn:
            load_df(conn, catalogo, "bronze", "catalogo")
            load_df(conn, interacoes, "bronze", "interacoes")
            load_df(conn, comentarios, "bronze", "comentarios")

    return {
        "catalogo": len(catalogo),
        "interacoes": len(interacoes),
        "comentarios": len(comentarios),
    }


def quarantine_record(tipo: str, origem: str, regra: str, mensagem: str, run_id: str, registro_id: Any, registro: dict) -> dict:
    return {
        "tipo": tipo,
        "registro_id": normalize_nulls(registro_id),
        "origem": origem,
        "regra": regra,
        "data_erro": utc_now(),
        "mensagem": mensagem,
        "run_id": run_id,
        "registro": {k: normalize_nulls(v) for k, v in registro.items()},
    }


def silver(output_dir: Path, run_id: str, skip_db: bool) -> dict[str, int]:
    bronze_dir = output_dir / "bronze"
    silver_dir = output_dir / "silver"
    quarantine_dir = output_dir / "quarentena"
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    cat_path = bronze_dir / "catalogo.parquet"
    int_path = bronze_dir / "interacoes.parquet"
    com_path = bronze_dir / "comentarios.parquet"
    for p in (cat_path, int_path, com_path):
        if not p.exists():
            raise FileNotFoundError(f"Bronze não encontrada: {p}. Execute --stage bronze primeiro.")

    catalogo = pd.read_parquet(cat_path)
    interacoes = pd.read_parquet(int_path)
    comentarios = pd.read_parquet(com_path)
    quarentena: list[dict] = []

    # Catálogo
    catalogo.columns = [str(c).strip().lower() for c in catalogo.columns]
    for col in ("titulo", "tipo", "categoria", "nivel", "descricao", "autor"):
        catalogo[col] = catalogo[col].astype(str).str.strip()
    catalogo["tipo"] = catalogo["tipo"].str.title()
    catalogo["nivel"] = catalogo["nivel"].str.title()
    catalogo["conteudo_id"] = pd.to_numeric(catalogo["conteudo_id"], errors="coerce")
    catalogo["carga_horaria_min"] = pd.to_numeric(catalogo["carga_horaria_min"], errors="coerce")
    catalogo["data_publicacao"] = pd.to_datetime(catalogo["data_publicacao"], errors="coerce").dt.date
    valid_types = {"Curso", "Vídeo", "Artigo", "Podcast"}
    valid_levels = {"Básico", "Intermediário", "Avançado"}

    mask_cat = (
        catalogo["conteudo_id"].notna()
        & catalogo["titulo"].ne("")
        & catalogo["tipo"].isin(valid_types)
        & catalogo["nivel"].isin(valid_levels)
        & catalogo["carga_horaria_min"].gt(0)
        & catalogo["data_publicacao"].notna()
    )
    for idx, row in catalogo.loc[~mask_cat].iterrows():
        quarentena.append(quarantine_record(
            "catalogo", "catalogo.csv", "validade/completude",
            "Registro de conteúdo com campo obrigatório, domínio ou tipo inválido.",
            run_id, idx, row.to_dict()
        ))
    catalogo_ok = catalogo.loc[mask_cat].drop_duplicates(subset=["conteudo_id"], keep="last").copy()
    valid_content = set(catalogo_ok["conteudo_id"].astype(int))

    # Interações
    if "avaliacao_atribuida" in interacoes.columns and "avaliacao" in interacoes.columns:
        interacoes["avaliacao"] = interacoes["avaliacao"].fillna(interacoes["avaliacao_atribuida"])
        interacoes = interacoes.drop(columns=["avaliacao_atribuida"])
    elif "avaliacao_atribuida" in interacoes.columns:
        interacoes = interacoes.rename(columns={"avaliacao_atribuida": "avaliacao"})

    if "tempo_consumido" in interacoes.columns and "tempo_consumido_min" in interacoes.columns:
        interacoes["tempo_consumido_min"] = interacoes["tempo_consumido_min"].fillna(interacoes["tempo_consumido"])
        interacoes = interacoes.drop(columns=["tempo_consumido"])
    elif "tempo_consumido" in interacoes.columns:
        interacoes = interacoes.rename(columns={"tempo_consumido": "tempo_consumido_min"})

    for col in ("usuario_id", "conteudo_id", "tempo_consumido_min", "percentual_conclusao", "avaliacao"):
        if col in interacoes:
            interacoes[col] = pd.to_numeric(interacoes[col], errors="coerce")
    interacoes["data_hora"] = pd.to_datetime(interacoes["data_hora"], errors="coerce")
    mask_int = (
        interacoes["usuario_id"].notna()
        & interacoes["conteudo_id"].isin(valid_content)
        & interacoes["data_hora"].notna()
        & interacoes["percentual_conclusao"].between(0, 100, inclusive="both")
        & interacoes["tempo_consumido_min"].fillna(0).ge(0)
        & (interacoes["avaliacao"].isna() | interacoes["avaliacao"].between(1, 5, inclusive="both"))
    )
    for idx, row in interacoes.loc[~mask_int].iterrows():
        quarentena.append(quarantine_record(
            "interacao", "interacoes.json", "validade/integridade_referencial",
            "Interação com usuário, conteúdo, data, percentual, tempo ou avaliação inválida.",
            run_id, idx, row.to_dict()
        ))
    interacoes_ok = interacoes.loc[mask_int].drop_duplicates(
        subset=["usuario_id", "conteudo_id", "tipo_interacao", "data_hora"], keep="last"
    ).copy()

    # Comentários
    for col in ("usuario_id", "conteudo_id", "avaliacao"):
        comentarios[col] = pd.to_numeric(comentarios[col], errors="coerce")
    comentarios["data"] = pd.to_datetime(comentarios["data"], errors="coerce").dt.date
    comentarios["comentario"] = comentarios["comentario"].astype(str).str.strip()
    mask_com = (
        comentarios["usuario_id"].notna()
        & comentarios["conteudo_id"].isin(valid_content)
        & comentarios["avaliacao"].between(1, 5, inclusive="both")
        & comentarios["data"].notna()
        & comentarios["comentario"].ne("")
    )
    for idx, row in comentarios.loc[~mask_com].iterrows():
        quarentena.append(quarantine_record(
            "comentario", "comentarios.json", "validade/integridade_referencial",
            "Comentário com usuário, conteúdo, avaliação, data ou texto inválido.",
            run_id, idx, row.to_dict()
        ))
    comentarios_ok = comentarios.loc[mask_com].drop_duplicates(
        subset=["usuario_id", "conteudo_id", "data", "comentario"], keep="last"
    ).copy()

    # Mantém auditoria original e run de processamento.
    for df in (catalogo_ok, interacoes_ok, comentarios_ok):
        df["_run_id"] = run_id

    catalogo_ok.to_parquet(silver_dir / "catalogo.parquet", index=False)
    interacoes_ok.to_parquet(silver_dir / "interacoes.parquet", index=False)
    comentarios_ok.to_parquet(silver_dir / "comentarios.parquet", index=False)

    qfile = quarantine_dir / f"quarentena_{run_id}.json"
    qfile.write_text(json.dumps(quarentena, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    if not skip_db:
        with db_connect() as conn:
            load_df(conn, catalogo_ok, "silver", "catalogo")
            load_df(conn, interacoes_ok, "silver", "interacoes")
            load_df(conn, comentarios_ok, "silver", "comentarios")
            if quarentena:
                salvar_quarentena_db(conn, quarentena)

    return {
        "catalogo_aprovados": len(catalogo_ok),
        "interacoes_aprovadas": len(interacoes_ok),
        "comentarios_aprovados": len(comentarios_ok),
        "quarentena": len(quarentena),
    }


def reprocess_quarantine(path: Path, output_dir: Path, run_id: str) -> dict[str, int]:
    """Reprocessa um arquivo de quarentena previamente corrigido.

    O operador deve corrigir manualmente o conteúdo de registro e manter:
      {"tipo": "interacao|comentario|catalogo", "registro": {...}}
    Registros aprovados são adicionados aos Parquets Silver; os reprovados voltam para quarentena.
    """
    records = json.loads(path.read_text(encoding="utf-8"))
    silver_dir = output_dir / "silver"
    quarantine_dir = output_dir / "quarentena"
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    catalogo = pd.read_parquet(silver_dir / "catalogo.parquet")
    valid_content = set(pd.to_numeric(catalogo["conteudo_id"], errors="coerce").dropna().astype(int))
    approved: dict[str, list[dict]] = {"catalogo": [], "interacao": [], "comentario": []}
    rejected: list[dict] = []

    for item in records:
        tipo = item.get("tipo")
        reg = item.get("registro", {})
        ok = False
        if tipo == "catalogo":
            ok = bool(reg.get("conteudo_id")) and bool(str(reg.get("titulo", "")).strip())
        elif tipo == "interacao":
            try:
                pct = float(reg.get("percentual_conclusao"))
                ok = int(reg.get("conteudo_id")) in valid_content and 0 <= pct <= 100
            except Exception:
                ok = False
        elif tipo == "comentario":
            try:
                nota = float(reg.get("avaliacao"))
                ok = int(reg.get("conteudo_id")) in valid_content and 1 <= nota <= 5
            except Exception:
                ok = False

        if ok:
            reg["_run_id"] = run_id
            approved[tipo].append(reg)
        else:
            rejected.append(quarantine_record(
                tipo or "desconhecido", str(item.get("origem", "quarentena_corrigida")),
                "reprocessamento", "Registro ainda inválido após correção.",
                run_id, item.get("registro_id"), reg
            ))

    mapping = {
        "catalogo": "catalogo.parquet",
        "interacao": "interacoes.parquet",
        "comentario": "comentarios.parquet",
    }
    for tipo, rows in approved.items():
        if not rows:
            continue
        dest = silver_dir / mapping[tipo]
        base = pd.read_parquet(dest)
        extra = pd.DataFrame(rows)
        for col in base.columns:
            if col not in extra:
                extra[col] = None
        extra = extra[base.columns]

        # Reaplica os tipos da camada Silver antes de gravar o registro
        # reprocessado. Registros vindos do JSON de quarentena chegam como
        # strings/objetos e precisam ser compatíveis com o schema Parquet.
        if tipo == "interacao":
            if "data_hora" in extra.columns:
                extra["data_hora"] = pd.to_datetime(extra["data_hora"], errors="coerce")
            for col in (
                "usuario_id",
                "conteudo_id",
                "tempo_consumido_min",
                "percentual_conclusao",
                "avaliacao",
            ):
                if col in extra.columns:
                    extra[col] = pd.to_numeric(extra[col], errors="coerce")

        pd.concat([base, extra], ignore_index=True).to_parquet(dest, index=False)

    out = quarantine_dir / f"reprocessamento_rejeitados_{run_id}.json"
    out.write_text(json.dumps(rejected, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {
        "aprovados": sum(len(v) for v in approved.values()),
        "rejeitados": len(rejected),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["bronze", "silver", "all"], default="all")
    parser.add_argument("--source-dir")
    parser.add_argument("--output-dir", default="dados")
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--reprocess-quarantine")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    run_id = str(uuid.uuid4())
    log_file = Path("logs") / "pipeline_ingestao.jsonl"

    if args.reprocess_quarantine:
        log_event(log_file, run_id, "reprocessamento", "INICIO", arquivo=args.reprocess_quarantine)
        result = reprocess_quarantine(Path(args.reprocess_quarantine), output_dir, run_id)
        log_event(log_file, run_id, "reprocessamento", "SUCESSO", **result)
        print(json.dumps({"run_id": run_id, **result}, ensure_ascii=False, indent=2))
        return

    if not args.source_dir:
        raise SystemExit("--source-dir é obrigatório para bronze/silver/all")

    source_dir = Path(args.source_dir)
    result: dict[str, Any] = {"run_id": run_id}

    try:
        if args.stage in ("bronze", "all"):
            log_event(log_file, run_id, "bronze", "INICIO")
            r = bronze(source_dir, output_dir, run_id, args.skip_db)
            result["bronze"] = r
            log_event(log_file, run_id, "bronze", "SUCESSO", **r)

        if args.stage in ("silver", "all"):
            log_event(log_file, run_id, "silver", "INICIO")
            r = silver(output_dir, run_id, args.skip_db)
            result["silver"] = r
            log_event(log_file, run_id, "silver", "SUCESSO", **r)

        result["status_final"] = "SUCESSO"
    except Exception as exc:
        result["status_final"] = "FALHA"
        result["erro"] = str(exc)
        log_event(log_file, run_id, args.stage, "FALHA", erro=str(exc))
        raise
    finally:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "resumo_ingestao_bronze_silver.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
