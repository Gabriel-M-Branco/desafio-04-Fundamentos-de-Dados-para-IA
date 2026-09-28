# Inventário de Dados Pessoais e Conformidade com a LGPD (RF32)

**Projeto:** Plataforma Educacional FIC_DEV — Módulo de Fundamentos de Dados para IA  
**Norma Regulamentadora:** Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 - LGPD)  
**Escopo:** Pipeline de Dados Ponta a Ponta (Fontes, Bronze, Silver, Parquet, Gold e Consumo Analítico)  
**Responsáveis:** Estudante 3 (Governança e Proteção de Dados), com suporte de Estudante 2 e Estudante 1  

---

## 1. Contexto e Diretrizes de Governança

A plataforma educacional FIC_DEV processa dados de navegação, engajamento e avaliações pedagógicas de seus estudantes. Em estrita observância aos princípios da **Finalidade**, **Adequação**, **Necessidade (Minimização)**, **Livre Acesso**, **Segurança** e **Transparência** (Art. 6º da LGPD), este documento estabelece o inventário formal de todos os dados pessoais que transitam pelo pipeline de engenharia de dados.

### Princípio da Minimização por Camadas (Data Lakehouse)
* **Fontes & Camada Bronze:** Ingestão de dados brutos com identificadores necessários para rastreabilidade operacional. Acesso restrito exclusivamente aos pipelines de engenharia de dados.
* **Camada Silver:** Aplicação de regras de higienização, mascaramento inicial e isolamento de anomalias em quarentena.
* **Camada Parquet & Gold:** Pseudonimização irreversível sem chave de salt (`HASH_SALT`), agregações por categoria e período (`ano_mes`), e supressão total de dados biográficos diretos.
* **Camada de Consumo (SQL Lab / Superset):** Exposição estrita de métricas agregadas e dados mascarados. Nenhum dado pessoal identificável direto é consultável por analistas de negócio.

---

## 2. Inventário Exaustivo de Dados Pessoais e Metadados Identificáveis

| Campo / Atributo | Tabela / Coleção de Origem | Esquema de Destino | Classificação (LGPD Art. 5º) | Base Legal (LGPD Art. 7º) | Finalidade do Tratamento | Período de Retenção | Medidas Técnicas de Segurança |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`autor`** | CSV: `dados/catalogo.csv`<br>PostgreSQL: `bronze.catalogo_raw` | `bronze.catalogo_raw`<br>`silver.catalogo` | **Dado Pessoal Direto** (Art. 5º, I)<br>Identifica a autoria do conteúdo/curso | **Art. 7º, V** (Execução de contrato / termos de uso)<br>**Art. 7º, IX** (Legítimo interesse) | Atribuição de autoria e instrutoria aos materiais educacionais da plataforma. | Vigência do cadastro ativo + 5 anos após inatividade (Art. 27 CDC). | **Mascaramento parcial** (`J*** D**`) para visualizações e queries analíticas; bloqueio total na camada Gold. |
| **`usuario_id`** | JSON: `dados/interacoes.json`<br>PostgreSQL: `bronze.interacoes_raw` | `silver.interacoes`<br>`dados/parquet/interacoes/` | **Identificador Indireto** (Art. 5º, I c/c Art. 13)<br>Permite reidentificação com tabela de cadastro | **Art. 7º, V** (Execução de contrato de ensino)<br>**Art. 7º, IX** (Legítimo interesse pedagógico) | Rastreamento do progresso curricular, cálculo de taxas de conclusão e personalização de recomendações. | Vigência do vínculo acadêmico + 5 anos para fins de auditoria pedagógica. | **Pseudonimização determinística** via UUIDv5 e Hashing SHA-256 com **Salt secreto** (`HASH_SALT`); ausência na Gold pública. |
| **`data_hora`** | JSON: `dados/interacoes.json`<br>PostgreSQL: `bronze.interacoes_raw` | `silver.interacoes`<br>`dados/parquet/interacoes/` | **Metadado de Conexão / Dado Pessoal Indireto** (Marco Civil Art. 15) | **Art. 7º, II** (Obrigação legal - Marco Civil da Internet)<br>**Art. 7º, V** (Contrato) | Trilha de auditoria técnica e cumprimento da guarda de registros de acesso a aplicações. | Mínimo legal de 6 meses (Marco Civil) a 1 ano no ambiente produtivo. | **Generalização temporal:** agregado na Gold apenas como `ano` e `mes` (`ano_mes`), eliminando resolução ao segundo. |
| **`comentario`** | MongoDB: `comentarios`<br>PostgreSQL: `bronze.comentarios_raw` | `bronze.comentarios_raw`<br>`silver.comentarios` | **Dado Pessoal Não Estruturado**<br>(Potencialmente sensível caso haja relato pessoal livre) | **Art. 7º, IX** (Legítimo interesse institucional)<br>**Art. 7º, I** (Consentimento nos termos) | Avaliação qualitativa de didática, detecção de pontos de melhoria e análise de sentimento pedagógico. | 2 anos a partir da postagem ou até revogação/exclusão pelo titular. | **Minimização radical:** o texto bruto é mantido na Silver e **nunca é transferido para a Gold**; apenas médias numéricas (`avaliacao_media`) sobem. |
| **`avaliacao`** | MongoDB: `comentarios.avaliacao`<br>PostgreSQL: `bronze.comentarios_raw` | `silver.comentarios`<br>`gold.desempenho_conteudos` | **Dado Comportamental** (Não pessoal quando desvinculado do autor) | **Art. 7º, IX** (Legítimo interesse) | Geração de indicadores de satisfação acadêmica (NPS educacional). | Indeterminado após agregação estatística irreversível. | Agregação por média aritmética ponderada (`AVG(avaliacao)` / `avaliacao_media`). |

---

## 3. Justificativa Jurídica Detalhada das Bases Legais (Art. 7º da LGPD)

### 3.1. Execução de Contrato e Procedimentos Preliminares (Art. 7º, V)
A coleta do `usuario_id` e a medição do consumo de aulas e materiais é intrínseca à prestação do serviço educacional contratado. Sem o registro de início e conclusão de atividades, é impossível emitir certificados de conclusão ou aferir o cumprimento da carga horária acadêmica.

### 3.2. Cumprimento de Obrigação Legal ou Regulatória (Art. 7º, II)
A guarda de logs de conexão e timestamps exatos (`data_hora`) pelo prazo de 6 meses decorre de imposição do **Artigo 15 da Lei Federal nº 12.965/2014 (Marco Civil da Internet)**, constituindo base legal autônoma e mandatória que independe de consentimento.

### 3.3. Legítimo Interesse do Controlador (Art. 7º, IX)
A realização de análises agregadas de engajamento, evasão e geração de recomendações de cursos é fundamental para o aprimoramento contínuo dos serviços pedagógicos oferecidos pela instituição. Realizou-se o Teste de Ponderação do Legítimo Interesse (LIA - *Legitimate Interests Assessment*), assegurando que:
1. **Finalidade Legítima:** Aperfeiçoar o ensino e apoiar estudantes em risco de evasão.
2. **Necessidade:** O pipeline aplica técnicas de pseudonimização e generalização temporal, tratando o mínimo de dados viável.
3. **Equilíbrio:** Nenhum dado íntimo é comercializado ou compartilhado com terceiros não autorizados.

---

## 4. Ciclo de Vida dos Dados e Política de Retenção e Descarte

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ 1. Coleta Ativa  │ ───> │ 2. Uso Analítico │ ───> │ 3. Arquivamento  │ ───> │ 4. Descarte /    │
│ (Fontes/Bronze)  │      │ (Silver/Gold)    │      │ (Backups Frios)  │      │    Anonimização  │
│ Durante o vínculo│      │ Durante o vínculo│      │ 5 anos legais    │      │    Irreversível  │
└──────────────────┘      └──────────────────┘      └──────────────────┘      └──────────────────┘
```

1. **Período Ativo:** Os dados brutos residem na camada Bronze durante o ano letivo corrente.
2. **Período de Arquivamento:** Dados da camada Silver e logs de auditoria são mantidos pelo prazo prescricional de 5 anos (reivindicações contratuais e educacionais).
3. **Descarte e Anonimização:** Ao término do prazo de retenção ou mediante solicitação do titular (Art. 18, VI da LGPD), os registros da camada Silver são anonimizados permanentemente (apagando `autor` e recalculando `usuario_id` para identificador fictício nulo), enquanto os agregados na Gold permanecem estritamente estatísticos e sem vinculação a pessoas naturais.

---

## 5. Medidas Técnicas e Organizacionais de Segurança da Informação

Conforme preconiza o Art. 46 da LGPD, o pipeline adota salvaguardas robustas:

1. **Segregação por Esquemas no Banco de Dados (PostgreSQL):**
   * Esquema `bronze`: permissão de escrita e leitura restrita ao usuário do pipeline de ingestão (`hop_user`).
   * Esquema `silver`: permissão de acesso ao pipeline distribuído (`beam_runner`).
   * Esquema `gold`: permissão de leitura concedida ao Apache Superset (`superset_reader`), sem privilégios de acesso aos esquemas `bronze` ou `silver`.
2. **Criptografia e Segredos Fora do Código:**
   * Todas as credenciais e salts criptográficos (`HASH_SALT`) são injetados exclusivamente via variáveis de ambiente no arquivo `.env` (ignorado pelo versionador Git).
3. **Quarentena e Auditoria de Falhas:**
   * Qualquer registro que viole o esquema ou contenha dados em formato incompatível é isolado em `quarentena.registros_invalidos`, prevenindo que inconsistências passem despercebidas para a camada analítica.
