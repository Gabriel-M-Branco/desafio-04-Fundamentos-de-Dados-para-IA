#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${HOP_HOME:?Defina HOP_HOME apontando para a instalação do Apache Hop}"
[[ -f "$ROOT_DIR/.env" ]] || { echo "Crie $ROOT_DIR/.env a partir de .env.example"; exit 1; }
set -a; source "$ROOT_DIR/.env"; set +a
RUN_ID="${RUN_ID:-aluno1-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$ROOT_DIR/logs"
"$HOP_HOME/hop-run.sh" --environment desafio4-dev \
  --file "$ROOT_DIR/hop/workflows/carga_aluno1.hwf" --runconfig local --level BASIC \
  --logfile "$ROOT_DIR/logs/hop_${RUN_ID}.log" \
  --parameters="RUN_ID=${RUN_ID},CATALOGO_PATH=$ROOT_DIR/dados/brutos/catalogo.csv,INTERACOES_PATH=$ROOT_DIR/dados/brutos/interacoes.json,COMENTARIOS_PATH=$ROOT_DIR/dados/brutos/comentarios.json"
echo "RUN_ID=$RUN_ID"
echo "Log: $ROOT_DIR/logs/hop_${RUN_ID}.log"
