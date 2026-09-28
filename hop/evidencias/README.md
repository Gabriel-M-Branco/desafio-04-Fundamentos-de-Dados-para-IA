# Evidências de Execução do Apache Hop (RF20 a RF23, RF26)

Este diretório armazena as capturas de tela oficiais da interface web do **Apache Hop Web** ([http://localhost:8080](http://localhost:8080)), comprovando a orquestração integrada ponta a ponta, tratamento de erros, logs e refino das camadas Bronze, Silver e Gold:

---

## Relação das Evidências Homologadas

| Arquivo de Evidência | Tela / Fluxo | Requisitos Atendidos | Detalhamento Visível na Imagem |
| :--- | :--- | :---: | :--- |
| `01_workflow_principal_execucao_sucesso_logs.png` | `workflow_principal.hwf` | RF22, RF23, RF26 | Execução mestre completa com checkmarks verdes em todas as etapas (`START` $\rightarrow$ `1. Ingestao Bronze e Silver` $\rightarrow$ `2. Criar Estruturas da Camada Gold` $\rightarrow$ `3. Iniciar Etapa Gold` $\rightarrow$ `4. Consolidar Camada Gold no Banco` $\rightarrow$ `5. Finalizar Etapa Gold` $\rightarrow$ `SUCESSO_INTEGRADO`). Painel lateral de **Logging** demonstrando a duração total da execução (`1.451 segundos`) e ausência de erros. |
| `02_workflow_carga_bronze_silver_sucesso.png` | `carga_bronze_silver.hwf` | RF20, RF21, RF22 | Execução integrada das camadas Bronze e Silver com status de sucesso em todos os nós: pré-validação (`Preflight Desafio 1`), ingestão Bronze com auditoria (`catalogo`, `interacoes`, `comentarios`), refino Silver com tipagem e desduplicação, e quarentena de inconsistências. |
| `03_workflow_principal_regras_orquestracao_rf22.png` | Nota técnica e cabeçalho do `workflow_principal.hwf` | RF22 | Detalhamento das 5 regras corporativas de orquestração: carga das camadas com metadados, aplicação de DDL analítico Gold, consolidação no PostgreSQL, rastreabilidade por lote em `controle.execucao_workflow` e compensação/interrupção automática em caso de falha crítica. |
