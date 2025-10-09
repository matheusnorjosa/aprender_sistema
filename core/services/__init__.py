"""
Services Layer - Centralizacao da logica de negocio
Implementa Single Source of Truth and DRY principles
"""

from .data_services import (
    CoordinatorService,
    DashboardService,
    FormadorService,
    MunicipioService,
    ProjetoService,
    UsuarioService,
)
from .pessoas import get_pessoas_super_qs

__all__ = [
    "UsuarioService",
    "FormadorService",
    "CoordinatorService",
    "DashboardService",
    "MunicipioService",
    "ProjetoService",
    "get_pessoas_super_qs",
]
