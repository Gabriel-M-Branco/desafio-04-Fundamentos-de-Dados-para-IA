# Governança de Metadados e Catálogo — OpenMetadata (RF27 a RF30, RF32)

**Projeto:** Plataforma Integrada de Engenharia de Dados e Inteligência Artificial  
**Módulo:** Governança, Rastreabilidade e Catálogo de Dados (RF27, RF28, RF29, RF30 e RF32)  
**Plataforma Adotada:** OpenMetadata v1.4.6  
**Abordagem Arquitetural:** *Metadata as Code* via API REST Oficial  

---

## 1. Visão Geral e Arquitetura de Governança

O **OpenMetadata** atua como o repositório central de governança, metadados técnicos e semânticos da plataforma FIC_DEV. Ele resolve os problemas de:
1. **Pântano de Dados (*Data Swamp* — RF27):** Impede o consumo de tabelas desordenadas e fontes não auditadas. Apenas os esquemas homologados (`silver` e `gold`) são catalogados com donos (*owners*) e descrições técnicas obrigatórias.
2. **Ambiguidade Semântica (RF28):** Institui o Glossário de Negócio corporativo com 4 termos padronizados, vinculados diretamente às colunas das tabelas da camada Gold.
3. **Opacidade de Origem e Rastreabilidade (*Lineage* — RF29):** Garante a auditabilidade ponta a ponta por meio de um grafo de linhagem que conecta a origem na camada Silver aos modelos agregados da camada Gold.
4. **Proteção à Privacidade e LGPD (RF32):** Classifica colunas com atributos identificáveis com a taxonomia corporativa `PII.Sensitive`.

---

## 2. Abordagem de Integração: Por que via API REST (*Metadata as Code*)?

### O Desafio de Recursos do Docker e o "Test Connection"
Ao tentar cadastrar o conector PostgreSQL manualmente clicando no botão **"Test Connection"** da interface web, a interface retorna o erro:
```text
Failed to deploy pipeline [...] due to [No response from the test connection. Make sure your service is reachable and accepting connections]
```

**Diagnóstico Técnico:**
- A interface web do OpenMetadata não executa testes de conexão diretamente pelo seu servidor Java principal. Ela despacha um DAG para um container auxiliar do **Apache Airflow / Ingestion Framework**.
- No ambiente deste projeto, para que os estudantes possam executar PostgreSQL, MongoDB, Hop, Beam e Superset simultaneamente sem estourar a memória RAM da máquina (o que exigiria mais de 4 GB adicionais apenas para o Airflow), a ingestão agendada foi desabilitada no `docker-compose.yml` (`PIPELINE_SERVICE_CLIENT_ENABLED: "false"`).

### A Solução Corporativa: *Metadata as Code* via API REST v1
Adotou-se o padrão da indústria de **Governança como Código (*Metadata as Code*)**. O script Python [`scripts/configurar_openmetadata.py`](../scripts/configurar_openmetadata.py) interage diretamente com a API REST oficial do OpenMetadata (`http://localhost:8585/api/v1`), realizando o provisionamento completo de forma idempotente, auditável e instantânea.

---

## 3. Mapeamento das Chamadas à API REST

O script [`scripts/configurar_openmetadata.py`](../scripts/configurar_openmetadata.py) implementa o seguinte fluxo de chamadas HTTP:

| Etapa | Método | Endpoint da API | Ação Executada | Requisito |
| :--- | :---: | :--- | :--- | :---: |
| **1. Autenticação** | `POST` | `/api/v1/users/login` | Envia credenciais administrativas (`admin@openmetadata.org` / `admin` em Base64) e obtém token JWT Bearer. | RF15 / RF27 |
| **2. Serviço Postgres** | `POST` | `/api/v1/services/databaseServices` | Registra o serviço de banco de dados `ficdev_postgres` apontando para o host interno `postgres:5432`. | RF27 |
| **3. Database** | `POST` | `/api/v1/databases` | Registra a base de dados lógica `ficdev_postgres.ficdev_recomendacao`. | RF27 |
| **4. Schemas** | `POST` | `/api/v1/databaseSchemas` | Cria os esquemas de dados homologados `silver` e `gold`. | RF27 |
| **5. Tabelas & Colunas** | `POST` | `/api/v1/tables` | Registra os metadados técnicos de `silver.catalogo`, `gold.kpis_mensais_categoria` e `gold.desempenho_conteudos`, incluindo tipagem e descrições colunares. | RF27 / RF28 |
| **6. Classificação LGPD** | `PATCH` | `/api/v1/tables/{id}` | Aplica via JSON Patch (`application/json-patch+json`) a tag de governança `PII.Sensitive` na coluna `autor`. | RF28 / RF32 |
| **7. Linhagem de Dados** | `PUT` | `/api/v1/lineage` | Estabelece as arestas do grafo de linhagem conectando `silver.catalogo` $\rightarrow$ `gold.kpis_mensais_categoria` e `gold.desempenho_conteudos`. | RF29 |
| **8. Glossário Oficial** | `POST` | `/api/v1/glossaries` | Cadastra o vocabulário de negócio `Glossario_Educacional_FICDEV`. | RF28 |
| **9. Termos de Negócio** | `POST` | `/api/v1/glossaryTerms` | Registra os 4 termos oficiais: *Usuário Ativo*, *Taxa de Conclusão*, *Tempo Médio de Consumo* e *Conversão de Recomendação*. | RF28 |

---

## 4. Tutorial Passo a Passo de Execução e Verificação

### Passo 1: Executar o Script de Automação
Certifique-se de que o container do OpenMetadata está ativo e execute no terminal:
```bash
python scripts/configurar_openmetadata.py
```
**Saída Esperada no Terminal:**
```text
[1/6] Autenticando no OpenMetadata API (admin@openmetadata.org)...
      Autenticado com sucesso!
[2/6] Registrando Servico Postgres, Database e Schemas (silver, gold)...
      Serviço Postgres 'ficdev_postgres' OK.
      Database 'ficdev_recomendacao' OK.
      Schema 'silver' OK.
      Schema 'gold' OK.
[3/6] Catalogando Tabelas e Metadados das Camadas Silver e Gold...
      Tabela 'silver.catalogo' catalogada.
      Tabela 'gold.kpis_mensais_categoria' catalogada.
      Tabela 'gold.desempenho_conteudos' catalogada.
[4/6] Aplicando Classificacoes de Sensibilidade LGPD (PII.Sensitive)...
      Tag 'PII.Sensitive' aplicada na coluna 'autor' de 'desempenho_conteudos'.
[5/6] Registrando Grafo de Linhagem Grafica (Lineage)...
      Linhagem: silver.catalogo -> gold.kpis_mensais_categoria conectada.
      Linhagem: silver.catalogo -> gold.desempenho_conteudos conectada.
[6/6] Criando Glossario de Negocio e Termos Oficiais FIC_DEV...
      Glossário 'Glossario_Educacional_FICDEV' OK.
      Termo 'Usuario_Ativo' cadastrado.
      Termo 'Taxa_Conclusao' cadastrado.
      Termo 'Tempo_Medio_Consumo' cadastrado.
      Termo 'Conversao_Recomendacao' cadastrado.
======================================================================
[SUCESSO] Plataforma OpenMetadata 100% configurada e populada!
======================================================================
```

---

### Passo 2: Acessar a Interface Web
1. Abra o navegador em: [http://localhost:8585](http://localhost:8585)
2. Insira as credenciais de administrador:
   - **Email:** `admin@openmetadata.org`
   - **Password:** `admin`
3. Clique em **Login**.

---

### Passo 3: Onde Conferir Cada Requisito no Navegador (Guia Visual)

#### 1. Catálogo e Tabelas (RF27 — Evidência: `01_catalogo_tabelas.png`)
- No menu lateral esquerdo, clique no ícone de lupa: **Explore** $\rightarrow$ **Tables**.
- Você verá as tabelas cadastradas:
  - `ficdev_postgres.ficdev_recomendacao.gold.kpis_mensais_categoria`
  - `ficdev_postgres.ficdev_recomendacao.gold.desempenho_conteudos`
  - `ficdev_postgres.ficdev_recomendacao.silver.catalogo`
- Clique sobre qualquer uma delas para visualizar o dicionário de dados (colunas, tipos SQL, descrições e dono).

#### 2. Glossário de Negócio (RF28 — Evidência: `02_glossario_termos.png`)
- No menu lateral esquerdo, clique no ícone de livro/governança: **Govern** $\rightarrow$ **Glossary**.
- Clique em **`Glossario_Educacional_FICDEV`**.
- Verifique os 4 termos homologados:
  1. **Usuário Ativo:** Aluno com interação no período de apuração mensal.
  2. **Taxa de Conclusão:** Razão percentual entre conclusões e inícios de cursos.
  3. **Tempo Médio de Consumo:** Duração média em minutos despendida nos conteúdos.
  4. **Conversão de Recomendação:** Taxa de aceite dos materiais recomendados pelo motor de IA.

#### 3. Classificação de Privacidade LGPD (RF28 e RF32 — Evidência: `03_classificacao_pii.png`)
- No menu esquerdo, vá em **Explore** $\rightarrow$ **Tables** $\rightarrow$ abra **`desempenho_conteudos`**.
- Role até a linha da coluna **`autor`**.
- Observe a tag azul **`PII.Sensitive`** aplicada diretamente na coluna, indicando dado pessoal protegido pela política de minimização e anonimização da LGPD.

#### 4. Grafo de Linhagem Gráfica (RF29 — Evidência: `04_linhagem_grafica.png`)
- Abra a tabela **`kpis_mensais_categoria`** (ou `desempenho_conteudos`).
- Na barra de abas superior (ao lado de *Schema*, *Sample Data*, etc.), clique em **Lineage**.
- O OpenMetadata renderizará o diagrama visual interativo demonstrando a tabela `silver.catalogo` com uma seta conectando-se diretamente à tabela `gold.kpis_mensais_categoria`.

---

## 5. Relação de Evidências Oficiais (RF34)

As evidências fotográficas da governança devem ser salvas no diretório `openmetadata/evidencias/` com os seguintes nomes padronizados:

| Arquivo | Descrição da Captura de Tela | Requisito Comprovado |
| :--- | :--- | :---: |
| `01_catalogo_tabelas.png` | Tela de listagem em *Explore -> Tables* com os esquemas `silver` e `gold`. | RF27 |
| `02_glossario_termos.png` | Tela de *Govern -> Glossary* com os 4 termos de negócio cadastrados. | RF28 |
| `03_classificacao_pii.png` | Detalhe da coluna `autor` na tabela `desempenho_conteudos` com a tag `PII.Sensitive`. | RF28, RF32 |
| `04_linhagem_grafica.png` | Aba *Lineage* exibindo o fluxo visual `silver.catalogo` $\rightarrow$ Camada Gold. | RF29 |
