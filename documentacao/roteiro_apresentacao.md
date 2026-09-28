# Roteiro Oficial de Apresentação e Demonstração Prática

**Curso:** FIC_DEV — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA — Desafio Prático 2  
**Equipe:** Diego Assunção Leite, Gabriel Moreira Branco, Gabriel André de Siqueira Nonato  
**Tempo Total:** 12 a 15 minutos (distribuído entre os integrantes)

---

## 1. Preparação do Ambiente (Deixar Aberto Antes de Começar)

- **Aba 1 (Documentação / Navegador):** `documentacao/arquitetura_e_storytelling.html` (ou `storytelling.html` e `arquitetura.html`)
- **Aba 2 (Apache Hop Web):** `http://localhost:8080` com `workflow_principal.hwf` aberto e nós em verde
- **Aba 3 (OpenMetadata):** `http://localhost:8585` (login `admin@openmetadata.org` / `admin`) na aba *Lineage* ou *Glossary*
- **Aba 4 (Apache Superset):** `http://localhost:8088` logado no **`Dashboard - Desafio 4`**
- **Terminal (VS Code):** Ambiente virtual ativo (`.venv`), pronto para rodar `python -m pytest tests/`

---

## 2. Introdução: Contextualização e Arquitetura (1 a 2 min)

- **O que mostrar:** `documentacao/arquitetura.html` ou diagrama do `README.md`.
- **Pontos-chave para falar:**
  - Projeto é a evolução do Desafio 1 para um **Data Lakehouse corporativo** sob o padrão da **Arquitetura Medalhão**.
  - O fluxo é **100% reproduzível, auditável, governado e idempotente**, coberto por 98 testes automatizados.
  - Adotamos uma **Arquitetura Híbrida**:
    - **ETL na Borda:** Apache Hop extrai, limpa e quarentena dados antes de gravar na Silver.
    - **ELT no Core:** Dados validados são exportados para Parquet colunar no Lakehouse, processados sob demanda por Apache Beam e consolidados na Gold.
  - A divisão de responsabilidades da equipe cobriu todo o ciclo de vida:
    - **Estudante 1:** Ingestão heterogênea, Apache Hop, Bronze, Silver e Quarentena.
    - **Estudante 2:** Parquet colunar Hive, Apache Beam (DirectRunner/Spark), Quality Gate e Camada Gold.
    - **Estudante 3:** Governança no OpenMetadata, LGPD, SQL Lab e BI no Apache Superset.

---

## 3. Bloco 1: Ingestão, Apache Hop, Bronze, Silver e Quarentena (3 a 4 min)

- **O que mostrar:** Apache Hop Web (`http://localhost:8080`), sub-workflow `carga_bronze_silver.hwf` e logs de execução.
- **Pontos-chave para falar:**
  - **Fontes Heterogêneas (Estágio 1):** Ingestão de 3 fontes distintas:
    - Catálogo educacional estruturado em CSV (`catalogo.csv`).
    - Telemetria de consumo em JSON (`interacoes.json`).
    - Avaliações dissertativas semiestruturadas no MongoDB (`coleção comentarios`).
  - **Camada Bronze (Estágio 2):**
    - Carga bruta 1:1 sem perdas de schema.
    - Enriquecimento obrigatório com metadados de auditoria: `_origem`, `_ingestao_em` e `_run_id` (UUID).
    - Permite rastrear a origem exata e o momento de cada linha ingerida.
  - **Camada Silver e Quarentena (Estágio 3):**
    - Padronização de tipos de dados, normalização de datas ISO 8601 e reconciliação MDM (Golden Record).
    - **Tratamento de Anomalias:** Dados inconsistentes (ex.: notas fora da escala 1 a 5 ou conteúdos órfãos) não quebram o pipeline.
    - São desviados para a tabela `quarentena.registros` com payload original preservado e diagnóstico do erro.
    - 8 registros anômalos foram isolados com sucesso sem contaminar o banco analítico.
  - **Idempotência:** Timestamps e controle de execução no schema `controle` evitam duplicidades em caso de reprocessamento.

---

## 4. Bloco 2: Parquet Hive, Apache Beam, Qualidade e Camada Gold (4 min)

- **O que mostrar:** Terminal rodando `python -m pytest tests/`, diretórios particionados de Parquet e tabela `gold.desempenho_conteudos`.
- **Pontos-chave para falar:**
  - **Armazenamento Colunar Parquet (RF24):**
    - Exportação da Silver para Parquet particionado no padrão Hive por ano e mês (`ano=YYYY/mes=MM/part-0.parquet`).
    - Habilita *Partition Pruning* e *Pushdown de Projeção* (consultas analíticas leem só as colunas solicitadas).
    - **Resultados Empíricos do Benchmark:**
      - Redução de **72,16% no tamanho comparado ao CSV** (36 KB vs 129 KB).
      - Redução de **89,44% comparado ao JSON** (36 KB vs 341 KB).
      - Tempo de leitura de projeção caiu para **1,08 ms**.
  - **Processamento Distribuído com Apache Beam (RF25):**
    - Pipeline com transformações determinísticas e agregações `CombinePerKey`.
    - Computa KPIs analíticos mensais sem dependência de locks relacionais.
    - Executado e homologado no **DirectRunner** (0,477s) e auditado para o runtime Spark do cluster Docker.
    - Resultados rigorosamente equivalentes entre os runtimes.
  - **Motor de Qualidade de Dados — Quality Gate (RF31):**
    - Implementação de 5 dimensões formais de qualidade:
      - *Completude:* Tolerância zero a nulos em chaves mandatórias.
      - *Validade:* Notas obrigatoriamente no intervalo de 1 a 5.
      - *Unicidade:* Chaves primárias sem duplicação.
      - *Consistência:* Percentual de conclusão entre 0 e 100%.
      - *Integridade Referencial:* Vínculo estrito entre interações e catálogo.
    - **Política de Bloqueio:** Falha crítica interrompe a carga imediatamente (`FalhaQualidadeDadosCriticaError`), blindando a Camada Gold.
    - 100% aprovado na base de produção (bloqueio comprovado de 75% nos testes anômalos).
  - **Camada Gold (RF26):**
    - Tabelas `gold.kpis_mensais_categoria` (64 agregações) e `gold.desempenho_conteudos` (1.000 conteúdos consolidados).
    - Publicação via UPSERT idempotente para servir diretamente o consumo.

---

## 5. Bloco 3: Governança OpenMetadata, LGPD e Apache Superset (4 a 5 min)

- **O que mostrar:** OpenMetadata (`http://localhost:8585`) nas telas de Linhagem e Glossário, e Superset (`http://localhost:8088`) no Dashboard.
- **Pontos-chave para falar no OpenMetadata (RF27-RF30, RF32-RF33):**
  - **Abordagem Metadata as Code:** Automação total via API REST oficial, dispensando os daemons pesados do Airflow (economia de mais de 3 GB de RAM).
  - **Catálogo Multi-Serviço:**
    - 13 tabelas catalogadas com **Owner `admin`** em 4 Tiers:
      - Gold: *Tier 1* | Silver: *Tier 2* | Bronze: *Tier 3* | Fontes: *Tier 4*.
    - Serviço dedicado **`ficdev_mongodb`** (NoSQL MongoDB) integrado ao lado do **`ficdev_postgres`**.
  - **Linhagem Ponta a Ponta (19 Arestas):**
    - Grafo visual contínuo: Fontes (CSV, JSON, MongoDB) $\rightarrow$ Bronze $\rightarrow$ Silver $\rightarrow$ Gold $\rightarrow$ Superset.
  - **Glossário de Negócio Formal:**
    - 4 termos de negócio padronizados com fórmulas matemáticas explícitas e vinculados diretamente às colunas físicas (*Usuário Ativo*, *Taxa de Conclusão*, *Tempo Médio de Consumo*, *Conversão de Recomendação*).
  - **Proteção de Dados e LGPD:**
    - Tag **`PII.Sensitive`** aplicada nas colunas sensíveis em todas as camadas (`autor`, `usuario_id`, `comentario`).
    - Comprovação técnica de mascaramento, pseudonimização com UUIDv5 e hashing irreversível SHA-256 com salt.

- **Pontos-chave para falar no Apache Superset e Storytelling (RF16-RF18):**
  - **Narrativa Executiva (Storytelling em 3 Atos):**
    - *Ato 1 (Alta Satisfação):* Plataforma bem avaliada (nota média global de **4,51 de 5,00**).
    - *Ato 2 (O Gargalo de Evasão):* Grande contraste de retenção por formato:
      - Podcasts: **95,24% de conversão** (40 conclusões em 42 inícios).
      - Vídeos: **89,80% de conversão** (44 conclusões em 49 inícios).
      - Artigos: **84,00% de conversão** (42 conclusões em 50 inícios).
      - **Cursos:** Ponto crítico de evasão com **apenas 60,87% de conversão** (18 alunos abandonaram após o início).
    - *Ato 3 (Mapa de 12 Segmentos):*
      - *Curso Intermediário* e *Podcast Avançado* registraram **0,00% de conclusão**, exigindo reformulação.
      - *Curso Avançado* possui a maior nota de satisfação da plataforma (**4,80**), porém menor volume de acessos (18).
  - **Interatividade por Filtros Cruzados (Cross-Filtering):**
    - Demonstrar ao vivo: clicar na fatia de "Curso" no gráfico de pizza e mostrar os demais gráficos recalculando instantaneamente.
  - **Datasets Virtuais no SQL Lab (RF17):**
    - Cruzamento analítico com classificação condicional de engajamento via `CASE WHEN`.
  - **Alerta Automatizado de Negócio (RF18):**
    - Alerta configurado no Superset que notifica a coordenação se o tempo médio cair abaixo de 500 minutos ou a taxa de conclusão recuar abaixo de 40%.

---

## 6. Encerramento (1 min)

- **Pontos-chave para falar:**
  - Sistema entrega a união completa de **DataOps, Governança e BI Executivo**.
  - 100% coberto por 98 testes automatizados, documentação técnica formal e relatórios em HTML.
  - Agradecer e abrir para perguntas da banca.

---

## 7. Respostas Rápidas para Perguntas Prováveis da Banca

- **"O que vocês chamam de Data Lake e o que chamam de Data Warehouse?"**
  - *Data Lake:* Diretório colunar aberto de arquivos Parquet particionados Hive com compressão Snappy, processados de forma distribuída pelo Beam.
  - *Data Warehouse:* Camadas Silver e Gold estruturadas no PostgreSQL, com integridade referencial, queries SQL rápidas e views que alimentam o Superset.
  - *Data Lakehouse:* A arquitetura completa integrada, unindo os arquivos abertos do Lake com o controle, qualidade e governança do Warehouse.

- **"Por que gravar no MongoDB e depois jogar no PostgreSQL?"**
  - *Separação OLTP vs OLAP:* MongoDB recebe escritas dinâmicas em tempo real da aplicação web; PostgreSQL processa análises pesadas sem concorrer por CPU/memória com os alunos.
  - *Junções Heterogêneas:* O PostgreSQL permite cruzar os comentários do Mongo com o CSV do catálogo e com os logs JSON da telemetria de forma indexada.
  - *Qualidade e BI:* O dado passa por validação e quarentena no Hop antes de alimentar o Superset com SQL ANSI padrão.

- **"Por que a arquitetura é classificada como Híbrida (ETL + ELT)?"**
  - *ETL na borda:* Hop extrai, limpa, valida e desvia erros para a quarentena antes de persistir na Silver.
  - *ELT no core:* Dados homologados são gravados em Parquet no Lakehouse; Beam e views SQL transformam e agregam sob demanda diretamente sobre o storage.

- **"Por que desativaram o Airflow no OpenMetadata?"**
  - Container do Airflow consumia mais de 3 GB de RAM ocioso. Adotamos o padrão *Metadata as Code* via API REST oficial, reduzindo 60% da memória com 100% de automação do catálogo, glossário e linhagem em segundos.

- **"O que acontece se entrar um dado com erro no pipeline?"**
  - Se for na ingestão Hop: é isolado na tabela `quarentena.registros` com payload original e diagnóstico.
  - Se for na esteira analítica Beam: o *Quality Gate* barra a execução com `FalhaQualidadeDadosCriticaError`, impedindo publicação de dados corrompidos na Camada Gold.
