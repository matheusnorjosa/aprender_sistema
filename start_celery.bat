@echo off
echo Iniciando Celery Worker para Aprender Sistema...
echo.

REM Ativar ambiente virtual se existir
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Ambiente virtual ativado.
)

echo Configurações:
echo - Broker: Database (desenvolvimento)
echo - Queues: migration, migration_heavy, google_sync, validation
echo.

REM Iniciar Celery Worker
echo Iniciando Celery Worker...
celery -A aprender_sistema worker --loglevel=info --concurrency=2

pause