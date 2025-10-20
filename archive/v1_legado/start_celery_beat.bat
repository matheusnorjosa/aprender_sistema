@echo off
echo Iniciando Celery Beat (Scheduler) para Aprender Sistema...
echo.

REM Ativar ambiente virtual se existir
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Ambiente virtual ativado.
)

echo Configurações:
echo - Scheduler: Database (django-celery-beat)
echo - Timezone: America/Fortaleza
echo.

REM Iniciar Celery Beat
echo Iniciando Celery Beat...
celery -A aprender_sistema beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

pause