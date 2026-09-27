"""Ponto de entrada oficial para execução do pipeline Apache Beam (RF25).

Atende rigorosamente à estrutura de entregáveis da Seção 11 do Desafio Prático 2:
    beam/pipeline.py

Execução direta:
    python beam/pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para resolução de pacotes internos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.beam.pipeline_gold import executar_pipeline_gold_beam
from src.config import carregar_config

if __name__ == "__main__":
    config = carregar_config()
    print("=================================================================")
    print("EXECUÇÃO DO PIPELINE APACHE BEAM — CAMADA GOLD (RF25)")
    print("=================================================================")
    resultado = executar_pipeline_gold_beam(
        config=config,
        runner="DirectRunner",
        lote_id="LOTE_BEAM_SECAO11_OFICIAL",
    )
    print(f"Runner utilizado: {resultado['runner']}")
    print(f"Lote ID: {resultado['lote_id']}")
    print(f"Registros lidos da Silver (Parquet): {resultado['registros_lidos']}")
    print(f"Registros analíticos consolidados: {resultado['registros_gold_gerados']}")
    print(f"Duração do processamento: {resultado['duracao_segundos']}s")
    print(f"Destino Parquet: {resultado['caminho_parquet_saida']}")
    print(f"Tamanho do arquivo: {resultado['tamanho_parquet_bytes']} bytes")
    print("=================================================================")
