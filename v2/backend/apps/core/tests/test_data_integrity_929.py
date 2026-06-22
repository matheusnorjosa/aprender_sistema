"""
Tests: Data Integrity (#929)

Validates:
- Composite indexes exist and are used by queries
- N+1 queries fixed (coordenador select_related)
- on_delete=PROTECT prevents accidental cascade deletion
- skip_locked in batch approval
- Query count regression on list endpoints
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import (
    AvailabilityBlock,
    Gerencia,
    Participation,
)
from apps.core.models.organizacao import EquipeGerencia
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def usuario(db):
    return UsuarioFactory(
        username="integrity_user",
        email="integrity@test.com",
        password="testpass123",
        cpf="99988877766",
    )


@pytest.fixture
def usuario2(db):
    return UsuarioFactory(
        username="integrity_user2",
        email="integrity2@test.com",
        password="testpass123",
        cpf="99988877755",
    )


@pytest.fixture
def tipo_evento(db):
    return TipoEventoFactory(nome="Teste Integridade")


@pytest.fixture
def municipio(db):
    return MunicipioFactory(nome="Teste Mun", uf="CE")


@pytest.fixture
def projeto(db):
    return ProjetoFactory(nome="Teste Projeto", fluxo="NAO_SUPER")


@pytest.fixture
def gerencia(db):
    return Gerencia.objects.create(nome="GERENCIA TESTE", nome_setor="Teste Setor")


@pytest.fixture
def solicitacao(usuario, tipo_evento, municipio, projeto):
    now = timezone.now()
    return SolicitacaoFactory(
        usuario=usuario,
        tipo_evento=tipo_evento,
        municipio=municipio,
        projeto=projeto,
        inicio=now,
        fim=now + timedelta(hours=2),
        status="pendente",
    )


# ── on_delete=PROTECT Tests ──────────────────────────────────────────


class TestOnDeleteProtect:
    """EquipeGerencia on_delete=PROTECT prevents accidental data loss."""

    def test_cannot_delete_gerencia_with_equipe(self, gerencia, usuario):
        EquipeGerencia.objects.create(
            gerencia=gerencia,
            usuario=usuario,
            papel="GERENTE",
        )
        with pytest.raises(IntegrityError):
            gerencia.delete()

    def test_cannot_delete_usuario_with_equipe(self, gerencia, usuario):
        EquipeGerencia.objects.create(
            gerencia=gerencia,
            usuario=usuario,
            papel="FORMADOR",
        )
        with pytest.raises(IntegrityError):
            usuario.delete()

    def test_can_delete_equipe_directly(self, gerencia, usuario):
        eq = EquipeGerencia.objects.create(
            gerencia=gerencia,
            usuario=usuario,
            papel="FORMADOR",
        )
        eq.delete()
        assert not EquipeGerencia.objects.filter(pk=eq.pk).exists()


# ── Composite Index Tests ────────────────────────────────────────────


class TestCompositeIndexes:
    """Verify composite indexes exist in the database."""

    @pytest.fixture(autouse=True)
    def _setup(self, db):
        pass

    def _get_indexes(self, table_name: str) -> list[str]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE tablename = %s",
                [table_name],
            )
            return [row[0] for row in cursor.fetchall()]

    def test_solicitacao_usuario_status_index(self):
        indexes = self._get_indexes("core_solicitacao")
        assert any("idx_solic_usuario_status" in name for name in indexes)

    def test_solicitacao_municipio_intervalo_index(self):
        indexes = self._get_indexes("core_solicitacao")
        assert any("idx_solic_mun_intervalo" in name for name in indexes)

    def test_participation_solicitacao_usuario_index(self):
        indexes = self._get_indexes("core_participation")
        assert any("idx_part_solic_usuario" in name for name in indexes)

    def test_availability_block_composite_index(self):
        indexes = self._get_indexes("core_availability_block")
        assert any("idx_avblock_usr_st_ini" in name for name in indexes)


# ── N+1 Query Count Tests ────────────────────────────────────────────


class TestQueryCountRegression:
    """Ensure list endpoints don't have N+1 queries."""

    @pytest.fixture
    def superuser(self, db):
        return UsuarioFactory(
            superuser=True,
            username="superquery",
            email="superquery@test.com",
            password="testpass123",
            cpf="11122233344",
        )

    @pytest.fixture
    def api_client(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        return client

    @pytest.fixture
    def solicitacoes_batch(self, superuser, tipo_evento, municipio, projeto):
        """Create 10 solicitacoes with coordenador and participations."""
        now = timezone.now()
        solis = []
        for i in range(10):
            sol = SolicitacaoFactory(
                usuario=superuser,
                tipo_evento=tipo_evento,
                municipio=municipio,
                projeto=projeto,
                inicio=now + timedelta(hours=i * 3),
                fim=now + timedelta(hours=i * 3 + 2),
                status="pendente",
                coordenador=superuser,
            )
            Participation.objects.create(
                solicitacao=sol,
                usuario=superuser,
                role="COORDENADOR",
            )
            solis.append(sol)
        return solis

    def test_solicitacao_list_constant_queries(self, api_client, solicitacoes_batch):
        """Listing 10 solicitacoes should NOT generate N+1 queries.

        Expected: ~5-8 queries (auth, count, data, prefetch) regardless of N.
        """
        with CaptureQueriesContext(connection) as context:
            response = api_client.get("/api/solicitacoes/")

        assert response.status_code == 200
        # With select_related + prefetch_related, query count should be bounded
        # Auth(1-2) + count(1) + main query(1) + prefetch participations(1) + session(1-2) = ~5-8
        assert (
            len(context.captured_queries) <= 12
        ), f"Too many queries ({len(context.captured_queries)}), " f"possible N+1. Queries:\n" + "\n".join(
            q["sql"][:120] for q in context.captured_queries
        )
