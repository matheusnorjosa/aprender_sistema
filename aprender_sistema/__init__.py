# Configuração do Celery
from __future__ import absolute_import, unicode_literals

# Importar Celery app para que seja carregado quando Django iniciar
from .celery import app as celery_app

__all__ = ('celery_app',)