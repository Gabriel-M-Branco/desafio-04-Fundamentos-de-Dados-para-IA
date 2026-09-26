from pathlib import Path
import json
import subprocess
import sys

import pandas as pd


def write_sources(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {
            "conteudo_id": 1,
            "titulo": " Curso Java ",
            "tipo": "Curso",
            "categoria": "Programação",
            "nivel": "Básico",
            "carga_horaria_min": 60,
            "data_publicacao": "2026-01-01",
            "descricao": "Teste",
            "autor": "Autor",
        },
        {
            "conteudo_id": 1,
            "titulo": "Curso Java",
            "tipo": "Curso",
            "categoria": "Programação",
            "nivel": "Básico",
            "carga_horaria_min": 60,
            "data_publicacao": "2026-01-01",
            "descricao": "Teste",
            "autor": "Autor",
        },
    ]).to_csv(base / "catalogo.csv", index=False)

    (base / "interacoes.json").write_text(json.dumps([
        {
            "usuario_id": 10,
            "conteudo_id": 1,
            "tipo_interacao": "conclusão",
            "data_hora": "2026-01-02T10:00:00",
            "tempo_consumido": 30,
            "percentual_conclusao": 100,
            "avaliacao_atribuida": 5,
        },
        {
            "usuario_id": 11,
            "conteudo_id": 1,
            "tipo_interacao": "visualização",
            "data_hora": "2026-01-02T11:00:00",
            "tempo_consumido": 10,
            "percentual_conclusao": 150,
            "avaliacao_atribuida": None,
        },
    ], ensure_ascii=False), encoding="utf-8")

    (base / "comentarios.json").write_text(json.dumps([
        {
            "usuario_id": 10,
            "conteudo_id": 1,
            "avaliacao": 5,
            "comentario": "Ótimo",
            "tags": ["java"],
            "data": "2026-01-02",
        }
    ], ensure_ascii=False), encoding="utf-8")


def test_bronze_silver_e_quarentena(tmp_path):
    src = tmp_path / "src"
    out = tmp_path / "dados"
    write_sources(src)

    cmd = [
        sys.executable,
        "scripts/estudante1_pipeline.py",
        "--stage", "all",
        "--source-dir", str(src),
        "--output-dir", str(out),
        "--skip-db",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    assert (out / "bronze" / "catalogo.csv").exists()
    assert (out / "bronze" / "interacoes.parquet").exists()
    assert (out / "silver" / "catalogo.parquet").exists()
    assert (out / "silver" / "interacoes.parquet").exists()

    cat = pd.read_parquet(out / "silver" / "catalogo.parquet")
    inter = pd.read_parquet(out / "silver" / "interacoes.parquet")

    assert len(cat) == 1
    assert len(inter) == 1
    assert inter.iloc[0]["percentual_conclusao"] == 100

    qfiles = list((out / "quarentena").glob("quarentena_*.json"))
    assert qfiles
    q = json.loads(qfiles[0].read_text(encoding="utf-8"))
    assert len(q) == 1
    assert q[0]["tipo"] == "interacao"


def test_falha_arquivo_ausente(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "dados"

    result = subprocess.run([
        sys.executable,
        "scripts/estudante1_pipeline.py",
        "--stage", "bronze",
        "--source-dir", str(src),
        "--output-dir", str(out),
        "--skip-db",
    ], capture_output=True, text=True)

    assert result.returncode != 0
    assert "Fonte obrigatória não encontrada" in result.stderr


def test_reprocessamento_quarentena_corrigida(tmp_path):
    src = tmp_path / "src"
    out = tmp_path / "dados"
    write_sources(src)

    primeira_execucao = subprocess.run([
        sys.executable,
        "scripts/estudante1_pipeline.py",
        "--stage", "all",
        "--source-dir", str(src),
        "--output-dir", str(out),
        "--skip-db",
    ], capture_output=True, text=True)

    assert primeira_execucao.returncode == 0, primeira_execucao.stderr

    qfile = next((out / "quarentena").glob("quarentena_*.json"))
    registros = json.loads(qfile.read_text(encoding="utf-8"))
    assert len(registros) == 1

    registros[0]["registro"]["percentual_conclusao"] = 100
    corrigido = tmp_path / "quarentena_corrigida.json"
    corrigido.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    reprocessamento = subprocess.run([
        sys.executable,
        "scripts/estudante1_pipeline.py",
        "--reprocess-quarantine", str(corrigido),
        "--output-dir", str(out),
    ], capture_output=True, text=True)

    assert reprocessamento.returncode == 0, reprocessamento.stderr

    resultado = json.loads(reprocessamento.stdout)
    assert resultado["aprovados"] == 1
    assert resultado["rejeitados"] == 0

    interacoes = pd.read_parquet(out / "silver" / "interacoes.parquet")
    assert len(interacoes) == 2
    assert 100 in interacoes["percentual_conclusao"].tolist()
