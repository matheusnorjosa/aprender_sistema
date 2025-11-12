"""
AS v2 — Config Package

Expõe a aplicação Celery para que possa ser descoberta automaticamente
quando Django é iniciado.

Isso permite que tasks sejam descobertos e registrados corretamente.
"""

from __future__ import annotations

from .celery import app as celery_app

__all__ = ("celery_app",)
