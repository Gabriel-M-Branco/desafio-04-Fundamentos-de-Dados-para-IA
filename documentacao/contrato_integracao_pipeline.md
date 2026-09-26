# Contrato de Integração do Pipeline

A etapa de ingestão entrega `hop/workflows/carga_bronze_silver.hwf` e `scripts/ingestao_bronze_silver.py`, executáveis até a camada Silver.

Na integração final da equipe, a esteira executa o encadeamento:
1. Ingestão Bronze e Silver (`carga_bronze_silver.hwf` / `scripts/ingestao_bronze_silver.py`);
2. Avaliação de Qualidade e Gate Bloqueador (RF31 - `src/qualidade/avaliador.py`);
3. Exportação e Particionamento Hive em Parquet (RF24 - `src/parquet/exportador.py`);
4. Processamento Analítico com Apache Beam e Spark (RF25 - `src/beam/pipeline_gold.py`);
5. Publicação da Camada Gold no PostgreSQL (RF26 - `src/gold/publicador.py`);
6. Catálogo, Linhagem e Governança no OpenMetadata (RF27-RF30) e Consumo no Superset (RF16-RF18).

Uma falha crítica de qualidade impede a publicação da camada Gold.
