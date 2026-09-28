# Evidências de Execução dos Dashboards (Apache Superset)

Esta pasta consolida as capturas de tela e evidências visuais dos dashboards homologados no **Apache Superset** para ambos os módulos da formação, segregados por desafio:

---

## 1. Desafio 3 (Etapa Anterior / Schema `public`)
Diretório: [`dashboard/evidencias/desafio_3/`](desafio_3/)

Evidências do painel analítico legado consumindo tabelas relacionais (`usuarios`, `conteudos`, `interacoes`, `recomendacoes`):
- `dashboard_visao_geral.png`: Visão geral dos cartões de métricas e gráficos de visualizações e conclusões por categoria.
- `dashboard_filtros_interativos.png`: Filtros interativos aplicados no painel.
- `dashboard_filtros_categoriasduplas.png`: Filtro com múltiplas categorias didáticas selecionadas em paralelo.
- `superset_conexao_database.png`: Configuração da conexão com o banco de dados PostgreSQL (`ficdev_postgresql`).

---

## 2. Desafio 4 (Etapa Atual / Schemas `gold` e `silver` — RF16 a RF18)
Diretório: [`dashboard/evidencias/desafio_4/`](desafio_4/)

Evidências do painel executivo corporativo do Desafio 4:
- `Desafio 4 - Dashboard.png`: Painel executivo oficial demonstrando a narrativa sequencial de Storytelling pedagógico (Atratividade $\rightarrow$ Retenção/Evasão em Cursos $\rightarrow$ Matriz de Desempenho), interatividade global com filtros cruzados (*cross-filtering*) e gráficos analíticos modelados a partir de datasets virtuais do SQL Lab.
- `Desafio 4 - Alert.png`: Painel de monitoramento ativo (*Alerts & Reports*) com alerta configurado (`Alerta Crítico: Baixo Tempo Total de Consumo por Categoria`), executando query SQL observer periódica na camada Gold com disparo condicional por e-mail.
