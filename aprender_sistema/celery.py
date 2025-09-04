"""
Configuração do Celery para o projeto Aprender Sistema
"""

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

# Configurar Django settings module para Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")

# Criar instância do Celery
app = Celery("aprender_sistema")

# Carregar configurações do Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobrir tasks automaticamente
app.autodiscover_tasks()

# Configurações específicas para migração
app.conf.update(
    # Configurar queues para diferentes tipos de tarefas
    task_routes={
        "core.tasks.migrate_usuarios": {"queue": "migration"},
        "core.tasks.migrate_formacoes": {"queue": "migration_heavy"},
        "core.tasks.migrate_eventos": {"queue": "migration"},
        "core.tasks.sync_google_calendar": {"queue": "google_sync"},
        "core.tasks.validate_migration": {"queue": "validation"},
    },
    # Configurações de performance para volumes altos
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    # Timeouts para operações longas
    task_soft_time_limit=600,  # 10 minutos
    task_time_limit=900,  # 15 minutos
    # Configurações de retry
    task_default_retry_delay=60,  # 1 minuto
    task_max_retries=3,
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Fortaleza",
    enable_utc=True,
)


@app.task(bind=True)
def debug_task(self):
    """Task de debug para testar Celery"""
    print(f"Request: {self.request!r}")
    return "Celery funcionando!"


@app.task
def test_migration_task():
    """Task de teste para migração"""
    import time

    print("Iniciando teste de migração...")
    time.sleep(5)  # Simular processamento
    print("Teste de migração concluído!")
    return {"status": "success", "message": "Migração testada com sucesso"}
