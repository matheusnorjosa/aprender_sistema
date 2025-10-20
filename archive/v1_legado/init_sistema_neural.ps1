# Sistema Neural APRENDER - Inicialização Automática
Write-Host "🚀 Inicializando Sistema Neural APRENDER..." -ForegroundColor Green
Set-Location $PSScriptRoot
python cursor_auto_init.py
Write-Host "✅ Inicialização concluída!" -ForegroundColor Green
Read-Host "Pressione Enter para continuar"
