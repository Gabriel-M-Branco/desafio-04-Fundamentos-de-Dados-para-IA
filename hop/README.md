# Apache Hop — Ingestão das Camadas Bronze e Silver (RF20 a RF23)

Implementação da etapa de ingestão de dados: Apache Hop, Bronze, Silver, workflow e tratamento de erros.

## Pré-requisito de Integridade

A tabela `public.usuarios` deve estar preenchida com os usuários válidos (gerados na etapa base `python -m src.main`). O workflow realiza uma validação de preflight no banco e interrompe a execução caso ela esteja vazia.

## Como Executar

### 1. Pela Interface Gráfica Web (Hop Web — Play no Navegador)

1. Certifique-se de que os contêineres Docker estão em execução:
   ```bash
   docker compose up -d
   ```
2. Abra no navegador: [http://localhost:8080](http://localhost:8080).
3. Na árvore de arquivos à esquerda (pasta `default`), dê dois cliques na pasta **`workflows`** e abra **`workflow_principal.hwf`** (ou `workflows/carga_bronze_silver.hwf`).
4. Clique no botão de **Play (▶ Executar)** na barra de ferramentas superior do editor.
5. Na tela de confirmação de execução:
   - Run configuration: **`local`**
   - Log level: **`Basic`**
6. Clique em **Launch**. O workflow executará todas as etapas (criação de tabelas, preflight, ingestão Bronze, classificação Silver e controle), finalizando com sucesso.

### 2. Pela Linha de Comando no Docker (CLI Headless)

Você também pode disparar a execução diretamente no contêiner com o HopRun:
```bash
docker exec hop-web /usr/local/tomcat/webapps/ROOT/hop-run.sh \
  --environment desafio4-dev \
  --project desafio4 \
  --file /files/workflows/workflow_principal.hwf \
  --runconfig local \
  --level BASIC
```

### 3. Pela Instalação Local do Hop (Desktop)

Se preferir rodar com o Apache Hop instalado na máquina:
1. Copie `.env.example` para `.env` e preencha as credenciais.
2. Defina o caminho: `export HOP_HOME=$HOME/hop` (ou variável de ambiente no Windows).
3. Execute:
   ```bash
   bash hop/run-pipeline.sh
   ```

## Portabilidade e Caminhos Relativos (Multiplataforma)

O projeto foi projetado para rodar em qualquer sistema operacional (Windows, Linux, macOS) e contêineres sem falhas de caminho:
- Todos os caminhos entre workflows e pipelines usam variáveis relativas nativas do Apache Hop:
  - `${Internal.Workflow.Filename.Folder}` (diretório relativo do workflow em execução);
  - `${Internal.Pipeline.Filename.Folder}` (diretório relativo do pipeline em execução);
- Não há caminhos absolutos ou fixados (*hardcoded*) no projeto;
- As fontes de dados em `dados/brutos/` e os scripts SQL em `sql/` são localizados de forma relativa a partir das pastas dos workflows e pipelines.

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
