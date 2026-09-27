# Arquitetura de Dados: Definição, Classificação e Trade-offs (RF19)

Este documento atende formalmente ao requisito funcional **RF19** do Desafio Prático 2 (**FIC_DEV — Fundamentos de Dados para IA**), especificando a topologia de dados, a classificação do fluxo entre ETL e ELT, as justificativas sob a ótica de custo, governança, desempenho e reprocessamento, além de contrastar a arquitetura atual com as limitações dos scripts isolados do Desafio 1.

---

## 1. Representação do Fluxo: Das Fontes ao Consumo

A plataforma foi arquitetada sobre o padrão **Medallion Architecture (Bronze $\to$ Silver $\to$ Gold)** integrado a um **Data Lakehouse com IA**, garantindo isolamento de camadas, auditoria contínua e rastreabilidade total:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       1. FONTES HETEROGÊNEAS (Dados Brutos)                                     │
│  • Catálogo Educacional (CSV)       • Interações de Alunos (JSON)       • Avaliações e Comentários (JSON)       │
└──────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────┘
                                                       │
                                      [ E: Extração via Apache Hop ]
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   2. CAMADA BRONZE (Cópia Auditável Imutável)                                   │
│  • Ingestão raw em tabelas dedicadas: bronze.conteudos, bronze.interacoes, bronze.comentarios                  │
│  • Metadados de auditoria técnica: data_ingestao, origem_dado, job_id                                          │
└──────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────┘
                                                       │
                           [ T: Validação, Tipagem, Deduplicação e Quarentena no Hop ]
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 3. CAMADA SILVER (Dados Padronizados e Confiáveis)                              │
│  • Schemas tipados e higienizados: silver.conteudos, silver.interacoes, silver.comentarios                     │
│  • Segregação ativa de inconsistências: quarentena.registros_invalidos                                         │
└───────────────────────────┬─────────────────────────────────────────────────────────┬───────────────────────────┘
                            │                                                         │
               [ L: Carga Poliglota & IA ]                              [ L: Exportação Hive Parquet ]
                            ▼                                                         ▼
┌──────────────────────────────────────────────────────┐  ┌───────────────────────────────────────────────────────┐
│           PERSISTÊNCIA OPERACIONAL & VETORIAL        │  │         DATA LAKEHOUSE (Parquet Particionado)         │
│ • PostgreSQL (Tabelas operacionais + pgvector)       │  │ • Particionamento Hive: categoria=.../data=...       │
│ • MongoDB (Comentários e tags desnormalizadas)       │  │ • Compressão colunar Snappy + estatísticas nativas   │
└──────────────────────────────────────────────────────┘  └───────────────────────────┬───────────────────────────┘
                                                                                      │
                                                                   [ E + T: Leitura e Agregação no Beam ]
                                                                   [ T: Data Quality Gate - 5 Dimensões ]
                                                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   4. CAMADA GOLD (Consumo Analítico e Decisão)                                  │
│  • Tabelas agregadas e dimensionais: gold.kpis_mensais_categoria, gold.desempenho_conteudos                     │
│  • Bloqueio automático de publicação via barreira de qualidade (QualityGateBlockError)                          │
└──────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────┘
                                                       │
                                        [ Consumo e Governança ]
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    5. CONSUMO ANALÍTICO & GOVERNANÇA ATIVA                                      │
│  • Apache Superset: Dashboards executivos, gráficos de linha/séries temporais, filtros cruzados e alertas       │
│  • SQL Lab: Consultas analíticas e Virtual Datasets baseados na Gold                                            │
│  • OpenMetadata: Catálogo técnico, glossário de negócio, classificações PII e linhagem ponta a ponta            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Identificação das Etapas de Extração (E), Transformação (T) e Carga (L)

O ecossistema implementa uma separação cirúrgica de responsabilidades em cada fronteira do pipeline:

| Estágio do Pipeline | Componente Responsável | Operação | Descrição Técnica Detalhada |
| :--- | :--- | :---: | :--- |
| **Ingestão Primária** | Apache Hop (`carga_bronze.hpl`) | **Extração (E)** | Leitura desacoplada dos arquivos heterogêneos originais (`catalogo.csv`, `interacoes.json`, `comentarios.json`) a partir de `dados/brutos/`. |
| **Persistência Raw** | Apache Hop (`carga_bronze.hpl`) | **Carga (L)** | Carga atômica nos schemas brutos do PostgreSQL (`bronze.*`), acrescentando colunas de controle (`data_ingestao`, `origem_dado`, `job_id`) sem perdas ou mutações destrutivas. |
| **Higienização e Refinamento** | Apache Hop (`carga_silver.hpl`) | **Transformação (T)** | Normalização textual, conversão de formatos de data (ISO 8601), validação de tipos, verificação de integridade referencial em memória e bifurcação condicional: registros inconsistentes são desviados para `quarentena.registros_invalidos`. |
| **Persistência Refinada** | Apache Hop (`carga_silver.hpl`) | **Carga (L)** | Gravação dos registros aprovados nas tabelas de confiança (`silver.conteudos`, `silver.interacoes`, `silver.comentarios`). |
| **Preparação Lakehouse** | Script PyArrow (`src/parquet/exportador.py`) | **Extração & Carga (E/L)** | Extração da Silver e carga colunar em formato Parquet no diretório `dados/parquet/`, particionado na árvore Hive (`categoria=.../data=...`). |
| **Processamento Distribuído** | Apache Beam (`src/beam/pipeline_gold.py`) | **Extração & Transformação (E/T)** | Leitura das partições Parquet, cruzamento multidimensional via *Side Input*, computação de métricas comutativas e associativas com `CombinePerKey` e cálculo dos KPIs de vazão e engajamento. |
| **Barreira de Qualidade** | Quality Gate (`src/qualidade/avaliador.py`) | **Transformação (T)** | Avaliação determinística de 5 dimensões de qualidade (completude, validade, unicidade, consistência, integridade). Falhas críticas abortam a publicação da Gold via exceção bloqueante (`QualityGateBlockError`). |
| **Publicação Analítica** | Publicador Gold (`src/gold/publicador.py`) | **Carga (L)** | Gravação idempotente das visões e tabelas agregadas (`gold.kpis_mensais_categoria` e `gold.desempenho_conteudos`), prontas para consulta rápida pelo Superset e SQL Lab. |

---

## 3. Classificação Arquitetural: Arquitetura Híbrida (ETL + ELT)

O fluxo principal do projeto classifica-se formalmente como uma **Arquitetura Híbrida (ETL na Borda e ELT no Core / Data Lakehouse)**:

1. **Abordagem ETL (Extract-Transform-Load) na Ingestão:**
   * Ocorre entre os arquivos brutos e a camada Silver via **Apache Hop**.
   * **Por que ETL aqui?** Dados de fontes externas possuem formatações inconsistentes, nulos anômalos e IDs corrompidos. Aplicar a transformação e o desvio para a quarentena *antes* de carregar a Silver garante que a base intermediária seja estritamente confiável e governada (Clean Data Ingestion).

2. **Abordagem ELT (Extract-Load-Transform) no Core Analítico:**
   * Ocorre a partir da camada Silver em direção à camada Gold via **Parquet + Apache Beam + SQL**.
   * **Por que ELT aqui?** Os dados padronizados são carregados imediatamente em formato bruto colunar (Parquet no Data Lakehouse) sem predeterminar todas as visões analíticas. A partir do Parquet, múltiplos motores (Apache Beam, Spark, SQL PostgreSQL) podem extrair, aplicar filtros sob demanda e transformar os dados em agregações analíticas (Gold) sem a necessidade de reprocessar a ingestão primária.

---

## 4. Justificativa Técnica da Arquitetura Escolhida

A escolha da Arquitetura Híbrida foi motivada por quatro pilares essenciais de engenharia de dados:

### 4.1 Custo Computacional e de Infraestrutura
* **Redução de Custo de Armazenamento:** A exportação da Silver para Parquet com compressão Snappy proporcionou uma redução média de **75% no tamanho dos arquivos em disco** comparado a CSV/JSON brutos (comprovado no benchmark de `RF24`), diminuindo drasticamente os custos de storage em nuvem ou disco local.
* **Otimização de Processamento (Pushdown de Filtros):** Consultas analíticas leem apenas as colunas e partições necessárias (`categoria=...`), evitando varreduras completas de tabela (*full table scans*) e minimizando o uso de memória e CPU.

### 4.2 Governança e Qualidade de Dados
* **Rastreabilidade e Imutabilidade:** A existência da camada **Bronze** garante que qualquer alteração de regra futura possa auditar o dado como ele chegou da fonte.
* **Isolamento de Falhas com Quarentena:** Em vez de abortar pipelines por causa de registros defeituosos, a arquitetura isola o dado inválido na tabela `quarentena.registros_invalidos` com carimbo de data, regra violada e payload original. O fluxo continua para os dados saudáveis, e o dado com defeito pode ser corrigido e reprocessado.
* **Quality Gate Bloqueante:** A camada Gold possui garantia matemática de conformidade: se um teste crítico falhar (ex: unicidade de PK ou referência a conteúdo inexistente), a Gold não é atualizada com dados inconsistentes.

### 4.3 Desempenho e Escalabilidade
* **Desacoplamento de Cargas Transacionais e Analíticas:** O Apache Superset consome exclusivamente a camada Gold (pré-agregada). Usuários de dashboards e cientistas de dados não geram consultas concorrentes na camada Bronze ou OLTP, garantindo tempos de resposta sub-segundo nas visualizações.
* **Processamento Paralelo Massivo:** O Apache Beam desacopla a regra de negócio da execução física, permitindo que a mesma lógica rode localmente com `DirectRunner` ou seja distribuída em nós de um cluster `Apache Spark`.

### 4.4 Reprocessamento e Idempotência
* **Idempotência Garantida:** Tanto as cargas do Apache Hop quanto o publicador Gold operam com cláusulas de idempotência (`ON CONFLICT DO UPDATE` / recriação transacional de partições).
* **Reprocessamento Histórico Desacoplado:** Caso surja um novo KPI ou uma métrica precise ser recalculada, não é necessário acionar as fontes brutas ou o Hop: o Apache Beam pode ler diretamente o histórico consolidado na Silver/Parquet e recalcular a Gold em segundos.

---

## 5. Limitações da Solução Anterior (Desafio 1: Scripts Isolados)

No Desafio Prático 1, o fluxo de dados era executado por meio de um script monolítico em Python (`python -m src.main`). Essa abordagem apresentava limitações arquiteturais severas que foram superadas no Desafio 2:

| Aspecto | Solução Anterior (Desafio 1 — Scripts Isolados) | Solução Evoluída (Desafio 2 — Lakehouse Híbrido) |
| :--- | :--- | :--- |
| **Orquestração** | Execução procedural síncrona em Python puro; ausência de workflow visual, dependências declarativas e controle automático de retry. | Workflows orquestrados no **Apache Hop** (`.hwf`), com execução orientada a grafos de dependência, paralelismo nativo e logs persistidos. |
| **Tolerância a Falhas** | Uma exceção de validação ou de rede no meio da execução derrubava todo o processo, gerando cargas parciais corrompidas no PostgreSQL. | Tratamento defensivo com desvio para **Quarentena** no Hop e transações atômicas com rollback em caso de falha crítica. |
| **Auditoria e Linhagem** | Os registros eram inseridos diretamente nas tabelas finais sem metadados de lote, horário de ingestão ou identificador de job. | Schemas Medallion com colunas `data_ingestao`, `origem_dado` e `job_id`, integradas à catalogação do **OpenMetadata**. |
| **Escalabilidade de Dados** | Leitura total dos arquivos JSON e CSV carregados inteiramente na memória RAM da máquina hospedeira (inviável para gigabytes/terabytes). | Processamento colunar fatiado em **Parquet particionado** e motor distribuído **Apache Beam** com suporte a computação em cluster Spark. |
| **Camadas de Acesso** | O Superset consultava visões diretamente sobre as tabelas transacionais que recebiam carga, causando contenção de leitura/escrita. | Separação estrita: consumo analítico isolado na camada **Gold**, alimentada apenas após aprovação no **Data Quality Gate**. |
| **Reprocessamento** | Qualquer reprocessamento exigia apagar o banco inteiro e rodar novamente todo o script do zero, incluindo o custoso cálculo de embeddings. | Arquitetura desacoplada: é possível reprocessar a quarentena via SQL pontual, reexecutar apenas a Gold via Beam, ou ingerir novos lotes incrementalmente. |
