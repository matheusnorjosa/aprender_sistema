"""
AS v2 — Core Views Package

Re-exports all views for backwards compatibility.
"""

# pyright: reportUnusedImport=false

from __future__ import annotations

from apps.core.views.acoes_notificacao import AcaoInstanciaViewSet, CicloAcoesViewSet, NotificacaoInternaViewSet
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
from apps.core.views.dat import DATRegistroViewSet, ProjetoGeralViewSet
from apps.core.views.dat_module import (
    DATAcaoViewSet,
    DATAreaViewSet,
    DATCadastroViewSet,
    DATCompraViewSet,
    DATCoordenadorViewSet,
    DATFormacaoViewSet,
)
from apps.core.views.options import (
    CoordenadorOptionViewSet,
    FormadorOptionViewSet,
    MunicipioOptionViewSet,
    ProjetoOptionViewSet,
    TipoEventoOptionViewSet,
)
from apps.core.views.plano_formacoes import PlanoFormacoesViewSet
from apps.core.views.solicitacao import SolicitacaoViewSet
from apps.core.views.stats import HomeStatsView
from apps.core.views.utils import _get_client_ip, api_root
from apps.core.views_basic import CurrentUserView

__all__ = [
    # Acoes/Notificacoes internas
    "CicloAcoesViewSet",
    "AcaoInstanciaViewSet",
    "NotificacaoInternaViewSet",
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
    # DAT Module
    "DATAreaViewSet",
    "DATCoordenadorViewSet",
    "DATAcaoViewSet",
    "DATCompraViewSet",
    "DATCadastroViewSet",
    "DATFormacaoViewSet",
    # Plano Formacoes
    "PlanoFormacoesViewSet",
    # Options
    "MunicipioOptionViewSet",
    "ProjetoOptionViewSet",
    "CoordenadorOptionViewSet",
    "FormadorOptionViewSet",
    "TipoEventoOptionViewSet",
    # Stats
    "HomeStatsView",
]
