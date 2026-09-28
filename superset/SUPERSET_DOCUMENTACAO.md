# Visualização Executiva e Monitoramento Nativo no Apache Superset (RF16 — RF18)

Este documento detalha a construção das visualizações, do storytelling executivo e das funcionalidades de monitoramento ativo implementadas no **Apache Superset** a partir da camada Gold no PostgreSQL.

---

## Requisito 16 — Storytelling Executivo com Dados

### 1. Pergunta Decisória Central
> *"A alta demanda pelos formatos mais consumidos da plataforma traduz-se em retenção e conclusão efetiva, ou estamos gerando volume de acessos sem engajamento real?"*

### 2. Estrutura Narrativa Sequencial

A narrativa foi dividida em uma sequência lógica de 3 gráficos encadeados:

#### **Passo 1: Contexto — Atratividade do Catálogo**
* **Visualização:** `STORYTELLING - Distribuição de acesso por tipo de conteúdo` (Gráfico de Pizza).
* **Título Informativo:** *Distribuição de Acesso por Tipo de Conteúdo*.
* **Fato Observado:** Os formatos de **Artigo** e **Podcast** concentram as maiores parcelas de interesse inicial do público, seguidos por **Cursos** e **Vídeo**.
* **Hipótese:** Os alunos buscam primeiramente conteúdos visuais e curtos para iniciar o contato com novos temas pedagógicos.

#### **Passo 2: Evidência — Funil de Retenção e Evasão**
* **Visualização:** `SQLab/STORYTELLING - Retenção do Tipo` (Gráfico de Barras Agrupadas).
* **Título Informativo:** *Retenção por Tipo: Desigualdade no Funil de Conclusão*.
* **Fato Observado:** Apesar de atrair menos pessoas, o formato **Curso** ainda sim apresenta a maior taxa de evasão, perdendo quase 40% dos alunos antes da conclusão. Em contrapartida, **Podcasts**, **Vídeos**, **Artigo** mantêm uma proporção de conclusão muito mais alta em relação aos inícios.
* **Hipótese:** Cursos extensos sofrem com fadiga de conteúdo ou falta de ritmificação didática.

#### **Passo 3: Descoberta e Ação Recomendada — Matriz de Desempenho**
* **Visualização:** `STORYTELLING - Desempenho de cada Tipo` (Bubble Chart).
* **Título Informativo:** *Desempenho por Formato e Nível: Qualidade e Retenção*.
* **Fato Observado:** Os conteúdos do tipo **Curso** apresentam baixo volume de engajamento acumulado em relação aos demais formatos.
* **Hipótese:** Materiais no formato **Podcast** e **Artigo** oferecem consumo ágil e de fácil fixação, resultando em altas notas de satisfação dos alunos, enquanto os **Cursos** enfrentam baixíssima adesão e baixa taxa de conclusão ao longo dos níveis.

* **Recomendação Executiva:** 
  1. Fracionar cursos de longa duração em módulos menores (*microlearning*).
  2. Utilizar os Podcasts e Artigos como alavanca de engajamento e como apoio didático intermediário.

---

## Requisito 17 — Visualizações Específicas do SQL Lab

Para garantir análises complementares ao Storytelling, foram desenvolvidas visualizações nativas baseadas em consultas virtuais executadas no SQL Lab:

1. **SQLab - Análise de Eficiência e Evasão por Categoria (Barras Empilhadas):**
   * **Eixo X:** `categoria`
   * **Eixo Y:** `total_inicios` e `total_conclusoes`
   * **Objetivo:** Mapear a perda de engajamento ao longo do funil didático por domínio de negócio.

2. **SQLab - Visualizações por Categoria (Série Temporal / Linhas):**
   * **Eixo X:** `data_referencia` (Mês)
   * **Eixo Y:** `total_visualizacoes`
   * **Séries:** `categoria`
   * **Objetivo:** Acompanhar a sazonalidade e a tendência histórica de consumo por área de conhecimento.

---

## Requisito 18 — Filtros Cruzados e Alertas no Superset

### 1. Interatividade por Filtro Cruzado (*Cross-Filtering*)
* **Configuração:** Recurso habilitado nas propriedades globais do Dashboard (`Enable cross-filtering`).
* **Comportamento:** O filtro cruzado funciona de maneira integrada entre os gráficos do Storytelling e os gráficos exclusivos do SQL Lab. Ao clicar em um elemento visual (ex.: na fatia *"Curso"* no gráfico de pizza do Storytelling), todos os paineis de storytelling recalculam automaticamente suas métricas para o recorte selecionado. Há também filtro cruzado dos gráficos exclusivos do SQLab.

### 2. Filtros Globais do Dashboard
Disponibilizados no painel lateral esquerdo (*Filter Bar*):
* **Filtro 1 (Dimensão de Negócio):** `Filtro 1 - Dimensão de Negócio` (Múltipla seleção por `categoria`).
* **Filtro 2 (Período):** `Filtro 2 - Período` (Filtro nativo de intervalo temporal associado à coluna de referência/data).

### 3. Configuração de Alerta de Negócio (*Alerts & Reports*)

* **Nome do Alerta:** `Alerta Crítico: Baixo Tempo Total de Consumo por Categoria`
* **Frequência:** `Inicio de cada mês, às 8h da manhã`
* **Forma de Contato:** `Envio de email para email_ficticio_desafio_4@cursos.ficdev.edu.br`
* **Banco de Dados:** PostgreSQL (Camada Gold)
* **SQL Observer (Condição Limitante, Se NOT NULL):**
  ```sql
  -- Avalia a condição considerando apenas o mês/ano mais recente na camada Gold
  SELECT 
      ano,
      mes,
      categoria,
      ROUND(AVG(tempo_total_consumido_min), 2) AS media_tempo_consumido_min
  FROM gold.kpis_mensais_categoria 
  WHERE (ano, mes) = (
      SELECT ano, mes 
      FROM gold.kpis_mensais_categoria 
      ORDER BY ano DESC, mes DESC 
      LIMIT 1
  )
  HAVING AVG(tempo_total_consumido_min) < 500;
  ```

---

## Localização dos Pacotes e Evidências

Todos os pacotes de exportação e capturas de tela foram consolidados e padronizados no diretório [`dashboard/`](../dashboard/):
- **Pacotes ZIP de Exportação:**
  - [`dashboard/dashboard_desafio_4.zip`](../dashboard/dashboard_desafio_4.zip): Pacote oficial de importação do Desafio 4 (Storytelling, SQL Lab e Alertas).
  - [`dashboard/dashboard_desafio_3.zip`](../dashboard/dashboard_desafio_3.zip): Pacote legado do Desafio 3 (Schema `public`).
- **Evidências Visuais (Screenshots):**
  - [`dashboard/evidencias/desafio_4/`](../dashboard/evidencias/desafio_4/): Capturas de tela do Dashboard Desafio 4 e Alerta Crítico.
  - [`dashboard/evidencias/desafio_3/`](../dashboard/evidencias/desafio_3/): Capturas de tela do painel e filtros do Desafio 3.