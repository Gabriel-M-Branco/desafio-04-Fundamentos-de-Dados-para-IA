"""Pipeline Apache Beam para geração da camada Gold analítica (RF25)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
import uuid

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.config import caminho_absoluto, carregar_config
from src.beam.transformacoes import (
    ConsolidarMetricasCategoria,
    ExtrairChaveCategoriaMes,
    FormatarRegistroGoldCategoria,
)
from src.parquet.leitor import ler_parquet_interacoes


def carregar_mapa_catalogo(caminho_catalogo: Path | str) -> dict[int, dict[str, Any]]:
    """Carrega o catálogo e cria mapa indexado por conteudo_id para Side Input."""
    caminho_p = Path(caminho_catalogo)
    if not caminho_p.is_absolute():
        caminho_p = caminho_absoluto(str(caminho_catalogo))

    if caminho_p.suffix.lower() == ".csv":
        df = pd.read_csv(caminho_p)
    elif caminho_p.suffix.lower() == ".json":
        df = pd.read_json(caminho_p)
    else:
        raise ValueError(f"Formato não suportado para catálogo: {caminho_p}")

    mapa = {}
    for _, row in df.iterrows():
        cid = int(row["conteudo_id"])
        mapa[cid] = {
            "titulo": str(row.get("titulo", "")),
            "categoria": str(row.get("categoria", "")),
            "tipo": str(row.get("tipo", "")),
            "nivel": str(row.get("nivel", "")),
        }
    return mapa


class ColetorSaida(beam.DoFn):
    """Auxiliar para coletar registros em memória durante a execução."""

    def __init__(self, lista_destino: list[dict[str, Any]]):
        self.lista_destino = lista_destino

    def process(self, elemento: dict[str, Any]):
        self.lista_destino.append(elemento)
        yield elemento


def executar_pipeline_gold_beam(
    config: dict[str, Any] | None = None,
    runner: str = "DirectRunner",
    pipeline_args: list[str] | None = None,
    lote_id: str | None = None,
    logger: Any = None,
) -> dict[str, Any]:
    """Executa o pipeline Apache Beam para consolidar KPIs da camada Gold."""
    inicio = perf_counter()
    if config is None:
        config = carregar_config()

    cfg_parquet = config.get("parquet", {})
    dir_parquet_interacoes = caminho_absoluto(cfg_parquet.get("diretorio_saida", "dados/parquet")) / "interacoes" / "particionado"
    origem_catalogo = caminho_absoluto(config.get("dados", {}).get("processados", {}).get("catalogo", "dados/processados/catalogo_processado.csv"))

    if not dir_parquet_interacoes.exists():
        raise FileNotFoundError(
            f"Diretório Parquet de interações não encontrado: {dir_parquet_interacoes}. "
            "Execute a etapa de exportação Parquet (RF24) antes do Beam."
        )

    lote = lote_id or f"LOTE_BEAM_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    agora_iso = datetime.now(timezone.utc).isoformat()

    if logger:
        logger.info("Iniciando Pipeline Apache Beam | Runner: %s | Lote: %s", runner, lote)
        logger.info("Origem Parquet: %s", dir_parquet_interacoes)

    # 1. Carrega dados de entrada
    df_interacoes = ler_parquet_interacoes(dir_parquet_interacoes)
    registros_interacoes = df_interacoes.to_dict(orient="records")
    total_lidos = len(registros_interacoes)

    mapa_catalogo = carregar_mapa_catalogo(origem_catalogo)

    # 2. Configura opções do Pipeline
    opcoes = PipelineOptions(pipeline_args or [])
    opcoes.view_as(beam.options.pipeline_options.StandardOptions).runner = runner

    dir_gold_temp = caminho_absoluto("dados/processados/beam_temp_gold")
    dir_gold_temp.mkdir(parents=True, exist_ok=True)
    prefixo_saida_temp = str(dir_gold_temp / "gold_kpi_part")

    # Limpa arquivos temporários anteriores se existirem
    for f_antigo in dir_gold_temp.glob("gold_kpi_part*"):
        f_antigo.unlink()

    # 3. Monta e executa o Pipeline Beam
    with beam.Pipeline(options=opcoes) as p:
        # PCollection de interações
        p_interacoes = p | "Criar Coleção Interações" >> beam.Create(registros_interacoes)

        # Agrupamento e agregação com CombinePerKey
        kpis_agregados = (
            p_interacoes
            | "Extrair Chave Categoria e Mês" >> beam.ParDo(ExtrairChaveCategoriaMes(), mapa_catalogo=mapa_catalogo)
            | "Consolidar Métricas de Negócio" >> beam.CombinePerKey(ConsolidarMetricasCategoria())
            | "Formatar para Camada Gold" >> beam.ParDo(FormatarRegistroGoldCategoria(lote_id=lote, data_carga=agora_iso))
            | "Serializar para JSON" >> beam.Map(lambda r: json.dumps(r, ensure_ascii=False))
            | "Gravar Partes Temporárias" >> beam.io.WriteToText(prefixo_saida_temp, file_name_suffix=".jsonl", shard_name_template="-SSSSS-of-NNNNN")
        )

    duracao_seg = round(perf_counter() - inicio, 4)

    # 4. Lê os shards gravados pelo Beam e consolida
    registros_gold_saida = []
    for arquivo_shard in dir_gold_temp.glob("gold_kpi_part*"):
        with arquivo_shard.open("r", encoding="utf-8") as f:
            for linha in f:
                linha_str = linha.strip()
                if linha_str:
                    registros_gold_saida.append(json.loads(linha_str))

    total_gerados = len(registros_gold_saida)

    # 5. Grava a saída consolidada em Parquet na pasta Gold
    dir_gold_parquet = caminho_absoluto("dados/parquet/gold")
    dir_gold_parquet.mkdir(parents=True, exist_ok=True)
    caminho_gold_parquet = dir_gold_parquet / "kpis_mensais_categoria.parquet"

    if registros_gold_saida:
        df_gold = pd.DataFrame(registros_gold_saida)
        df_gold.sort_values(by=["ano", "mes", "categoria"], inplace=True)
        tabela_gold = pa.Table.from_pandas(df_gold, preserve_index=False)
        pq.write_table(tabela_gold, caminho_gold_parquet, compression="snappy")
        tamanho_bytes = caminho_gold_parquet.stat().st_size
    else:
        tamanho_bytes = 0

    resultado = {
        "runner": runner,
        "lote_id": lote,
        "data_execucao": agora_iso,
        "registros_lidos": total_lidos,
        "registros_gold_gerados": total_gerados,
        "duracao_segundos": duracao_seg,
        "caminho_parquet_saida": str(caminho_gold_parquet),
        "tamanho_parquet_bytes": tamanho_bytes,
        "amostra_saida": registros_gold_saida[:3] if registros_gold_saida else [],
    }

    if logger:
        logger.info(
            "Pipeline Apache Beam finalizado com sucesso | lidos=%d | agregados_gold=%d | duracao=%.4fs | saida=%s",
            total_lidos,
            total_gerados,
            duracao_seg,
            caminho_gold_parquet,
        )

    return resultado
