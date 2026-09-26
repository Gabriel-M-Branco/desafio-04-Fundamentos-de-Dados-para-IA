# Evidências — Ingestão Bronze e Silver

Responsabilidade: **Apache Hop, Bronze, Silver, workflows e tratamento de erros**.

## Entregas implementadas

- `hop/pipelines/bronze_catalogo.hpl`, `bronze_interacoes.hpl`, `bronze_comentarios.hpl`
- `hop/pipelines/silver_catalogo.hpl`, `silver_interacoes.hpl`, `silver_comentarios.hpl`
- `hop/workflows/carga_bronze_silver.hwf`
- `hop/workflows/workflow_principal.hwf`
- `hop/environments/local.properties`
- `scripts/ingestao_bronze_silver.py`
- `tests/test_ingestao_bronze_silver.py`

## Evidências que devem ser capturadas no ambiente real

1. Hop GUI com os pipelines de Bronze abertos.
2. Execução Bronze concluída com sucesso.
3. Conteúdo de `dados/bronze/` mostrando CSV/JSON preservados.
4. Hop GUI com os pipelines de Silver.
5. Execução Silver concluída.
6. Conteúdo de `dados/silver/`.
7. Arquivo de `dados/quarentena/quarentena_<run_id>.json`.
8. Workflow `workflow_principal.hwf` com Bronze → Silver.
9. Falha de arquivo:
   - renomear temporariamente uma fonte;
   - executar Bronze;
   - capturar erro.
10. Falha de regra:
   - usar cópia de teste com `percentual_conclusao=150`;
   - executar Silver;
   - mostrar registro na quarentena.
11. Falha de conexão:
   - usar porta PostgreSQL incorreta;
   - executar Bronze sem `--skip-db`;
   - capturar falha e interrupção.
12. Reprocessamento:
   - corrigir um JSON de quarentena;
   - executar:
     ```bash
     python scripts/ingestao_bronze_silver.py --reprocess-quarantine caminho/arquivo_corrigido.json
     ```
   - mostrar o registro reaproveitado na Silver.
13. Log `logs/pipeline_ingestao.jsonl` com run_id, etapa, status e timestamps.

## Comandos de validação

Sem PostgreSQL:

```bash
python scripts/ingestao_bronze_silver.py \
  --stage all \
  --source-dir dados/brutos \
  --skip-db
```

Com PostgreSQL:

```bash
python scripts/ingestao_bronze_silver.py \
  --stage all \
  --source-dir dados/brutos
```

Testes:

```bash
python -m pytest tests/test_ingestao_bronze_silver.py -v
```
## Critério de conclusão

A parte do Estudante 1 só deve ser marcada como demonstrada quando as execuções e capturas acima forem produzidas no ambiente da equipe.


## Execução local confirmada

Execução realizada com **Python 3.12.11** no ambiente virtual da equipe.

Comando:

```bash
python scripts/estudante1_pipeline.py \
  --stage all \
  --source-dir ../desafio-03-pipeline-recomendacao/dados/brutos \
  --skip-db
```

Resultado registrado:

```text
run_id: 550954f8-2459-4495-a605-49541b0acf96
Bronze:
- catalogo: 1000
- interacoes: 1000
- comentarios: 1000

Silver:
- catalogo_aprovados: 1000
- interacoes_aprovadas: 1000
- comentarios_aprovados: 1000
- quarentena: 0

status_final: SUCESSO
```

Arquivos gerados e verificados localmente:

```text
dados/bronze/catalogo.csv
dados/bronze/catalogo.parquet
dados/bronze/comentarios.json
dados/bronze/comentarios.parquet
dados/bronze/interacoes.json
dados/bronze/interacoes.parquet

dados/silver/catalogo.parquet
dados/silver/comentarios.parquet
dados/silver/interacoes.parquet

dados/quarentena/quarentena_550954f8-2459-4495-a605-49541b0acf96.json
dados/resumo_estudante1.json
logs/pipeline_estudante1.jsonl
```

O log também registrou uma execução anterior com falha de fonte ausente, útil como evidência do tratamento de erro de arquivo.

### Testes automatizados

Executado:

```bash
python -m pytest tests/test_estudante1_pipeline.py -v
```

Resultado:

```text
3 passed
```

Testes aprovados:

- `test_bronze_silver_e_quarentena`
- `test_falha_arquivo_ausente`
- `test_reprocessamento_quarentena_corrigida`

### Evidências visuais concluídas

Já foram capturadas e versionadas no GitHub:

- `01_bronze_pipeline_aberto.png`;
- `02_bronze_execucao_sucesso.png`;
- `03_silver_pipeline_aberto.png`;
- `04_silver_execucao_sucesso.png`;
- `05_workflow_principal.png`;
- `06_workflow_execucao_sucesso.png`;
- `07_falha_arquivo.png`;
- `08_quarentena_regra.png`;
- `09_falha_conexao_postgres.png`;
- `10_reprocessamento.png`;
- `10_reprocessamento_vscode.png`.

O workflow foi validado no Apache Hop com o fluxo **START → Bronze → Silver → SUCESSO**.

### Caminhos usados na validação local

Na validação realizada neste computador, os pipelines e o workflow usam caminhos absolutos de `/home/diego/Documentos/...`. Essa configuração foi mantida porque o transform `DataGrid` usado para montar os argumentos do `ExecProcess` não expandiu as variáveis internas do Apache Hop durante a execução. Para executar em outro computador, os caminhos devem ser ajustados no ambiente/projeto Hop antes da execução.

### Situação das evidências

As evidências previstas para a responsabilidade do Estudante 1 foram capturadas e versionadas. Foram demonstrados os três cenários de falha exigidos para esta parte (arquivo, regra e conexão), além do reprocessamento controlado de um registro corrigido.
