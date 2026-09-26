#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/hop"
: "${HOP_HOME:?Defina HOP_HOME apontando para a instalação do Apache Hop}"
CONF="$HOP_HOME/hop-conf.sh"
[[ -x "$CONF" ]] || { echo "Não encontrei $CONF"; exit 1; }

if ! "$CONF" --projects-list 2>/dev/null | grep -q "desafio4-aluno1"; then
  "$CONF" --project-create --project desafio4-aluno1 --project-home "$PROJECT_DIR" --project-config-file project-config.json
fi
if ! "$CONF" --environments-list 2>/dev/null | grep -q "desafio4-dev"; then
  "$CONF" --environment-create --environment desafio4-dev --environment-project desafio4-aluno1 \
    --environment-purpose Development --environment-config-files "$PROJECT_DIR/environments/dev-env-config.json"
fi
echo "Projeto desafio4-aluno1 e ambiente desafio4-dev configurados."
