#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${HOP_HOME:?Defina HOP_HOME}"
set -a; source "$ROOT_DIR/.env"; set +a
RUN_ID="teste-conexao-$(date -u +%Y%m%dT%H%M%SZ)"
set +e
POSTGRES_PORT=65432 "$HOP_HOME/hop-run.sh" --environment desafio4-dev \
  --file "$ROOT_DIR/hop/pipelines/bronze_catalogo.hpl" --runconfig local --level BASIC \
  --parameters="RUN_ID=$RUN_ID,CATALOGO_PATH=$ROOT_DIR/dados/brutos/catalogo.csv"
rc=$?
set -e
[[ $rc -ne 0 ]] || { echo "ERRO: falha de conexão não detectada"; exit 1; }
echo "OK: falha de conexão detectada (exit=$rc)."
