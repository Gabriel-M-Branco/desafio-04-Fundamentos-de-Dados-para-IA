"""Orquestrador do Fluxo Completo de Execução Ponta a Ponta.

Executa em uma única chamada todas as etapas do tutorial do Desafio:
1. python -m src.main (Carga Base, pgvector, embeddings e recomendações IA)
2. docker exec hop-web ... (Workflow integrado Apache Hop: Bronze, Silver e DDL Gold)
3. python -m src.executar_etapas --etapa todas (Parquet Hive, Qualidade RF31, LGPD RF32/33, Beam RF25, Gold RF26)
4. python scripts/demonstrar_dados_mestres.py (MDM / Golden Record - RF30)
5. python scripts/configurar_openmetadata.py (OpenMetadata Catálogo, Glossário e Linhagem - RF27-RF29)
6. python dashboard/sync_database.py (Sincronização e importação de dashboards no Apache Superset)
7. python -m pytest tests/ (Suíte completa de 103 testes automatizados)

Uso:
    python scripts/executar_fluxo_completo.py
    python scripts/executar_fluxo_completo.py --sem-testes
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from time import perf_counter

RAIZ_PROJETO = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa o fluxo completo do pipeline em um único comando."
    )
    parser.add_argument(
        "--sem-testes",
        action="store_true",
        help="Executa todo o pipeline de dados e governança, omitindo apenas o pytest final.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    py = sys.executable

    etapas = [
        (
            "1. Carga Base, IA e Embeddings (RF02-RF10)",
            [py, "-m", "src.main"],
            "Inicializa esquemas, carrega MongoDB, calcula embeddings vetoriais com pgvector e recomendações.",
        ),
        (
            "2. Ingestão Bronze/Silver e DDL Gold no Apache Hop (RF20-RF23, RF26)",
            [
                "docker",
                "exec",
                "hop-web",
                "/usr/local/tomcat/webapps/ROOT/hop-run.sh",
                "--environment",
                "desafio4-dev",
                "--project",
                "desafio4",
                "--file",
                "/files/workflows/workflow_principal.hwf",
                "--runconfig",
                "local",
                "--level",
                "BASIC",
            ],
            "Executa o workflow principal no Apache Hop, isola quarentena e provisiona tabelas Gold.",
        ),
        (
            "3. Pipeline Analítico, Parquet Hive, Qualidade RF31, LGPD e Apache Beam (RF24-RF26, RF31-RF33)",
            [py, "-m", "src.executar_etapas", "--etapa", "todas"],
            "Gera Parquet particionado Hive, benchmark comparativo, Quality Gate, proteção LGPD e agregações Beam.",
        ),
        (
            "4. Governança de Dados Mestres — MDM (RF30)",
            [py, str(RAIZ_PROJETO / "scripts" / "demonstrar_dados_mestres.py")],
            "Executa motor de matching, sobrevivência de atributos e geração de Golden Record a partir da Silver real.",
        ),
        (
            "5. Governança, Glossário e Linhagem no OpenMetadata (RF27-RF29)",
            [py, str(RAIZ_PROJETO / "scripts" / "configurar_openmetadata.py")],
            "Provisiona catálogo completo, 4 termos de glossário e grafo de linhagem de 5 pontas via API REST.",
        ),
        (
            "6. Sincronização Analítica no Apache Superset (RF16-RF18)",
            [py, str(RAIZ_PROJETO / "dashboard" / "sync_database.py")],
            "Sincroniza conexão de banco e importa dashboards analíticos no Apache Superset.",
        ),
    ]

    if not args.sem_testes:
        etapas.append(
            (
                "7. Suíte de Testes Automatizados (RF34)",
                [py, "-m", "pytest", "tests/"],
                "Validação de qualidade do código e testes automatizados de regressão.",
            )
        )

    inicio_total = perf_counter()
    total_etapas = len(etapas)

    print("=" * 80)
    print("INICIANDO FLUXO COMPLETO DO DESAFIO (TODAS AS ETAPAS EM UMA ÚNICA EXECUÇÃO)")
    print(f"Diretório raiz: {RAIZ_PROJETO}")
    print(f"Interpretador Python: {py}")
    print(f"Total de etapas programadas: {total_etapas}")
    print("=" * 80)
    print()

    tempos: list[tuple[str, float]] = []

    for idx, (nome, comando, descricao) in enumerate(etapas, start=1):
        print("-" * 80)
        print(f">>> [{idx}/{total_etapas}] {nome}")
        print(f"    Descrição: {descricao}")
        print(f"    Comando:   {' '.join(comando)}")
        print("-" * 80)

        t_inicio = perf_counter()
        try:
            resultado = subprocess.run(comando, cwd=str(RAIZ_PROJETO))
            duracao = perf_counter() - t_inicio
            tempos.append((nome, duracao))

            if resultado.returncode != 0:
                print()
                print("!" * 80)
                print(f"[ERRO CRÍTICO] A etapa '{nome}' falhou com código de saída {resultado.returncode}.")
                print("O fluxo foi interrompido para análise.")
                print("!" * 80)
                sys.exit(resultado.returncode)

            print(f"[OK] Etapa [{idx}/{total_etapas}] concluída com sucesso em {duracao:.2f}s.")
            print()
        except KeyboardInterrupt:
            print("\n[INTERROMPIDO] Execução cancelada pelo usuário.")
            sys.exit(130)
        except Exception as exc:
            duracao = perf_counter() - t_inicio
            print(f"\n[FALHA INESPERADA] Erro ao executar a etapa '{nome}': {exc}")
            sys.exit(1)

    duracao_total = perf_counter() - inicio_total
    print("=" * 80)
    print("FLUXO COMPLETO CONCLUÍDO COM SUCESSO!")
    print(f"Tempo total de execução: {duracao_total:.2f} segundos.")
    print("-" * 80)
    print("Resumo de tempo por etapa:")
    for nome, t in tempos:
        print(f"  - {nome:<60}: {t:6.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
