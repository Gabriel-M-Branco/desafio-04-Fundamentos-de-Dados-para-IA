# Documentação Técnica da Plataforma

Índice consolidado dos documentos técnicos, relatórios de engenharia e artefatos do projeto (**Desafio Prático 4 / 2º Desafio do Módulo de Fundamentos de Dados para IA — FIC_DEV**).

---

## 1. Arquitetura, Modelagem e Fundamentos
- [especificacao_tecnica.md](especificacao_tecnica.md): Especificação técnica completa de arquitetura de dados, modelagem relacional, armazenamento no MongoDB e motor de recomendação.
- [arquitetura_etl_elt.md](arquitetura_etl_elt.md): Classificação do fluxo entre ETL e ELT, justificativas sob custo, governança, desempenho e limitações dos scripts isolados (RF19).
- [modelo-dados.pdf](modelo-dados.pdf): Diagramas conceituais, lógicos e relacionais das entidades do banco de dados.
- [arquitetura.pdf](arquitetura.pdf): Visão gráfica da arquitetura em camadas e fluxo de dados.
- [kpis.md](kpis.md): Especificação formal dos KPIs, fórmulas matemáticas, views analíticas e perguntas de negócio.
- [uso_da_ia.md](uso_da_ia.md): Relatório de governança, ética e transparência no uso de ferramentas de Inteligência Artificial.

---

## 2. Ingestão, Padronização e Orquestração (Apache Hop)
- [especificacao_bronze_silver.md](especificacao_bronze_silver.md): Detalhamento dos contratos de entrada e saída das camadas Bronze e Silver, regras de negócio e tipagem.
- [contrato_integracao_pipeline.md](contrato_integracao_pipeline.md): Definição de contratos e interfaces de integração entre a ingestão Hop e o motor analítico Beam.
- [evidencias_bronze_silver.md](evidencias_bronze_silver.md): Evidências auditáveis de execução, tempos de processamento e logs das camadas Bronze e Silver.

---

## 3. Processamento Distribuído, Qualidade e Camada Gold
- [benchmark_parquet.md](benchmark_parquet.md): Metodologia, medições e análise comparativa de performance colunar (Parquet particionado Hive vs CSV vs JSON — RF24).
- [execucao_beam_spark.md](execucao_beam_spark.md): Comparação de runtimes do Apache Beam (DirectRunner vs Apache Spark), diagnóstico de ambiente e instruções reproduzíveis (RF25).
- [qualidade_dados.md](qualidade_dados.md): Especificação formal das 5 dimensões corporativas de qualidade de dados avaliadas, limites, severidades e histórico (RF31).
- [camada_gold.md](camada_gold.md): Modelagem dimensional da camada Gold, granularidade, medidas pré-agregadas e visões analíticas para consumo no Superset (RF26).

---

## 4. Governança, Proteção de Dados e Catálogo (OpenMetadata)
- [governanca_openmetadata.md](governanca_openmetadata.md): Guia de governança, tutorial de catálogo via API REST (*Metadata as Code*), glossário, classificação LGPD e linhagem gráfica (RF27 a RF30, RF32).
- [dados_mestres.md](dados_mestres.md): Especificação de Master Data Management (MDM), correspondência de entidades (Matching Rules) e Golden Record para conteúdos educacionais (RF30).



