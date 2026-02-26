"""
AS v2 — Serializers Package

Re-exporta todos os serializers para manter retrocompatibilidade.
Import pattern: `from apps.core.serializers import SolicitacaoSerializer`

Type-checked with Pyright (strict mode).
"""

from __future__ import annotations

from apps.core.serializers.agenda import AvailabilityBlockSerializer
from apps.core.serializers.auditoria import AuditLogSerializer
from apps.core.serializers.compra import CompraSerializer
from apps.core.serializers.config import ConfigSerializer
from apps.core.serializers.dat_module import (
    DATAcaoListSerializer,
    DATAcaoSerializer,
    DATAreaOptionSerializer,
    DATAreaSerializer,
    DATCadastroListSerializer,
    DATCadastroSerializer,
    DATCompraListSerializer,
    DATCompraSerializer,
    DATCoordenadorListSerializer,
    DATCoordenadorOptionSerializer,
    DATCoordenadorSerializer,
    DATFormacaoCalendarioSerializer,
    DATFormacaoListSerializer,
    DATFormacaoSerializer,
)
from apps.core.serializers.dat_registro import (
    DATRegistroCreateSerializer,
    DATRegistroDetailSerializer,
    DATRegistroListSerializer,
    DATRegistroUpdateSerializer,
)
from apps.core.serializers.organizacao import (
    GerenciaSerializer,
    MunicipioOptionSerializer,
    MunicipioSerializer,
    ProdutoOptionSerializer,
    ProdutoSerializer,
    ProjetoGeralOptionSerializer,
    ProjetoGeralSerializer,
    ProjetoOptionSerializer,
    ProjetoSerializer,
    TipoEventoOptionSerializer,
)
from apps.core.serializers.plano_formacoes import (
    AcompanhamentoNestedSerializer,
    AcompanhamentoSerializer,
    FormacaoNestedSerializer,
    FormacaoSerializer,
    PlanoFormacoesListSerializer,
    PlanoFormacoesOptionSerializer,
    PlanoFormacoesSerializer,
    ProvaNestedSerializer,
    ProvaSerializer,
)
from apps.core.serializers.solicitacao import (
    AuditLogTimelineSerializer,
    EventDetailSerializer,
    ParticipationNestedSerializer,
    SolicitacaoSerializer,
)
from apps.core.serializers.usuario import (
    CurrentUserSerializer,
    GroupSerializer,
    UserSlimSerializer,
    UsuarioAdminSerializer,
    UsuarioOptionSerializer,
)
from apps.core.serializers.workflow import (
    AcaoControleSerializer,
    AcaoDATCreateSerializer,
    AcaoDATSerializer,
    DeslocamentoSerializer,
)

__all__ = [
    # Usuario
    "CurrentUserSerializer",
    "UserSlimSerializer",
    "UsuarioOptionSerializer",
    "UsuarioAdminSerializer",
    "GroupSerializer",
    # Organizacao
    "MunicipioSerializer",
    "MunicipioOptionSerializer",
    "ProjetoGeralSerializer",
    "ProjetoGeralOptionSerializer",
    "ProjetoSerializer",
    "ProjetoOptionSerializer",
    "GerenciaSerializer",
    "TipoEventoOptionSerializer",
    "ProdutoSerializer",
    "ProdutoOptionSerializer",
    # Solicitacao
    "ParticipationNestedSerializer",
    "SolicitacaoSerializer",
    "AuditLogTimelineSerializer",
    "EventDetailSerializer",
    # Agenda
    "AvailabilityBlockSerializer",
    # Compra
    "CompraSerializer",
    # Workflow
    "AcaoControleSerializer",
    "AcaoDATSerializer",
    "AcaoDATCreateSerializer",
    "DeslocamentoSerializer",
    # DAT Registros
    "DATRegistroListSerializer",
    "DATRegistroCreateSerializer",
    "DATRegistroUpdateSerializer",
    "DATRegistroDetailSerializer",
    # DAT Module
    "DATAreaSerializer",
    "DATAreaOptionSerializer",
    "DATCoordenadorSerializer",
    "DATCoordenadorOptionSerializer",
    "DATCoordenadorListSerializer",
    "DATAcaoSerializer",
    "DATAcaoListSerializer",
    "DATCompraSerializer",
    "DATCompraListSerializer",
    "DATCadastroSerializer",
    "DATCadastroListSerializer",
    "DATFormacaoSerializer",
    "DATFormacaoListSerializer",
    "DATFormacaoCalendarioSerializer",
    # Plano Formacoes (novo modelo estruturado)
    "PlanoFormacoesSerializer",
    "PlanoFormacoesListSerializer",
    "PlanoFormacoesOptionSerializer",
    "FormacaoSerializer",
    "FormacaoNestedSerializer",
    "AcompanhamentoSerializer",
    "AcompanhamentoNestedSerializer",
    "ProvaSerializer",
    "ProvaNestedSerializer",
    # Auditoria
    "AuditLogSerializer",
    # Config
    "ConfigSerializer",
]
