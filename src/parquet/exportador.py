"""Módulo de exportação de dados da camada Silver para Parquet com particionamento (RF24)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
import uuid

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.config import caminho_absoluto
from src.parquet.esquema import obter_esquema_interacoes


def carregar_dados_silver_interacoes(caminho_origem: Path | str) -> list[dict[str, Any]]:
    """Carrega os dados de interações da camada Silver."""
    caminho = Path(caminho_origem)
    if not caminho.is_absolute():
        caminho = caminho_absoluto(str(caminho_origem))

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de origem da Silver não encontrado: {caminho}")

    if caminho.suffix.lower() == ".json":
        with caminho.open("r", encoding="utf-8") as f:
            dados = json.load(f)
            if not isinstance(dados, list):
                raise ValueError("O arquivo JSON de interações deve conter uma lista de objetos.")
            return dados
    elif caminho.suffix.lower() == ".csv":
        df = pd.read_csv(caminho)
        return df.to_dict(orient="records")
    elif caminho.suffix.lower() == ".parquet":
        df = pd.read_parquet(caminho)
        return df.to_dict(orient="records")
    else:
        raise ValueError(f"Formato não suportado para leitura da Silver: {caminho.suffix}")


def preparar_tabela_interacoes_arrow(
    registros: list[dict[str, Any]],
    lote_id: str | None = None,
    origem: str = "silver/interacoes",
    timestamp_ingestao: str | None = None,
) -> pa.Table:
    """Valida, converte e enriquece registros com campos de auditoria e partição."""
    if not registros:
        raise ValueError("A lista de registros para exportação Parquet não pode estar vazia.")

    agora_iso = timestamp_ingestao or datetime.now(timezone.utc).isoformat()
    lote = lote_id or f"LOTE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    linhas_preparadas = []
    for idx, reg in enumerate(registros):
        # Extrai ano e mes do campo data_hora (ISO format: YYYY-MM-DDTHH:MM:SS ou datetime)
        dt_val = reg.get("data_hora", "")
        if isinstance(dt_val, (pd.Timestamp, datetime)):
            dt_str = dt_val.strftime("%Y-%m-%dT%H:%M:%S")
            ano = dt_val.year
            mes = dt_val.month
        else:
            dt_str = str(dt_val).replace(" ", "T")
            try:
                partes_data = dt_str.split("T")[0].split("-")
                ano = int(partes_data[0])
                mes = int(partes_data[1])
            except (IndexError, ValueError) as err:
                raise ValueError(f"Campo data_hora inválido para extração de partição temporal: '{dt_str}'") from err

        # Mapeia avaliacao ou avaliacao_atribuida
        avaliacao = reg.get("avaliacao")
        if avaliacao is None or (isinstance(avaliacao, float) and pd.isna(avaliacao)):
            avaliacao = reg.get("avaliacao_atribuida")

        if avaliacao is not None and pd.notna(avaliacao):
            avaliacao_float = float(avaliacao)
        else:
            avaliacao_float = None

        # Mapeia tempo consumido em minutos
        tempo_min = reg.get("tempo_consumido_min")
        if tempo_min is None or (isinstance(tempo_min, float) and pd.isna(tempo_min)):
            tempo_min = reg.get("tempo_consumido", 0.0)

        # Mapeia interacao_id com fallback seguro para índice
        interacao_id = reg.get("interacao_id")
        if interacao_id is None or pd.isna(interacao_id):
            interacao_id = idx + 1

        linha = {
            "interacao_id": int(interacao_id),
            "usuario_id": int(reg["usuario_id"]),
            "conteudo_id": int(reg["conteudo_id"]),
            "tipo_interacao": str(reg["tipo_interacao"]).strip(),
            "data_hora": dt_str,
            "tempo_consumido_min": float(tempo_min),
            "percentual_conclusao": float(reg["percentual_conclusao"]),
            "avaliacao": avaliacao_float,
            "_data_ingestao": agora_iso,
            "_lote_id": lote,
            "_origem": origem,
            "ano": ano,
            "mes": mes,
        }
        linhas_preparadas.append(linha)

    df = pd.DataFrame(linhas_preparadas)
    esquema = obter_esquema_interacoes()
    tabela = pa.Table.from_pandas(df, schema=esquema, preserve_index=False)
    return tabela


def carregar_dados_silver_do_banco(config: dict[str, Any] | None = None, logger: Any = None) -> list[dict[str, Any]] | None:
    """Tenta carregar interações diretamente da tabela silver.interacoes do PostgreSQL (produzida pelo Apache Hop)."""
    try:
        from src.config import carregar_config, obter_parametros_conexao_postgres
        import psycopg2
        if config is None:
            config = carregar_config()
        params = obter_parametros_conexao_postgres(config)
        with psycopg2.connect(**params) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT interacao_id, usuario_id, conteudo_id, tipo_interacao, 
                           data_hora, tempo_consumido_min, percentual_conclusao, avaliacao
                    FROM silver.interacoes
                    ORDER BY interacao_id;
                """)
                cols = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                if rows:
                    if logger:
                        logger.info("Carregados %d registros diretamente da tabela PostgreSQL silver.interacoes (gerada pelo Apache Hop).", len(rows))
                    return [dict(zip(cols, row)) for row in rows]
    except Exception as exc:
        if logger:
            logger.debug("Não foi possível carregar silver.interacoes do PostgreSQL (%s), usando fallback de arquivo.", exc)
    return None


def exportar_interacoes_parquet(
    config: dict[str, Any],
    particionado: bool = True,
    lote_id: str | None = None,
    logger: Any = None,
) -> dict[str, Any]:
    """Exporta o conjunto da Silver para Parquet (particionado ou arquivo único).

    Retorna dicionário com métricas de execução e caminhos gerados.
    """
    inicio = perf_counter()
    cfg_parquet = config.get("parquet", {})
    origem_rel = cfg_parquet.get("origem_silver_interacoes", "dados/processados/interacoes_processadas.json")
    dir_saida_rel = cfg_parquet.get("diretorio_saida", "dados/parquet")
    compressao = cfg_parquet.get("compressao", "snappy")
    particionar_por = cfg_parquet.get("particionar_por", ["ano", "mes"])

    caminho_origem = caminho_absoluto(origem_rel)
    dir_saida = caminho_absoluto(dir_saida_rel) / "interacoes"
    dir_saida.mkdir(parents=True, exist_ok=True)

    registros = None
    if origem_rel == "dados/processados/interacoes_processadas.json":
        registros = carregar_dados_silver_do_banco(config, logger=logger)

    if not registros:
        if logger:
            logger.info("Iniciando exportação Parquet da fonte Silver em arquivo: %s", caminho_origem)
        registros = carregar_dados_silver_interacoes(caminho_origem)
    else:
        if logger:
            logger.info("Exportando %d registros da tabela PostgreSQL silver.interacoes para Parquet.", len(registros))

    tabela = preparar_tabela_interacoes_arrow(registros, lote_id=lote_id)

    if particionado:
        destino_final = dir_saida / "particionado"
        destino_final.mkdir(parents=True, exist_ok=True)
        # Escreve dataset particionado
        ds.write_dataset(
            tabela,
            base_dir=str(destino_final),
            format="parquet",
            partitioning=particionar_por,
            partitioning_flavor="hive",
            file_options=ds.ParquetFileFormat().make_write_options(compression=compressao),
            existing_data_behavior="overwrite_or_ignore",
        )
    else:
        destino_final = dir_saida / f"interacoes_consolidado_{compressao}.parquet"
        pq.write_table(tabela, destino_final, compression=compressao)

    duracao_seg = round(perf_counter() - inicio, 4)

    # Mede tamanho total gerado em bytes
    if destino_final.is_dir():
        arquivos = list(destino_final.rglob("*.parquet"))
        tamanho_bytes = sum(f.stat().st_size for f in arquivos)
        qtd_arquivos = len(arquivos)
    else:
        tamanho_bytes = destino_final.stat().st_size
        qtd_arquivos = 1

    resultado = {
        "formato": "parquet",
        "particionado": particionado,
        "particoes_usadas": particionar_por if particionado else [],
        "caminho_destino": str(destino_final),
        "total_registros": len(registros),
        "total_arquivos": qtd_arquivos,
        "tamanho_bytes": tamanho_bytes,
        "tamanho_kb": round(tamanho_bytes / 1024, 2),
        "compressao": compressao,
        "duracao_segundos": duracao_seg,
        "lote_id": tabela.column("_lote_id")[0].as_py(),
    }

    if logger:
        logger.info(
            "Exportação Parquet concluída | registros=%d | arquivos=%d | tamanho=%.2f KB | duracao=%.4fs",
            resultado["total_registros"],
            resultado["total_arquivos"],
            resultado["tamanho_kb"],
            duracao_seg,
        )

    return resultado


if __name__ == "__main__":
    from src.config import carregar_config
    from src.logging_utils import configurar_logger

    configuracao = carregar_config()
    log = configurar_logger(caminho_absoluto(configuracao["logs"]["arquivo"]))
    log.info("Executando exportação oficial da Silver para Parquet particionado...")
    res = exportar_interacoes_parquet(configuracao, particionado=True, logger=log)
    print(f"Exportação Parquet concluída: {res['total_registros']} registros em {res['total_arquivos']} arquivos. Destino: {res['caminho_destino']}")
