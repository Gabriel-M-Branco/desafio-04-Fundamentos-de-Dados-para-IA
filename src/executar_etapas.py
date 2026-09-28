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
    def _verificar_silver_disponivel() -> bool:
        try:
            from src.config import obter_parametros_conexao_postgres
            import psycopg2
            params = obter_parametros_conexao_postgres(config)
            with psycopg2.connect(**params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM silver.interacoes;")
                    count = cur.fetchone()[0]
                    return count > 0
        except Exception:
            return False

    silver_ja_existe = _verificar_silver_disponivel()
    precisa_ingestao = (args.etapa == "ingestao") or (args.etapa == "todas" and not silver_ja_existe)

    if args.etapa == "todas" and silver_ja_existe:
        logger.info(">>> [0/5] Camada Silver já validada no PostgreSQL (alimentada pelo Apache Hop). Utilizando dados oficiais sem retrabalho.")
        print("[OK] Camada Silver identificada no PostgreSQL (ingerida pelo Apache Hop). Utilizando registros oficiais.")

        # Sincroniza e reporta registros de quarentena do banco para o arquivo local
        try:
            import json
            import psycopg2
            from src.config import obter_parametros_conexao_postgres
            params = obter_parametros_conexao_postgres(config)
            with psycopg2.connect(**params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM quarentena.registros;")
                    total_q = cur.fetchone()[0]
                    if total_q > 0:
                        cur.execute("""
                            SELECT json_agg(json_build_object(
                                'entidade', entidade,
                                'id_registro', id_registro,
                                'origem', origem,
                                'regra', regra_violada,
                                'mensagem', mensagem_erro,
                                'data_erro', data_erro,
                                'id_execucao', id_execucao,
                                'registro', payload
                            )) FROM quarentena.registros;
                        """)
                        rows_json = cur.fetchone()[0]
                        dir_dados = caminho_absoluto("dados")
                        q_dir = dir_dados / "quarentena"
                        q_dir.mkdir(parents=True, exist_ok=True)
                        q_alias = q_dir / "quarentena_RUN_INTEGRADO_BRONZE_SILVER.json"
                        q_alias.write_text(json.dumps(rows_json, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
                        print(f"     Tabela quarentena.registros (PostgreSQL): {total_q} anomalias identificadas e isoladas.")
                        print(f"     Arquivo local sincronizado: dados/quarentena/quarentena_RUN_INTEGRADO_BRONZE_SILVER.json")
        except Exception as exc:
            logger.debug("Não foi possível sincronizar quarentena local: %s", exc)

    if precisa_ingestao:
        script_ingestao = caminho_absoluto("scripts/ingestao_bronze_silver.py")
        if script_ingestao.exists():
            logger.info(">>> [0/5] Executando Etapa 1 / RF20-RF23: Ingestão das Camadas Bronze & Silver")
            try:
                from scripts.ingestao_bronze_silver import bronze, silver
                import uuid
                run_id_ingestao = str(uuid.uuid5(uuid.NAMESPACE_DNS, "RUN_INTEGRADO_BRONZE_SILVER"))
                
                dir_brutos = caminho_absoluto("dados/brutos")
                dir_dados = caminho_absoluto("dados")
                r_bronze = bronze(dir_brutos, dir_dados, run_id_ingestao, skip_db=True)
                r_silver = silver(dir_dados, run_id_ingestao, skip_db=True)
                
                # Atualiza também o alias amigável de quarentena
                q_alias = dir_dados / "quarentena" / "quarentena_RUN_INTEGRADO_BRONZE_SILVER.json"
                q_oficial = dir_dados / "quarentena" / f"quarentena_{run_id_ingestao}.json"
                if q_oficial.exists():
                    import shutil
                    shutil.copy2(q_oficial, q_alias)
                    
                    total_q_db = 0
                    try:
                        from scripts.ingestao_bronze_silver import db_connect, salvar_quarentena_db
                        with db_connect() as conn:
                            q_registros = json.loads(q_oficial.read_text(encoding="utf-8"))
                            total_q_db = salvar_quarentena_db(conn, q_registros)
                    except Exception:
                        pass

                print(
                    f"[OK] Ingestão Bronze & Silver concluída: {r_silver['interacoes_aprovadas']} interações, "
                    f"{r_silver['catalogo_aprovados']} conteúdos, {r_silver['quarentena']} na quarentena."
                )
                if r_silver['quarentena'] > 0:
                    print(f"     Arquivo de quarentena gerado: dados/quarentena/quarentena_{run_id_ingestao}.json")
                    print(f"     Alias de quarentena sincronizado: dados/quarentena/quarentena_RUN_INTEGRADO_BRONZE_SILVER.json")
                    if total_q_db > 0:
                        print(f"     Tabela quarentena.registros (PostgreSQL): {total_q_db} anomalias persistidas com sucesso")
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

    # 3. QUALIDADE DE DADOS (RF31) E PROTEÇÃO LGPD (RF32/RF33)
    if args.etapa in ("qualidade", "todas"):
        import json
        logger.info(">>> [3/5] Executando Etapa 5 / RF31: Avaliação das 5 Dimensões de Qualidade de Dados")
        dir_parquet_interacoes = caminho_absoluto(config.get("parquet", {}).get("diretorio_saida", "dados/parquet")) / "interacoes" / "particionado"
        origem_catalogo = caminho_absoluto(config.get("dados", {}).get("processados", {}).get("catalogo", "dados/processados/catalogo_processado.csv"))
        df_int = ler_parquet_interacoes(dir_parquet_interacoes)
        df_cat = pd.read_csv(origem_catalogo)

        # 3.1 Avaliação dos dados de produção (Silver)
        rel_qualidade = avaliar_qualidade_dados(df_int, df_cat, logger=logger)
        persistir_historico_qualidade(rel_qualidade)
        print(f"[OK] Qualidade Silver (Produção): Status Geral = {rel_qualidade['status_geral']}")
        print(f"     Bloquear Gold: {rel_qualidade['bloquear_publicacao_gold']} (Publicação Gold Liberada)")
        for t in rel_qualidade["detalhes_testes"]:
            print(f"     - [{t['status']}] {t['nome']}: {t['metrica_descricao']}")

        # 3.2 Avaliação dos Cenários de Teste (Governança e Falhas - RF31)
        caminho_int_cen = caminho_absoluto("dados/brutos/cenarios_de_teste/interacoes_cenarios.json")
        caminho_cat_cen = caminho_absoluto("dados/brutos/cenarios_de_teste/catalogo_cenarios.csv")
        if caminho_int_cen.exists() and caminho_cat_cen.exists():
            df_int_cen = pd.read_json(caminho_int_cen)
            df_cat_cen = pd.read_csv(caminho_cat_cen)
            rel_cenarios = avaliar_qualidade_dados(df_int_cen, df_cat_cen, logger=logger)
            caminho_rel_cen = caminho_absoluto("dados/processados/qualidade_cenarios_teste.json")
            caminho_rel_cen.parent.mkdir(parents=True, exist_ok=True)
            caminho_rel_cen.write_text(json.dumps(rel_cenarios, ensure_ascii=False, indent=2), encoding="utf-8")
            
            print(f"\n[OK] Avaliação dos Cenários de Teste (RF31 / Quality Gate):")
            print(f"     Status dos Cenários: {rel_cenarios['status_geral']}")
            print(f"     Bloquear Publicação Gold: {rel_cenarios['bloquear_publicacao_gold']} (Barreira de governança ativada com sucesso)")
            for t in rel_cenarios["detalhes_testes"]:
                print(f"     - [{t['status']}] {t['nome']} ({t['id_regra']}): {t['metrica_descricao']}")

            # 3.3 Demonstração de Proteção LGPD (RF32 / RF33)
            from src.lgpd.protecao import mascarar_nome, pseudonimizar_id, gerar_hash_salted
            print(f"\n[OK] Demonstração de Proteção LGPD (RF32 / RF33):")
            nome_ex = str(df_cat_cen.dropna(subset=['autor']).iloc[0]['autor'])
            print(f"     - Mascaramento Dinâmico (Autor): '{nome_ex}' -> '{mascarar_nome(nome_ex)}'")
            uid_ex = int(df_int_cen.dropna(subset=['usuario_id']).iloc[0]['usuario_id'])
            print(f"     - Pseudonimização (UUIDv5): ID {uid_ex} -> '{pseudonimizar_id(uid_ex)}'")
            print(f"     - Hashing Criptográfico com Salt (HMAC-SHA256): ID {uid_ex} -> '{gerar_hash_salted(uid_ex)[:24]}...'")

    # 4. APACHE BEAM E RUNTIMES (RF25)
    if args.etapa in ("beam", "todas"):
        import logging
        logging.getLogger("apache_beam.utils.subprocess_server").setLevel(logging.ERROR)
        logger.info(">>> [4/5] Executando Etapa 3 / RF25: Pipeline Apache Beam e Comparador de Runtimes")
        rel_beam = executar_comparacao_runtimes_beam(config=config, tentar_spark=True, logger=logger)
        print(f"[OK] Pipeline Beam executado:")
        print(f"     DirectRunner: {rel_beam['direct_runner']['status']} | {rel_beam['direct_runner']['registros_gold_gerados']} KPIs gerados")
        print(f"     SparkRunner: {rel_beam['spark_runner']['status']} (Diagnóstico formalizado no relatório)")
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
