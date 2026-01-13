"""
Testes de retrocompatibilidade para arquitetura modular.

Garante que todos os imports antigos continuam funcionando
apos a modularizacao dos models.

Type-checked with Pyright (strict mode).
"""
# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest


class TestModelsBackwardsCompatibility:
    """Verifica que imports de models continuam funcionando."""

    def test_import_from_models_module(self) -> None:
        """Import tradicional: from apps.core.models import X"""
        from apps.core.models import (
            AcaoControle,
            AcaoDAT,
            AuditLog,
            AvailabilityBlock,
            Compra,
            Config,
            Deslocamento,
            EquipeGerencia,
            Gerencia,
            GoogleOAuthCredential,
            Municipio,
            Participation,
            Produto,
            Projeto,
            Solicitacao,
            TipoEvento,
            Usuario,
        )
        assert Usuario is not None
        assert Municipio is not None
        assert Gerencia is not None
        assert EquipeGerencia is not None
        assert Projeto is not None
        assert TipoEvento is not None
        assert Produto is not None
        assert Solicitacao is not None
        assert Participation is not None
        assert AvailabilityBlock is not None
        assert Compra is not None
        assert Deslocamento is not None
        assert AcaoControle is not None
        assert AcaoDAT is not None
        assert Config is not None
        assert AuditLog is not None
        assert GoogleOAuthCredential is not None

    def test_direct_import_usuario(self) -> None:
        """Import direto: from apps.core.models.usuario import Usuario"""
        from apps.core.models.usuario import Usuario
        assert Usuario is not None
        assert Usuario._meta.db_table == "core_usuario"

    def test_direct_import_organizacao(self) -> None:
        """Import direto: from apps.core.models.organizacao import X"""
        from apps.core.models.organizacao import (
            EquipeGerencia,
            Gerencia,
            Municipio,
            Produto,
            Projeto,
            TipoEvento,
        )
        assert Municipio is not None
        assert Gerencia is not None
        assert EquipeGerencia is not None
        assert Projeto is not None
        assert TipoEvento is not None
        assert Produto is not None

    def test_direct_import_solicitacao(self) -> None:
        """Import direto: from apps.core.models.solicitacao import X"""
        from apps.core.models.solicitacao import Participation, Solicitacao
        assert Solicitacao is not None
        assert Participation is not None
        assert Solicitacao._meta.db_table == "core_solicitacao"

    def test_direct_import_agenda(self) -> None:
        """Import direto: from apps.core.models.agenda import X"""
        from apps.core.models.agenda import AvailabilityBlock
        assert AvailabilityBlock is not None
        assert AvailabilityBlock._meta.db_table == "core_availability_block"

    def test_direct_import_compra(self) -> None:
        """Import direto: from apps.core.models.compra import X"""
        from apps.core.models.compra import Compra
        assert Compra is not None
        assert Compra._meta.db_table == "core_compra"

    def test_direct_import_workflow(self) -> None:
        """Import direto: from apps.core.models.workflow import X"""
        from apps.core.models.workflow import AcaoControle, AcaoDAT, Deslocamento
        assert Deslocamento is not None
        assert AcaoControle is not None
        assert AcaoDAT is not None

    def test_direct_import_config(self) -> None:
        """Import direto: from apps.core.models.config import X"""
        from apps.core.models.config import Config
        assert Config is not None
        assert Config._meta.db_table == "core_config"

    def test_direct_import_auditoria(self) -> None:
        """Import direto: from apps.core.models.auditoria import X"""
        from apps.core.models.auditoria import AuditLog
        assert AuditLog is not None
        assert AuditLog._meta.db_table == "core_audit_log"

    def test_direct_import_integracao(self) -> None:
        """Import direto: from apps.core.models.integracao import X"""
        from apps.core.models.integracao import GoogleOAuthCredential
        assert GoogleOAuthCredential is not None
        assert GoogleOAuthCredential._meta.db_table == "core_google_oauth_credential"

    def test_models_are_same_class(self) -> None:
        """Verifica que e a mesma classe em ambos imports."""
        from apps.core.models import Usuario as Usuario1
        from apps.core.models.usuario import Usuario as Usuario2
        assert Usuario1 is Usuario2

        from apps.core.models import Solicitacao as Solicitacao1
        from apps.core.models.solicitacao import Solicitacao as Solicitacao2
        assert Solicitacao1 is Solicitacao2

        from apps.core.models import Municipio as Municipio1
        from apps.core.models.organizacao import Municipio as Municipio2
        assert Municipio1 is Municipio2

    def test_all_exports_defined(self) -> None:
        """Verifica que __all__ esta definido corretamente."""
        from apps.core import models
        assert hasattr(models, "__all__")
        assert len(models.__all__) == 29  # Total de models exportados (17 base + 8 DAT + 4 PlanoFormacoes)

    def test_solicitacao_gcal_status_enum(self) -> None:
        """Verifica que GCalStatus enum esta acessivel."""
        from apps.core.models import Solicitacao
        assert hasattr(Solicitacao, "GCalStatus")
        assert Solicitacao.GCalStatus.NONE == "NONE"
        assert Solicitacao.GCalStatus.PUBLISHED == "PUBLISHED"

    def test_participation_role_enum(self) -> None:
        """Verifica que Role enum esta acessivel."""
        from apps.core.models import Participation
        assert hasattr(Participation, "Role")
        assert Participation.Role.COORDENADOR == "COORDENADOR"
        assert Participation.Role.FORMADOR == "FORMADOR"
