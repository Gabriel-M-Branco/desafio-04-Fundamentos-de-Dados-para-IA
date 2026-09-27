# Plataforma Integrada de Engenharia de Dados e Inteligência Artificial

Projeto desenvolvido para o **Desafio Prático 4 do Curso FIC_DEV — Programador de Sistemas com IA**, correspondente ao **2º Desafio do Módulo de Fundamentos de Dados para IA**.

O projeto consolida uma arquitetura corporativa moderna de ponta a ponta: ingestão heterogênea e orquestrada com Apache Hop (Bronze e Silver), persistência poliglota com PostgreSQL e MongoDB, geração de embeddings semânticos e motor de recomendação com IA, particionamento colunar Parquet em padrão Hive, processamento distribuído com Apache Beam, motor de governança de qualidade de dados com barreiras críticas e camada Gold analítica consumida via Apache Superset.

---

## Identificação Acadêmica

- **Curso:** FIC_DEV — Programador de Sistemas com IA
- **Módulo:** Fundamentos de Dados para IA
- **Contexto:** Desafio Prático 4 do Curso / 2º Desafio do Módulo de Dados para IA
- **Instituição:** SECITECI / Escola Técnica Estadual de Cuiabá
- **Turma:** Vespertino — 2026
- **Equipe:**
  - Diego Assunção Leite
  - Gabriel Moreira Branco
  - Gabriel André de Siqueira Nonato
- **Repositório:** [https://github.com/Gabriel-M-Branco/desafio-04-Fundamentos-de-Dados-para-IA](https://github.com/Gabriel-M-Branco/desafio-04-Fundamentos-de-Dados-para-IA)

---

## Arquitetura Unificada do Sistema

A solução adota o padrão **Medallion Architecture (Bronze / Silver / Gold)** combinado com conceitos de **Data Lakehouse** e **IA Integrada**:

```mermaid
flowchart TD
    subgraph Fontes["1. Fontes de Dados Heterogêneas"]
        F1["catalogo.csv - Catálogo Educacional"]
        F2["interacoes.json - Consumo dos Alunos"]
        F3["comentarios.json - Feedbacks e Avaliações"]
    end

    subgraph Hop["2. Ingestão e Governança no Apache Hop"]
        H1["bronze_pipelines - Ingestão e Auditoria Raw"]
        H2["silver_pipelines - Tipagem e Validação"]
        H3["quarentena.registros - Isolamento de Falhas"]
        H4["controle.execucao - Logs e Rastreabilidade"]
    end

    subgraph Armazenamento["3. Armazenamento Poliglota e IA"]
        PG_RAW["PostgreSQL - Schemas bronze e silver"]
        MG["MongoDB - Comentários e Avaliações"]
        EMB["SentenceTransformers + pgvector - Embeddings"]
        REC["Motor de Recomendação Personalizada"]
    end

    subgraph Processamento["4. Processamento Analítico e Qualidade"]
        PQ["Parquet Particionado Hive - ano=YYYY/mes=MM"]
        QUAL["Motor de Qualidade - 5 Dimensões"]
        BEAM["Apache Beam - DirectRunner e Spark"]
    end

    subgraph Consumo["5. Camada Analítica e Visualização"]
        GOLD["PostgreSQL - Schema gold"]
        SUPERSET["Apache Superset e SQL Lab"]
    end

    F1 --> H1
    F2 --> H1
    F3 --> H1
    H1 --> PG_RAW
    H1 --> H2
    H2 -- "Válidos" --> PG_RAW
    H2 -- "Inválidos" --> H3
    H1 --> H4
    H2 --> H4

    PG_RAW --> MG
    PG_RAW --> EMB
    EMB --> REC

    PG_RAW --> PQ
    PQ --> BEAM
    PQ --> QUAL
    QUAL -- "Gate Aprovado" --> GOLD
    BEAM --> GOLD
    GOLD --> SUPERSET
```

---

## Guia de Instalação e Execução Multiplataforma

O projeto foi configurado com **caminhos 100% relativos** e conteinerização completa, garantindo execução estável no **Windows**, **macOS** e nas **principais distribuições Linux** (Ubuntu/Debian, Fedora/RHEL, Arch).

### 1. Pré-requisitos
- **Git** instalado.
- **Docker** e **Docker Compose** (Docker Desktop no Windows/macOS ou Docker Engine + Compose plugin no Linux).
- **Python 3.10 ou superior** instalado localmente.

---

### 2. Clonar e Acessar o Repositório

```bash
git clone https://github.com/Gabriel-M-Branco/desafio-04-Fundamentos-de-Dados-para-IA.git
cd desafio-04-Fundamentos-de-Dados-para-IA
```

---

### 3. Configurar o Ambiente Virtual (Python venv)

Selecione o seu sistema operacional:

#### No Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### No Windows (Prompt de Comando — CMD):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

#### No macOS e Linux (Ubuntu, Debian, Fedora, Arch):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 4. Instalar as Dependências

Com o ambiente virtual ativo:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 5. Configurar o Arquivo de Variáveis de Ambiente (`.env`)

O arquivo `.env.example` já inclui os parâmetros padronizados para execução local no Docker:

#### No Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### No macOS / Linux:
```bash
cp .env.example .env
```

> **Dica:** Os valores padrão do `.env.example` funcionam perfeitamente para testes locais em contêiner.

---

### 6. Subir a Infraestrutura (Docker Compose)

Inicie todos os serviços do ecossistema:
```bash
docker compose up -d
```

Verifique se todos os contêineres estão saudáveis e operacionais:
```bash
docker compose ps
```

| Serviço | Contêiner | Porta | Finalidade |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | `postgres` | `5432` | Banco relacional, extensão pgvector e schemas Medalhão (`bronze`, `silver`, `gold`, `quarentena`, `controle`). |
| **MongoDB** | `mongodb` | `27017` | Persistência NoSQL orientada a documentos para avaliações e comentários. |
| **Apache Hop Web** | `hop-web` | `8080` | Interface visual de ETL para execução dos workflows e pipelines. |
| **Spark Job Server** | `spark-job-server` | `8098:8099` | Runtime distribuído de processamento Apache Spark para Beam. |
| **Apache Superset** | `superset` | `8088` | Plataforma analítica de BI, consultas SQL Lab e dashboards. |
| **OpenMetadata Server** | `openmetadata-server` | `8585` | Catálogo de dados, linhagem ponta a ponta e governança (RF27-RF30). |
| **Elasticsearch** | `openmetadata-elasticsearch` | `9200` | Motor de busca e indexação de metadados para o OpenMetadata. |

---

### 7. Execução do Pipeline Ponta a Ponta

Para executar toda a plataforma de forma sequencial e integrada, siga as 3 etapas abaixo:

#### Etapa A: Carga Base, IA e Embeddings (Motor Legado e Pré-requisitos)
Gera o catálogo de conteúdos, carrega o MongoDB, calcula embeddings com `sentence-transformers` na extensão `pgvector` e gera as recomendações personalizadas:

```bash
python -m src.main
```

> Este comando garante a presença das referências em `public.usuarios` e `public.conteudos`, que são validadas na etapa de integridade referencial do Apache Hop.

#### Etapa B: Ingestão e Padronização Bronze & Silver (Apache Hop)
O Apache Hop lê os arquivos de `dados/brutos/`, grava a camada bruta com metadados de auditoria em `bronze.*`, valida e tipa em `silver.*`, isola inconsistências em `quarentena.registros` e loga etapas em `controle`.

Você pode rodá-lo por **qualquer uma das opções**:

- **Opção 1 — Pela Interface Web (Hop Web no Navegador — Play):**
  1. Acesse no navegador: [http://localhost:8080](http://localhost:8080).
  2. Na árvore de arquivos à esquerda (pasta `default`), dê dois cliques na pasta **`workflows`** e abra **`workflow_principal.hwf`** (ou use o ícone de pasta amarela no menu superior para abrir).
  3. Com o fluxograma aberto na tela, clique no ícone de **Play (▶ Executar)** na barra superior do fluxo.
  4. Na janela de diálogo, selecione a run configuration **`local`** e clique em **Launch**.
  
- **Opção 2 — Pela Linha de Comando (Headless via Docker):**
  ```bash
  docker exec hop-web /usr/local/tomcat/webapps/ROOT/hop-run.sh \
    --environment desafio4-dev \
    --project desafio4 \
    --file /files/workflows/workflow_principal.hwf \
    --runconfig local \
    --level BASIC
  ```

#### Etapa C: Parquet, Qualidade, Apache Beam e Camada Gold
Com as camadas Bronze e Silver povoadas no PostgreSQL e Parquet, execute a esteira analítica distribuída:

```bash
python -m src.executar_etapas --etapa todas
```

O orquestrador executará de forma encadeada:
1. **RF24 (Parquet Hive):** Exporta 1.000 registros para partição colunar (`dados/parquet/interacoes/particionado/ano=2026/mes=MM/`).
2. **RF24 (Benchmark):** Executa o teste comparativo de performance de leitura colunar (Parquet vs CSV vs JSON).
3. **RF31 (Qualidade de Dados):** Executa os 5 testes corporativos (Completude, Validade, Unicidade, Consistência e Integridade Referencial).
4. **RF25 (Apache Beam):** Agrega os KPIs analíticos mensais e de desempenho via DirectRunner e avalia o cluster Spark.
5. **RF26 (Camada Gold):** Publica as agregações na camada `gold` do PostgreSQL (`kpis_mensais_categoria`, `desempenho_conteudos` e visões analíticas).

---

## Verificação e Conferência dos Resultados

### 1. No PostgreSQL
Para auditar a volumetria populada em todas as camadas da arquitetura Medalhão:

```bash
docker exec -it postgres psql -U postgres -d ficdev_recomendacao -c "
SELECT 'bronze.catalogo_raw' as tabela, count(*) FROM bronze.catalogo_raw
UNION ALL SELECT 'bronze.interacoes_raw', count(*) FROM bronze.interacoes_raw
UNION ALL SELECT 'bronze.comentarios_raw', count(*) FROM bronze.comentarios_raw
UNION ALL SELECT 'silver.catalogo', count(*) FROM silver.catalogo
UNION ALL SELECT 'silver.interacoes', count(*) FROM silver.interacoes
UNION ALL SELECT 'silver.comentarios', count(*) FROM silver.comentarios
UNION ALL SELECT 'quarentena.registros', count(*) FROM quarentena.registros
UNION ALL SELECT 'controle.execucao_workflow', count(*) FROM controle.execucao_workflow
UNION ALL SELECT 'gold.kpis_mensais_categoria', count(*) FROM gold.kpis_mensais_categoria
UNION ALL SELECT 'gold.desempenho_conteudos', count(*) FROM gold.desempenho_conteudos;
"
```

### 2. No MongoDB
Consulte a coleção semiestruturada e teste agregações:
```bash
python -c "from src.config import carregar_config; from src.database.mongo import agregar_por_categoria; print(agregar_por_categoria(carregar_config()))"
```

### 3. Testes Automatizados da Aplicação
Execute a suíte com **84 testes automatizados**:
```bash
python -m pytest tests/
```

### 4. No Apache Superset (Consumo Analítico)
1. Acesse no navegador: [http://localhost:8088](http://localhost:8088).
2. Credenciais padrão: usuário `admin` e senha `admin` (conforme `.env`).
3. Conecte-se ao banco `postgresql://postgres:postgres@postgres:5432/ficdev_recomendacao`.
4. Os datasets devem consultar exclusivamente a camada **`gold`**:
   - `gold.kpis_mensais_categoria`
   - `gold.desempenho_conteudos`
   - `gold.vw_kpis_executivos`
   - `gold.vw_ranking_conteudos_engajamento`

---

## Especificação Técnica dos Módulos

### 1. Ingestão e Governança com Apache Hop (RF20 a RF23)
- **Schema `bronze`:** Ingestão das fontes brutas com campos de metadados: `origem`, `data_hora_ingestao` e `id_execucao`.
- **Schema `silver`:** Padronização e tipagem de campos, desduplicação por chaves de negócio e validação referencial.
- **Schema `quarentena`:** Isolamento de linhas rejeitadas com diagnóstico e payload JSON íntegro na tabela `quarentena.registros`.
- **Schema `controle`:** Rastreabilidade por lote e etapas nas tabelas `execucao_workflow` e `execucao_etapa`.
- **Portabilidade:** Todos os fluxos utilizam `${Internal.Workflow.Filename.Folder}` e `${Internal.Pipeline.Filename.Folder}`, sem dependências de caminhos absolutos locais.

### 2. Armazenamento Poliglota e Inteligência Artificial (RF06 a RF11)
- **PostgreSQL com pgvector:** Armazenamento vetorial com índices para busca por similaridade de cosseno.
- **MongoDB:** Armazenamento de avaliações e comentários desnormalizados para agregação flexível.
- **SentenceTransformers:** Embeddings multilíngues gerados com `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões).
- **Motor de Recomendação:** Fórmula ponderada de afinidade (`Ivis`), curtidas (`Icur`) e filtro de conclusão (`Iconc`).

### 3. Formato Colunar e Particionamento Parquet Hive (RF24)
- **Particionamento:** Estrutura Hive por período (`ano=YYYY/mes=MM`) para *partition pruning*.
- **Tipagem Estrita:** Esquema imutável via PyArrow preservando campos de auditoria corporativa.
- **Benchmark:** Redução de ~89% no volume em disco comparado ao JSON e ganhos expressivos em tempo de consulta com projeção colunar.
- **Relatório Técnico:** [`documentacao/benchmark_parquet.md`](documentacao/benchmark_parquet.md).

### 4. Processamento Distribuído com Apache Beam e Spark (RF25)
- **Pipeline:** Transformações em janela com `beam.CombinePerKey` determinístico para cálculo de métricas educacionais.
- **Runtimes:** DirectRunner validado e diagnóstico completo de execução distribuída via Spark Job Server.
- **Relatório Técnico:** [`documentacao/execucao_beam_spark.md`](documentacao/execucao_beam_spark.md).

### 5. Motor de Qualidade de Dados (RF31)
- **5 Dimensões Avaliadas:**
  1. *Completude (Q01):* Taxa de preenchimento de campos obrigatórios.
  2. *Validade (Q02):* Conformidade com regras de intervalo (notas 1 a 5, percentuais 0 a 100%).
  3. *Unicidade (Q03):* Ausência de chaves primárias duplicadas.
  4. *Consistência (Q04):* Coerência entre conclusão de conteúdo e percentual de término.
  5. *Integridade Referencial (Q05):* Ausência de registros órfãos sem correspondência no catálogo.
- **Barreira Bloqueadora (Quality Gate):** Falhas críticas impedem a escrita e publicação na Gold (`FalhaQualidadeDadosCriticaError`).
- **Relatório Técnico:** [`documentacao/qualidade_dados.md`](documentacao/qualidade_dados.md).

### 6. Camada Gold para Consumo Analítico (RF26)
- **Modelagem Analítica:** Tabelas `gold.kpis_mensais_categoria` e `gold.desempenho_conteudos` e visões analíticas de suporte.
- **Desacoplamento:** O consumo analítico consulta estritamente a Gold, blindando as camadas Bronze e Silver de sobrecargas.
- **Relatório Técnico:** [`documentacao/camada_gold.md`](documentacao/camada_gold.md).

---

## Estrutura do Repositório

```text
desafio-04-Fundamentos-de-Dados-para-IA/
├── config/                  # Configuração funcional da aplicação (YAML)
├── dados/                   # Camadas de dados físicas (brutos, parquet e processados)
│   ├── brutos/              # Fontes originais (catalogo.csv, interacoes.json, comentarios.json)
│   ├── parquet/             # Dados colunares particionados (Hive) e saídas analíticas
│   └── processados/         # Resultados intermediários, histórico de qualidade e benchmarks
├── dashboard/               # Pacotes de exportação e sincronização com Apache Superset
├── documentacao/            # Relatórios técnicos aprofundados e especificações formais
├── hop/                     # Projeto Apache Hop (workflows .hwf, pipelines .hpl e metadados)
│   ├── environments/        # Configuração de variáveis por ambiente
│   ├── metadata/            # Conexões de banco de dados e run configurations
│   ├── pipelines/           # Pipelines de ingestão Bronze e Silver
│   └── workflows/           # Workflows orquestradores de execução
├── mongodb/                 # Scripts e consultas de agregação NoSQL
├── sql/                     # DDLs relacionais, DDLs Medalhão e consultas SQL
├── src/                     # Código-fonte Python modular
│   ├── beam/                # Pipelines analíticos e comparador de runtimes Apache Beam
│   ├── database/            # Conectores PostgreSQL e MongoDB
│   ├── gold/                # Publicador e modelador da Camada Gold
│   ├── ingestao/            # Validação e processamento de dados
│   ├── parquet/             # Exportador particionado e benchmark colunar
│   ├── qualidade/           # Motor de avaliação das 5 dimensões de qualidade
│   └── recomendacao/        # Embeddings com SentenceTransformers e busca semântica
├── tests/                   # Suíte de 84 testes automatizados (Pytest)
├── docker-compose.yml       # Orquestração de todos os serviços conteinerizados
├── requirements.txt         # Dependências Python versionadas
├── .env.example             # Modelo de configuração de variáveis de ambiente
└── README.md                # Documentação técnica e guia unificado de execução
```

---

## Sumário da Documentação Complementar

Para aprofundamento técnico em cada módulo específico, consulte:

- [`documentacao/especificacao_tecnica.md`](documentacao/especificacao_tecnica.md): Especificação de modelagem relacional, pgvector e motor de recomendação.
- [`documentacao/benchmark_parquet.md`](documentacao/benchmark_parquet.md): Metodologia e resultados do benchmark empírico Parquet vs CSV vs JSON.
- [`documentacao/execucao_beam_spark.md`](documentacao/execucao_beam_spark.md): Comparação de runtimes Apache Beam (DirectRunner vs Spark) e compatibilidade de ambiente.
- [`documentacao/qualidade_dados.md`](documentacao/qualidade_dados.md): Regras formais, fórmulas, severidades e histórico das 5 dimensões de qualidade.
- [`documentacao/camada_gold.md`](documentacao/camada_gold.md): Modelagem dimensional, granularidade, medidas e visões analíticas da Gold.
- [`documentacao/kpis.md`](documentacao/kpis.md): Definição de métricas de negócio e indicadores de decisão pedagógicos.
- [`documentacao/uso_da_ia.md`](documentacao/uso_da_ia.md): Registro de governança sobre o uso de ferramentas de Inteligência Artificial.
- [`hop/README.md`](hop/README.md): Documentação detalhada dos workflows e pipelines do Apache Hop.

---

## Autores

- **Diego Assunção Leite**
- **Gabriel Moreira Branco**
- **Gabriel André de Siqueira Nonato**

**Curso:** FIC_DEV — Programador de Sistemas com IA  
**Instituição:** SECITECI / Escola Técnica Estadual de Cuiabá  
**Ano:** 2026
