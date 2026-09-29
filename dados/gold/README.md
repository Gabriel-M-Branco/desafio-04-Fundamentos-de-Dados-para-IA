# Camada Gold — Exportações Analíticas Físicas (RF26)

Este diretório contém os instantâneos físicos das tabelas analíticas da camada **Gold** em formatos colunar Parquet e tabular CSV, gerados pelo pipeline de publicação após validação pelo Quality Gate (RF31).

## Arquivos Disponíveis

1. **`kpis_mensais_categoria.parquet` / `kpis_mensais_categoria.csv`:**
   - Granularidade: `(ano, mes, categoria)`
   - Medidas agregadas: total de visualizações, inícios, conclusões, curtidas, taxa de conclusão média, tempo total consumido e avaliação média.
   - Gerado pelo pipeline distribuído Apache Beam a partir das interações colunares limpas.

2. **`desempenho_conteudos.parquet` / `desempenho_conteudos.csv`:**
   - Granularidade: `(conteudo_id)`
   - Dimensões: título, tipo de conteúdo, categoria temática e nível didático.
   - Medidas de engajamento consolidadas para alimentar o Storytelling executivo no Apache Superset.

As tabelas correspondentes em banco relacional encontram-se persistidas e indexadas no schema `gold` do PostgreSQL (`gold.kpis_mensais_categoria` e `gold.desempenho_conteudos`).
