"""
AS v2 — Core Views Package

Re-exports all views for backwards compatibility.
"""
# pyright: reportUnusedImport=false

from apps.core.views.utils import _get_client_ip, api_root
from apps.core.views.solicitacao import SolicitacaoViewSet
from apps.core.views.availability import (
    AvailabilityBlockViewSet,
    AvailabilityCheckManyView,
    AvailabilityCheckView,
)
from apps.core.views_basic import CurrentUserView
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
from apps.core.views.dat import (
    DATRegistroViewSet,
    ProjetoGeralViewSet,
)
from apps.core.views.options import (
    CoordenadorOptionViewSet,
    FormadorOptionViewSet,
    MunicipioOptionViewSet,
    ProjetoOptionViewSet,
    TipoEventoOptionViewSet,
)

__all__ = [
    # Utils
    "_get_client_ip",
    "api_root",
    # Solicitacao
    "SolicitacaoViewSet",
    # Availability
    "AvailabilityBlockViewSet",
    "AvailabilityCheckView",
    "AvailabilityCheckManyView",
    # User
    "CurrentUserView",
    # Admin
    "MunicipioViewSet",
    "ProjetoViewSet",
    "ProdutoViewSet",
    "GerenciaViewSet",
    "CompraViewSet",
    "UsuarioAdminViewSet",
    "GroupViewSet",
    "AuditLogViewSet",
    # DAT Registros
    "DATRegistroViewSet",
    "ProjetoGeralViewSet",
    # Options
    "MunicipioOptionViewSet",
    "ProjetoOptionViewSet",
    "CoordenadorOptionViewSet",
    "FormadorOptionViewSet",
    "TipoEventoOptionViewSet",
]
