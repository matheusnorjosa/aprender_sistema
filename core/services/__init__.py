"""
Services Layer - Centralizacao da logica de negocio
Implementa Single Source of Truth e DRY principles
"""

from .data_services import (
    UsuarioService,
    FormadorService,
    CoordinatorService,
    DashboardService,
    MunicipioService
)

__all__ = [
    'UsuarioService',
    'FormadorService',
    'CoordinatorService',
    'DashboardService',
    'MunicipioService'
]