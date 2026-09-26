"""Definição de esquemas e tipos estritos para a camada Silver e Parquet (RF24)."""
from __future__ import annotations

import pyarrow as pa

# Esquema oficial para o dataset de Interações em formato Parquet
ESQUEMA_INTERACOES_PARQUET = pa.schema([
    pa.field("interacao_id", pa.int64(), nullable=False),
    pa.field("usuario_id", pa.int64(), nullable=False),
    pa.field("conteudo_id", pa.int64(), nullable=False),
    pa.field("tipo_interacao", pa.string(), nullable=False),
    pa.field("data_hora", pa.string(), nullable=False),
    pa.field("tempo_consumido_min", pa.float64(), nullable=False),
    pa.field("percentual_conclusao", pa.float64(), nullable=False),
    pa.field("avaliacao", pa.float64(), nullable=True),
    # Campos de Auditoria Corporativa (RF24 / Governança)
    pa.field("_data_ingestao", pa.string(), nullable=False),
    pa.field("_lote_id", pa.string(), nullable=False),
    pa.field("_origem", pa.string(), nullable=False),
    # Dimensões de Particionamento Físico
    pa.field("ano", pa.int32(), nullable=False),
    pa.field("mes", pa.int32(), nullable=False),
])

def obter_esquema_interacoes() -> pa.Schema:
    """Retorna o esquema PyArrow formal para o dataset de interações."""
    return ESQUEMA_INTERACOES_PARQUET
