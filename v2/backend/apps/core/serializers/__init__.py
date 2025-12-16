"""
AS v2 — Serializers Package

Re-exporta todos os serializers para manter retrocompatibilidade.
Import pattern: `from apps.core.serializers import SolicitacaoSerializer`

Type-checked with Pyright (strict mode).
"""
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
    ProdutoSerializer,
    ProjetoGeralOptionSerializer,
    ProjetoGeralSerializer,
    ProjetoOptionSerializer,
    ProjetoSerializer,
    TipoEventoOptionSerializer,
)
from apps.core.serializers.solicitacao import (
    AuditLogTimelineSerializer,
    EventDetailSerializer,
    ParticipationNestedSerializer,
    SolicitacaoSerializer,
)
from apps.core.serializers.usuario import (
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
    # Auditoria
    "AuditLogSerializer",
    # Config
    "ConfigSerializer",
]
