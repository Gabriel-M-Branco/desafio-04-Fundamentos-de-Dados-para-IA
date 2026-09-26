"""Orquestrador de execução modular por etapas do Desafio Prático 2 (RF15).

Permite executar cada etapa de forma isolada ou encadeada de ponta a ponta:
    python -m src.executar_etapas --etapa parquet
    python -m src.executar_etapas --etapa benchmark
    python -m src.executar_etapas --etapa beam
    python -m src.executar_etapas --etapa qualidade
    python -m src.executar_etapas --etapa gold
    python -m src.executar_etapas --etapa todas
"""
from __future__ import annotations

import argparse
from time import perf_counter

import pandas as pd

from src.beam.comparador_runtimes import executar_comparacao_runtimes_beam
from src.beam.pipeline_gold import executar_pipeline_gold_beam
from src.config import caminho_absoluto, carregar_config
from src.gold.publicador import publicar_camada_gold
from src.logging_utils import configurar_logger
from src.parquet.benchmark import executar_benchmark_comparativo
from src.parquet.exportador import exportar_interacoes_parquet
from src.parquet.leitor import ler_parquet_interacoes
from src.qualidade.avaliador import avaliar_qualidade_dados, persistir_historico_qualidade


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execução modular do pipeline por etapas (Desafio 2 / RF15)"
    )
    parser.add_argument(
        "--etapa",
        choices=["ingestao", "parquet", "benchmark", "beam", "qualidade", "gold", "todas"],
        default="todas",
        help="Etapa específica a ser executada",
    )
    parser.add_argument(
        "--runner-beam",
        choices=["DirectRunner", "SparkRunner"],
        default="DirectRunner",
        help="Runner do Apache Beam para a etapa beam",
    )
    parser.add_argument(
        "--repeticoes-benchmark",
        type=int,
        default=5,
        help="Número de repetições cronometradas para o benchmark comparativo",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = carregar_config()
    logger = configurar_logger(caminho_absoluto(config["logs"]["arquivo"]))

    inicio = perf_counter()
    logger.info("=================================================================")
    logger.info("EXECUÇÃO MODULAR DESAFIO 2 — ETAPA SELECIONADA: %s", args.etapa.upper())
    logger.info("=================================================================")

    # 0. INGESTÃO BRONZE & SILVER (RF20-RF23)
    if args.etapa in ("ingestao", "todas"):
        script_ingestao = caminho_absoluto("scripts/ingestao_bronze_silver.py")
        if script_ingestao.exists():
            logger.info(">>> [0/5] Executando Etapa 1 / RF20-RF23: Ingestão das Camadas Bronze & Silver")
            try:
                from scripts.ingestao_bronze_silver import bronze, silver
                dir_brutos = caminho_absoluto("dados/brutos")
                dir_dados = caminho_absoluto("dados")
                run_id_ingestao = "RUN_INTEGRADO_BRONZE_SILVER"
                r_bronze = bronze(dir_brutos, dir_dados, run_id_ingestao, skip_db=True)
                r_silver = silver(dir_dados, run_id_ingestao, skip_db=True)
                print(
                    f"[OK] Ingestão Bronze & Silver concluída: {r_silver['interacoes_aprovadas']} interações, "
                    f"{r_silver['catalogo_aprovados']} conteúdos, {r_silver['quarentena']} na quarentena."
                )
            except Exception as exc:
                logger.warning("Aviso na execução da ingestão integrada: %s", exc)

    # 1. PARQUET (RF24)
    if args.etapa in ("parquet", "todas"):
        logger.info(">>> [1/5] Executando Etapa 2 / RF24: Exportação da Silver para Parquet particionado")
        res_parquet = exportar_interacoes_parquet(config, particionado=True, logger=logger)
        print(
            f"[OK] Parquet particionado gerado com sucesso: {res_parquet['total_registros']} registros, "
            f"{res_parquet['total_arquivos']} arquivos ({res_parquet['tamanho_kb']} KB)."
        )

    # 2. BENCHMARK COMPARATIVO (RF24)
    if args.etapa in ("benchmark", "todas"):
        logger.info(">>> [2/5] Executando Etapa 2 / RF24: Benchmark Comparativo Parquet vs CSV vs JSON")
        res_bench = executar_benchmark_comparativo(
            config=config,
            repeticoes=args.repeticoes_benchmark,
            logger=logger,
        )
        print(f"[OK] Benchmark concluído com sucesso!")
        print(f"     Relatório JSON: {config['parquet']['benchmark_saida']}")
        print(f"     Documentação MD: {config['parquet']['benchmark_doc']}")

    # 3. QUALIDADE DE DADOS (RF31)
    if args.etapa in ("qualidade", "todas"):
        logger.info(">>> [3/4] Executando Etapa 5 / RF31: Avaliação das 5 Dimensões de Qualidade de Dados")
        dir_parquet_interacoes = caminho_absoluto(config.get("parquet", {}).get("diretorio_saida", "dados/parquet")) / "interacoes" / "particionado"
        origem_catalogo = caminho_absoluto(config.get("dados", {}).get("processados", {}).get("catalogo", "dados/processados/catalogo_processado.csv"))
        df_int = ler_parquet_interacoes(dir_parquet_interacoes)
        df_cat = pd.read_csv(origem_catalogo)

        rel_qualidade = avaliar_qualidade_dados(df_int, df_cat, logger=logger)
        persistir_historico_qualidade(rel_qualidade)
        print(f"[OK] Qualidade avaliada: Status Geral = {rel_qualidade['status_geral']}")
        print(f"     Bloquear Gold: {rel_qualidade['bloquear_publicacao_gold']}")
        for t in rel_qualidade["detalhes_testes"]:
            print(f"     - [{t['status']}] {t['nome']}: {t['metrica_descricao']}")

    # 4. APACHE BEAM E RUNTIMES (RF25)
    if args.etapa in ("beam", "todas"):
        logger.info(">>> [4/5] Executando Etapa 3 / RF25: Pipeline Apache Beam e Comparador de Runtimes")
        rel_beam = executar_comparacao_runtimes_beam(config=config, tentar_spark=True, logger=logger)
        print(f"[OK] Pipeline Beam executado:")
        print(f"     DirectRunner: {rel_beam['direct_runner']['status']} | {rel_beam['direct_runner']['registros_gold_gerados']} KPIs gerados")
        print(f"     SparkRunner: {rel_beam['spark_runner']['status']}")
        print(f"     Relatório JSON: dados/processados/resultado_execucao_beam.json")
        print(f"     Documentação MD: documentacao/execucao_beam_spark.md")

    # 5. PUBLICAÇÃO CAMADA GOLD (RF26)
    if args.etapa in ("gold", "todas"):
        logger.info(">>> [5/5] Executando Etapa 4 / RF26: Publicação Analítica na Camada Gold do PostgreSQL")
        res_gold = publicar_camada_gold(config=config, logger=logger)
        print(f"[OK] Camada Gold publicada com sucesso no PostgreSQL:")
        print(f"     Tabela gold.kpis_mensais_categoria: {res_gold['total_kpis_mensais_carregados']} linhas")
        print(f"     Tabela gold.desempenho_conteudos: {res_gold['total_conteudos_carregados']} linhas")
        print(f"     Visões analíticas disponíveis: gold.vw_kpis_executivos e gold.vw_ranking_conteudos_engajamento")

    duracao_total = round(perf_counter() - inicio, 4)
    logger.info("Execução da etapa %s concluída em %.4f segundos.", args.etapa.upper(), duracao_total)
    print(f"\n>>> Execução concluída em {duracao_total}s.")


if __name__ == "__main__":
    main()
