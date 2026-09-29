# Script PowerShell para execução do fluxo completo do Desafio 4
param (
    [switch]$SemTestes
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "EXECUTANDO FLUXO COMPLETO DO PIPELINE (DESAFIO 4)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

if ($SemTestes) {
    python scripts/executar_fluxo_completo.py --sem-testes
} else {
    python scripts/executar_fluxo_completo.py
}
