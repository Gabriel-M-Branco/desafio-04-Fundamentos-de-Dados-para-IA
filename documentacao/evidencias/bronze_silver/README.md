# Evidências visuais — Estudante 1

Coloque nesta pasta os prints reais feitos no ambiente local.

## Arquivos esperados

1. `01_bronze_pipeline_aberto.png` — Apache Hop com `bronze_pipeline.hpl` aberto.
2. `02_bronze_execucao_sucesso.png` — execução Bronze concluída com sucesso.
3. `03_silver_pipeline_aberto.png` — Apache Hop com `silver_pipeline.hpl` aberto.
4. `04_silver_execucao_sucesso.png` — execução Silver concluída com sucesso.
5. `05_workflow_principal.png` — workflow mostrando START → Bronze → Silver → SUCESSO.
6. `06_workflow_execucao_sucesso.png` — execução do workflow completo.
7. `07_falha_arquivo.png` — falha causada por fonte obrigatória ausente.
8. `08_quarentena_regra.png` — registro inválido enviado para quarentena.
9. `09_falha_conexao_postgres.png` — falha de conexão PostgreSQL.
10. `10_reprocessamento.png` — reprocessamento de registro corrigido.
11. `10_reprocessamento_vscode.png` — evidência complementar do reprocessamento mostrando `aprovados: 1` e `rejeitados: 0`.

## Evidências já concluídas

- Prints `01` a `10` capturados e versionados, incluindo uma evidência complementar do reprocessamento no VS Code.
- Workflow `START → Bronze → Silver → SUCESSO` executado com sucesso.
- Pipeline Bronze → Silver executado com sucesso.
- 1000 registros de catálogo, 1000 interações e 1000 comentários processados.
- Quarentena vazia na execução válida.
- `pytest`: 3 testes aprovados.
- Logs gerados em `logs/pipeline_estudante1.jsonl`.

Os prints devem ser reais; não devem ser simulados ou gerados artificialmente.
