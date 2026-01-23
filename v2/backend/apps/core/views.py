"""
Core views - Re-export Facade

PA-01: Nenhuma solicitação é auto-aprovada.
PA-02: Apenas Superintendência pode aprovar/reprovar.
PA-05: Registrar usuário, data/hora e justificativa em AuditLog.

This file maintains backwards compatibility by re-exporting
all views from the modular views/ package submodules.
"""

# pyright: reportUnusedImport=false, reportPrivateUsage=false

from __future__ import annotations

from apps.core.views.admin import (
    AuditLogViewSet,
    CompraViewSet,
    GerenciaViewSet,
    GroupViewSet,
    MunicipioViewSet,
    ProdutoViewSet,
    ProjetoViewSet,
    UsuarioAdminViewSet,
)
from apps.core.views.availability import AvailabilityBlockViewSet, AvailabilityCheckManyView, AvailabilityCheckView
from apps.core.views.options import (
    CoordenadorOptionViewSet,
    FormadorOptionViewSet,
    MunicipioOptionViewSet,
    ProjetoOptionViewSet,
    TipoEventoOptionViewSet,
)
from apps.core.views.solicitacao import SolicitacaoViewSet

# Import directly from submodules to avoid circular import with views/ package
from apps.core.views.utils import _get_client_ip, api_root
from apps.core.views_basic import CurrentUserView

__all__ = [
    "_get_client_ip",
    "api_root",
    "SolicitacaoViewSet",
    "AvailabilityBlockViewSet",
    "AvailabilityCheckView",
    "AvailabilityCheckManyView",
    "CurrentUserView",
    "MunicipioViewSet",
    "ProjetoViewSet",
    "ProdutoViewSet",
    "GerenciaViewSet",
    "CompraViewSet",
    "UsuarioAdminViewSet",
    "GroupViewSet",
    "AuditLogViewSet",
    "MunicipioOptionViewSet",
    "ProjetoOptionViewSet",
    "CoordenadorOptionViewSet",
    "FormadorOptionViewSet",
    "TipoEventoOptionViewSet",
]
