#!/usr/bin/env bash
# Script Bash para execução do fluxo completo do Desafio 4 no Linux e macOS
set -e

# Detecta se python3 ou python está no PATH
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[ERRO] Interpretador Python não encontrado no PATH."
    exit 1
fi

echo "================================================================="
echo "EXECUTANDO FLUXO COMPLETO DO PIPELINE (DESAFIO 4)"
echo "Ambiente: $(uname -s) | Python: $($PY_CMD --version)"
echo "================================================================="

$PY_CMD scripts/executar_fluxo_completo.py "$@"
