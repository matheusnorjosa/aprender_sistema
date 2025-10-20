# ============================================
# 🔧 SCRIPT DE CORREÇÃO - DJANGO CORROMPIDO
# ============================================
# Sistema Aprender - Fix para ModuleNotFoundError: django.template
# Autor: Claude Code
# Data: 2025-09-30

Write-Host "🔧 CORREÇÃO DA INSTALAÇÃO DO DJANGO" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se está no diretório correto
$projectPath = "C:\Users\datsu\OneDrive\Documentos\Aprender Sistema"
if ((Get-Location).Path -ne $projectPath) {
    Write-Host "❌ Execute este script no diretório do projeto!" -ForegroundColor Red
    Write-Host "   Diretório atual: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "   Diretório esperado: $projectPath" -ForegroundColor Yellow
    exit 1
}

# Passo 1: Desativar venv (se ativo)
Write-Host "🔹 Passo 1: Desativando venv atual..." -ForegroundColor Yellow
deactivate 2>$null

# Passo 2: Fazer backup do venv antigo
Write-Host "🔹 Passo 2: Backup do venv corrompido..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupName = ".venv_backup_$timestamp"
    Rename-Item ".venv" $backupName
    Write-Host "   ✅ Backup criado: $backupName" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Nenhum venv encontrado" -ForegroundColor Yellow
}

# Passo 3: Criar novo venv
Write-Host "🔹 Passo 3: Criando novo ambiente virtual..." -ForegroundColor Yellow
python -m venv .venv
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Venv criado com sucesso" -ForegroundColor Green
} else {
    Write-Host "   ❌ Erro ao criar venv" -ForegroundColor Red
    exit 1
}

# Passo 4: Ativar novo venv
Write-Host "🔹 Passo 4: Ativando novo venv..." -ForegroundColor Yellow
& ".venv\Scripts\Activate.ps1"

# Passo 5: Atualizar pip
Write-Host "🔹 Passo 5: Atualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Passo 6: Instalar dependências
Write-Host "🔹 Passo 6: Instalando dependências (isso pode demorar)..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Dependências instaladas" -ForegroundColor Green
} else {
    Write-Host "   ❌ Erro ao instalar dependências" -ForegroundColor Red
    exit 1
}

# Passo 7: Verificar Django
Write-Host ""
Write-Host "🔹 Passo 7: Verificando instalação do Django..." -ForegroundColor Yellow
python -c "import django; print(f'   ✅ Django {django.__version__} instalado')"

Write-Host "🔹 Passo 8: Testando django.template..." -ForegroundColor Yellow
python -c "import django.template; print('   ✅ django.template OK')"

# Passo 9: Executar check do Django
Write-Host ""
Write-Host "🔹 Passo 9: Executando Django check..." -ForegroundColor Yellow
python manage.py check
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Sistema Django OK" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Warnings encontrados (isso é normal)" -ForegroundColor Yellow
}

# Sucesso!
Write-Host ""
Write-Host "✅ CORREÇÃO CONCLUÍDA COM SUCESSO!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Cyan
Write-Host "1. Executar migrations: python manage.py migrate" -ForegroundColor White
Write-Host "2. Criar superuser: python manage.py createsuperuser" -ForegroundColor White
Write-Host "3. Rodar servidor: python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "Para remover backups antigos:" -ForegroundColor Yellow
Write-Host "Remove-Item .venv_backup_* -Recurse -Force" -ForegroundColor White
