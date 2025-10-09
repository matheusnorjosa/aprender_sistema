# SSOT Daily Job - PowerShell Script
# Executa espelho + comparador + commit via Docker
# Uso: pwsh scripts/ssot_daily.ps1 -GitUserName "ssot-bot" -GitUserEmail "ssot-bot@example.com"

param(
  [string]$GitUserName = "ssot-bot",
  [string]$GitUserEmail = "ssot-bot@example.com"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Run-Docker {
    param([string]$Command)
    Write-Host ">>> docker compose exec -T web $Command" -ForegroundColor Gray
    docker compose exec -T web bash -c $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Failed: $Command"
    }
}

try {
    Write-Step "SSOT Daily Job - Iniciando"

    # 1) Baixar espelhos (5 abas)
    Write-Step "1/3: Baixando espelhos do Google Sheets"

    # Executar via Python manage.py shell
    $downloadCmd = "from backend.config.sheets_config import *; import os,urllib.request; base='/app/data/ingest/daily'; os.makedirs(f'{base}/abas',exist_ok=True); url = lambda id,g: f'https://docs.google.com/spreadsheets/d/{id}/export?format=csv&gid={g}'; targets=[(url(AGENDA_2025_ID,ABAS['ACerta']),f'{base}/abas/acerta.csv'),(url(AGENDA_2025_ID,ABAS['Brincando']),f'{base}/abas/brincando.csv'),(url(AGENDA_2025_ID,ABAS['Vidas']),f'{base}/abas/vidas.csv'),(url(AGENDA_2025_ID,ABAS['Super']),f'{base}/abas/super.csv'),(url(AGENDA_2025_ID,ABAS['Outros']),f'{base}/abas/outros.csv')]; [print('OK',d) or None for u,d in targets for _ in [urllib.request.urlopen(u)] for f in [open(d,'wb')] if not f.write(_.read()) and not f.close()]"

    docker compose exec -T web python manage.py shell -c $downloadCmd
    if ($LASTEXITCODE -ne 0) { throw "Failed to download mirrors" }

    # 2) Executar comparador
    Write-Step "2/3: Executando comparador de fontes"

    docker compose exec -T web python manage.py compare_fontes --fonte-a sheets --fonte-b /app/data/ingest/daily/abas --abas ACerta,Brincando,Vidas,Super,Outros --limit 10
    if ($LASTEXITCODE -ne 0) { throw "Failed to run comparator" }

    # 3) Commit (via host git, não container)
    Write-Step "3/3: Commitando relatório (via host)"

    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $commitMsg = "chore: SSOT diário $timestamp"

    git add docs/VALIDACAO_FONTE_DUPLA.md

    # Verificar se há mudanças staged
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit --no-verify -m $commitMsg
        Write-Host "   Commit criado: $commitMsg" -ForegroundColor Green
    } else {
        Write-Host "   Nenhuma mudança detectada (arquivos idênticos)" -ForegroundColor Yellow
    }

    Write-Host "`n✅ SSOT Daily Job - Concluído com sucesso!" -ForegroundColor Green
    Write-Host "   Timestamp: $timestamp" -ForegroundColor Green

} catch {
    Write-Host "`n❌ SSOT Daily Job - Falhou!" -ForegroundColor Red
    Write-Host "   Erro: $_" -ForegroundColor Red
    exit 1
}
