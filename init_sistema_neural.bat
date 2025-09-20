@echo off
title Sistema Neural APRENDER - Inicialização Automática
color 0A

echo.
echo ========================================
echo   SISTEMA NEURAL APRENDER
echo   Inicialização Automática
echo ========================================
echo.

echo 🚀 Inicializando Sistema Neural APRENDER...
cd /d "%~dp0"

echo 📋 Verificando ambiente virtual...
if not exist "venv\Scripts\python.exe" (
    echo ❌ Ambiente virtual não encontrado!
    echo 💡 Execute: python -m venv venv
    pause
    exit /b 1
)

echo ✅ Ambiente virtual encontrado!

echo 📦 Verificando dependências...
venv\Scripts\python.exe -c "import mcp, pandas, ijson, orjson, mistletoe" 2>nul
if errorlevel 1 (
    echo ⚠️ Dependências não encontradas!
    echo 💡 Execute: venv\Scripts\pip.exe install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ Dependências verificadas!

echo 🔧 Executando inicialização automática...
venv\Scripts\python.exe cursor_auto_init.py

echo.
echo ✅ Inicialização concluída!
echo.
echo 📋 Próximos passos:
echo    1. Abra o Cursor
echo    2. Os comandos MCP serão executados automaticamente
echo    3. Use @aprender-context para acessar as ferramentas
echo.
echo 🎯 Sistema Neural APRENDER pronto para uso!
echo.
pause
