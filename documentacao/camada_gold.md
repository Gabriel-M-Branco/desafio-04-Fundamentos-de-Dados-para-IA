# Especificação da Camada Gold para Consumo Analítico (RF26)

Este documento descreve a modelagem dimensional, granularidade, chaves, medidas, fórmulas e visões analíticas da **Camada Gold** no PostgreSQL, atendendo integralmente ao requisito **RF26** e servindo de interface oficial para o **Estudante 3** (SQL Lab, Datasets e Apache Superset).

---

## 1. Princípios Arquiteturais da Camada Gold

1. **Desacoplamento Estrito da Camada Bronze/Silver:** O consumo analítico e os dashboards executivos não consultam tabelas brutas ou transacionais diretamente. Toda a métrica consumida no Superset é pré-agregada e auditada pela camada Gold.
2. **Centralização da Lógica de Cálculo no Apache Beam:** Para eliminar discrepâncias de fórmulas entre relatórios, as agregações temporais e de engajamento são computadas exclusivamente pelo pipeline Apache Beam e persistidas na Gold, dispensando queries analíticas excessivamente complexas no Superset.
3. **Barreira de Qualidade (Data Quality Gate):** A publicação na Gold só é concluída se o lote for 100% aprovado nos testes críticos de qualidade de dados (RF31).

---

## 2. Modelagem das Tabelas da Camada Gold

### 2.1 Tabela `gold.kpis_mensais_categoria`
- **Finalidade:** Alimentar gráficos de tendência temporal (séries temporais de visualizações, inícios, conclusões e taxa de término por categoria).
- **Granularidade:** Uma linha por `(ano, mes, categoria)`.
- **Chave Primária Composta:** `(ano, mes, categoria)`.

| Campo | Tipo SQL | Classificação | Descrição e Fórmula |
| :--- | :--- | :--- | :--- |
| `ano` | `INTEGER` | Dimensão / PK | Ano do evento extraído de `data_hora`. |
| `mes` | `INTEGER` | Dimensão / PK | Mês do evento (1 a 12). |
| `categoria` | `VARCHAR(120)` | Dimensão / PK | Categoria educacional padronizada (ex: "Ciência de Dados"). |
| `total_interacoes` | `INTEGER` | Métrica Aditiva | Contagem total de interações registradas no período/categoria. |
| `usuarios_ativos` | `INTEGER` | Métrica Não-Aditiva | $\text{COUNT(DISTINCT usuario\_id)}$. |
| `total_visualizacoes` | `INTEGER` | Métrica Aditiva | $\sum [\text{tipo\_interacao} = \text{'visualização'}]$. |
| `total_inicios` | `INTEGER` | Métrica Aditiva | $\sum [\text{tipo\_interacao} = \text{'início'}]$. |
| `total_conclusoes` | `INTEGER` | Métrica Aditiva | $\sum [\text{tipo\_interacao} = \text{'conclusão'}]$. |
| `total_curtidas` | `INTEGER` | Métrica Aditiva | $\sum [\text{tipo\_interacao} = \text{'curtida'}]$. |
| `taxa_conclusao_pct` | `NUMERIC(5,2)` | Métrica Derivada | $\left( \frac{\text{total\_conclusoes}}{\text{NULLIF(total\_inicios, 0)}} \right) \times 100$ |
| `tempo_total_consumido_min` | `NUMERIC(12,2)` | Métrica Aditiva | Soma do tempo consumido em minutos. |
| `tempo_medio_min` | `NUMERIC(10,2)` | Métrica Derivada | $\frac{\text{tempo\_total\_consumido\_min}}{\text{total\_interacoes}}$ |
| `avaliacao_media` | `NUMERIC(3,2)` | Métrica Derivada | Média aritmética das notas atribuídas no período $[1.0, 5.0]$. |
| `_data_carga_gold` | `TIMESTAMP` | Auditoria | Carimbo de data/hora UTC da publicação na Gold. |
| `_lote_processamento` | `VARCHAR(100)` | Auditoria | Identificador unívoco do lote gerado pelo Beam. |

---

### 2.2 Tabela `gold.desempenho_conteudos`
- **Finalidade:** Mapear o ranking de conteúdos mais populares, taxas de conclusão individuais e orientar revisões curriculares.
- **Granularidade:** Uma linha por `conteudo_id`.
- **Chave Primária:** `conteudo_id`.

| Campo | Tipo SQL | Classificação | Descrição |
| :--- | :--- | :--- | :--- |
| `conteudo_id` | `BIGINT` | Dimensão / PK | Identificador único do conteúdo. |
| `titulo` | `VARCHAR(255)` | Atributo | Título do material educacional. |
| `tipo` | `VARCHAR(30)` | Atributo | Curso, Vídeo, Artigo ou Podcast. |
| `categoria` | `VARCHAR(120)` | Atributo | Categoria temática. |
| `nivel` | `VARCHAR(30)` | Atributo | Básico, Intermediário ou Avançado. |
| `total_visualizacoes` | `INTEGER` | Métrica | Total acumulado de visualizações do conteúdo. |
| `total_inicios` | `INTEGER` | Métrica | Quantidade de estudantes que iniciaram o material. |
| `total_conclusoes` | `INTEGER` | Métrica | Quantidade de estudantes que concluíram o material. |
| `taxa_conclusao_pct` | `NUMERIC(5,2)` | Métrica | Taxa de conclusão percentual do conteúdo. |
| `tempo_total_min` | `NUMERIC(12,2)` | Métrica | Volume total de minutos consumidos pelos alunos. |
| `avaliacao_media` | `NUMERIC(3,2)` | Métrica | Nota média de satisfação atribuída pelos estudantes. |
| `_data_carga_gold` | `TIMESTAMP` | Auditoria | Carimbo UTC da carga. |
| `_lote_processamento` | `VARCHAR(100)` | Auditoria | Identificador do lote de auditoria. |

---

## 3. Visões Analíticas Criadas para o Apache Superset e SQL Lab

1. **`gold.vw_kpis_executivos` (e espelho `public.vw_gold_kpis_mensais_categoria`):**
   - Transforma `(ano, mes)` em uma data no formato padrão `MAKE_DATE(ano, mes, 1)` para que o componente de série temporal (*Time Series Chart*) do Apache Superset possa plotar tendências sem necessidade de parsing de string no front-end.
2. **`gold.vw_ranking_conteudos_engajamento` (e espelho `public.vw_gold_ranking_conteudos`):**
   - Aplica window functions `DENSE_RANK() OVER (PARTITION BY categoria ORDER BY total_visualizacoes DESC)` para alimentar cartões de top conteúdos no dashboard.

---

## 4. Como o Estudante 3 Consome a Camada Gold

1. **No SQL Lab:**
   - Executar consultas como:
     ```sql
     SELECT * FROM gold.vw_kpis_executivos ORDER BY data_referencia DESC;
     ```
2. **Criando Datasets no Superset:**
   - Conectar no banco `PostgreSQL` e selecionar o schema `gold` (ou `public`) e as visões `vw_kpis_executivos` e `vw_ranking_conteudos_engajamento`.
