"""
Testes de retrocompatibilidade para arquitetura modular de serializers.

Garante que todos os imports antigos continuam funcionando
apos a modularizacao dos serializers.

Type-checked with Pyright (strict mode).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import pytest


class TestSerializersBackwardsCompatibility:
    """Verifica que imports de serializers continuam funcionando."""

    def test_import_from_serializers_module(self) -> None:
        """Import tradicional: from apps.core.serializers import X"""
        from apps.core.serializers import (
            AcaoControleSerializer,
            AcaoDATCreateSerializer,
            AcaoDATSerializer,
            AuditLogSerializer,
            AuditLogTimelineSerializer,
            AvailabilityBlockSerializer,
            CompraSerializer,
            ConfigSerializer,
            CurrentUserSerializer,
            DeslocamentoSerializer,
            EventDetailSerializer,
            GerenciaSerializer,
            GroupSerializer,
            MunicipioOptionSerializer,
            MunicipioSerializer,
            ParticipationNestedSerializer,
            ProdutoSerializer,
            ProjetoOptionSerializer,
            ProjetoSerializer,
            SolicitacaoSerializer,
            TipoEventoOptionSerializer,
            UserSlimSerializer,
            UsuarioAdminSerializer,
            UsuarioOptionSerializer,
        )

        # Usuario
        assert CurrentUserSerializer is not None
        assert UserSlimSerializer is not None
        assert UsuarioOptionSerializer is not None
        assert UsuarioAdminSerializer is not None
        assert GroupSerializer is not None
        # Organizacao
        assert MunicipioSerializer is not None
        assert MunicipioOptionSerializer is not None
        assert ProjetoSerializer is not None
        assert ProjetoOptionSerializer is not None
        assert GerenciaSerializer is not None
        assert TipoEventoOptionSerializer is not None
        assert ProdutoSerializer is not None
        # Solicitacao
        assert ParticipationNestedSerializer is not None
        assert SolicitacaoSerializer is not None
        assert AuditLogTimelineSerializer is not None
        assert EventDetailSerializer is not None
        # Agenda
        assert AvailabilityBlockSerializer is not None
        # Compra
        assert CompraSerializer is not None
        # Workflow
        assert AcaoControleSerializer is not None
        assert AcaoDATSerializer is not None
        assert AcaoDATCreateSerializer is not None
        assert DeslocamentoSerializer is not None
        # Auditoria
        assert AuditLogSerializer is not None
        # Config
        assert ConfigSerializer is not None

    def test_direct_import_usuario(self) -> None:
        """Import direto: from apps.core.serializers.usuario import X"""
        from apps.core.serializers.usuario import (
            CurrentUserSerializer,
            GroupSerializer,
            UserSlimSerializer,
            UsuarioAdminSerializer,
            UsuarioOptionSerializer,
        )

        assert CurrentUserSerializer is not None
        assert UserSlimSerializer is not None
        assert UsuarioOptionSerializer is not None
        assert UsuarioAdminSerializer is not None
        assert GroupSerializer is not None

    def test_direct_import_organizacao(self) -> None:
        """Import direto: from apps.core.serializers.organizacao import X"""
        from apps.core.serializers.organizacao import (
            GerenciaSerializer,
            MunicipioOptionSerializer,
            MunicipioSerializer,
            ProdutoSerializer,
            ProjetoOptionSerializer,
            ProjetoSerializer,
            TipoEventoOptionSerializer,
        )

        assert MunicipioSerializer is not None
        assert MunicipioOptionSerializer is not None
        assert ProjetoSerializer is not None
        assert ProjetoOptionSerializer is not None
        assert GerenciaSerializer is not None
        assert TipoEventoOptionSerializer is not None
        assert ProdutoSerializer is not None

    def test_direct_import_solicitacao(self) -> None:
        """Import direto: from apps.core.serializers.solicitacao import X"""
        from apps.core.serializers.solicitacao import (
            AuditLogTimelineSerializer,
            EventDetailSerializer,
            ParticipationNestedSerializer,
            SolicitacaoSerializer,
        )

        assert ParticipationNestedSerializer is not None
        assert SolicitacaoSerializer is not None
        assert AuditLogTimelineSerializer is not None
        assert EventDetailSerializer is not None

    def test_direct_import_agenda(self) -> None:
        """Import direto: from apps.core.serializers.agenda import X"""
        from apps.core.serializers.agenda import AvailabilityBlockSerializer

        assert AvailabilityBlockSerializer is not None

    def test_direct_import_compra(self) -> None:
        """Import direto: from apps.core.serializers.compra import X"""
        from apps.core.serializers.compra import CompraSerializer

        assert CompraSerializer is not None

    def test_direct_import_workflow(self) -> None:
        """Import direto: from apps.core.serializers.workflow import X"""
        from apps.core.serializers.workflow import (
            AcaoControleSerializer,
            AcaoDATCreateSerializer,
            AcaoDATSerializer,
            DeslocamentoSerializer,
        )

        assert AcaoControleSerializer is not None
        assert AcaoDATSerializer is not None
        assert AcaoDATCreateSerializer is not None
        assert DeslocamentoSerializer is not None

    def test_direct_import_auditoria(self) -> None:
        """Import direto: from apps.core.serializers.auditoria import X"""
        from apps.core.serializers.auditoria import AuditLogSerializer

        assert AuditLogSerializer is not None

    def test_direct_import_config(self) -> None:
        """Import direto: from apps.core.serializers.config import X"""
        from apps.core.serializers.config import ConfigSerializer

        assert ConfigSerializer is not None

    def test_serializers_are_same_class(self) -> None:
        """Verifica que e a mesma classe em ambos imports."""
        from apps.core.serializers import SolicitacaoSerializer as Serializer1
        from apps.core.serializers.solicitacao import SolicitacaoSerializer as Serializer2

        assert Serializer1 is Serializer2

        from apps.core.serializers import UsuarioAdminSerializer as Usuario1
        from apps.core.serializers.usuario import UsuarioAdminSerializer as Usuario2

        assert Usuario1 is Usuario2

        from apps.core.serializers import MunicipioSerializer as Mun1
        from apps.core.serializers.organizacao import MunicipioSerializer as Mun2

        assert Mun1 is Mun2

    def test_all_exports_defined(self) -> None:
        """Verifica que __all__ esta definido corretamente."""
        from apps.core import serializers

        assert hasattr(serializers, "__all__")
        # __all__ pode crescer com novos modulos; manter checagem minima + unicidade.
        assert len(serializers.__all__) >= 54
        assert len(serializers.__all__) == len(set(serializers.__all__))
