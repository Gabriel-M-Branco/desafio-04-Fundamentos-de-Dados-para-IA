# Apache Hop — Ingestão das Camadas Bronze e Silver (RF20 a RF23)

Implementação da etapa de ingestão de dados: Apache Hop, Bronze, Silver, workflow e tratamento de erros.

## Pré-requisito de continuidade

O Desafio 2 reaproveita o Desafio 1. A tabela `public.usuarios` deve estar preenchida com os usuários válidos da solução anterior. O workflow faz um preflight e falha explicitamente se ela estiver vazia.

## Preparação

1. Copie `.env.example` para `.env` e preencha as credenciais locais.
2. Defina o Hop: `export HOP_HOME=$HOME/hop` (ajuste o caminho).
3. Rode `bash hop/configurar-projeto.sh`.
4. Rode `bash hop/run-pipeline.sh`.

O script gera um `RUN_ID` único e grava o log em `logs/hop_<RUN_ID>.log`.

## Artefatos

- `pipelines/bronze_*.hpl`: CSV/JSON -> schema `bronze`, sem transformação destrutiva.
- `pipelines/silver_*.hpl`: aprovados -> `silver`; rejeitados -> `quarentena.registros`.
- `workflows/carga_bronze_silver.hwf`: Bronze -> Silver, estados da execução e rotas de falha.
- `workflows/workflow_principal.hwf`: Orquestrador mestre parametrizado.
- `metadata/rdbms/PostgreSQL.json`: conexão reutilizável com credenciais por variáveis.
- `../sql/camadas_bronze_silver.sql`: tabelas, regras, validação e reprocessamento.

## Integração da equipe

Este workflow termina na Silver. No encadeamento da esteira completa, sua saída de sucesso segue para:

`Qualidade (RF31) -> Parquet (RF24) -> Apache Beam (RF25) -> Camada Gold (RF26) -> Superset / Governança`

## RF23

- arquivo inexistente: `bash hop/testes/falha_arquivo.sh`
- conexão indisponível: `bash hop/testes/falha_conexao.sh`
- regra inválida (automático): `bash hop/testes/falha_regra.sh`
- regra inválida (SQL manual): `hop/testes/falha_regra.sql`
- reprocessamento: `sql/reprocessar_quarentena_exemplo.sql`
