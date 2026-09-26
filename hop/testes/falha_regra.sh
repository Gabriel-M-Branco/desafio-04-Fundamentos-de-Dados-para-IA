#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${HOP_HOME:?Defina HOP_HOME}"
set -a; source "$ROOT_DIR/.env"; set +a

RUN_ID="teste-regra-$(date -u +%Y%m%dT%H%M%SZ)"

# Garante as estruturas.
docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$ROOT_DIR/sql/camadas_bronze_silver.sql"

# Insere um registro propositalmente inválido na Bronze.
docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL
INSERT INTO bronze.catalogo_raw(
  conteudo_id,titulo,tipo,categoria,nivel,carga_horaria_min,data_publicacao,
  descricao,autor,origem,data_hora_ingestao,id_execucao)
VALUES(
  '-99','', 'Ebook','Teste','Especialista','-10','2026-99-99',
  'Registro propositalmente inválido','FIC_DEV','falha_regra.sh',CURRENT_TIMESTAMP,'$RUN_ID');
SQL

# Executa somente a etapa Silver de catálogo para demonstrar erro de linha/quarentena.
"$HOP_HOME/hop-run.sh" --environment desafio4-dev \
  --file "$ROOT_DIR/hop/pipelines/silver_catalogo.hpl" --runconfig local --level BASIC \
  --parameters="RUN_ID=$RUN_ID"

echo "=== Registro esperado na quarentena ==="
docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT entidade,id_registro,regra_violada,mensagem_erro,id_execucao FROM quarentena.registros WHERE id_execucao='$RUN_ID';"

echo "RUN_ID=$RUN_ID"
