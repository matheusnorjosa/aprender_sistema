"""
M10-01 (#1623) — escopo ator×gerência para Solicitacao.

`approve_solicitation_batch` é concedida ao grupo FUNÇÃO "Gerente" inteiro
(seed), não só ao aprovador composto. Antes, o `get_queryset` dava alcance
NACIONAL a quem tivesse essa cap, e o `IsOwnerOrPrivileged` liberava edição de
qualquer objeto — então um Gerente pedagógico (não-Superintendência), que nem
pode aprovar, lia/editava/excluía solicitações de QUALQUER gerência.

Contrato:
- GLOBAL (superuser / Controle / DAT / aprovador-composto) → vê e edita tudo.
- GESTOR não-global (Gerente) → só a(s) própria(s) gerência(s) + as próprias.
- Fora do escopo → 404 (indistinguível de inexistente).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao M1623")


@pytest.fixture
def gerencia_a():
    return Gerencia.objects.create(nome="GERENCIA A 1623", nome_setor="Vidas", ativo=True)


@pytest.fixture
def gerencia_b():
    return Gerencia.objects.create(nome="GERENCIA B 1623", nome_setor="Fluir", ativo=True)


@pytest.fixture
def coordenador_a():
    """Dono das solicitações da gerência A (não é o Gerente)."""
    return UsuarioFactory(username="coord_a_1623", cpf="78000000001")


@pytest.fixture
def gerente_a(gerencia_a):
    """Gerente pedagógico da gerência A (grupo Gerente → approve_solicitation_batch)."""
    user = UsuarioFactory(username="gerente_a_1623", cpf="78000000002")
    user.groups.add(GroupFactory(name="Gerente"))
    EquipeGerencia.objects.create(usuario=user, gerencia=gerencia_a, papel="GERENTE")
    return user


def _solic(owner, municipio, tipo_evento, projeto):
    inicio = timezone.now() + timedelta(days=4)
    return SolicitacaoFactory(
        usuario=owner,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="aprovado",
    )


@pytest.fixture
def sol_a(coordenador_a, municipio, tipo_evento, gerencia_a):
    projeto = ProjetoFactory(nome="Proj A 1623", gerencia=gerencia_a)
    return _solic(coordenador_a, municipio, tipo_evento, projeto)


@pytest.fixture
def sol_b(municipio, tipo_evento, gerencia_b):
    owner = UsuarioFactory(username="coord_b_1623", cpf="78000000003")
    projeto = ProjetoFactory(nome="Proj B 1623", gerencia=gerencia_b)
    return _solic(owner, municipio, tipo_evento, projeto)


def _url(pk):
    return f"/api/solicitacoes/{pk}/"


class TestGerenteScopedToOwnGerencia:
    def test_gerente_lista_apenas_propria_gerencia(self, gerente_a, sol_a, sol_b):
        """RED: hoje o Gerente vê as duas (alcance nacional)."""
        client = APIClient()
        client.force_authenticate(gerente_a)
        resp = client.get("/api/solicitacoes/")
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.data.get("results", resp.data)}
        assert sol_a.id in ids
        assert sol_b.id not in ids  # RED: sol_b aparecia

    def test_gerente_retrieve_outra_gerencia_404(self, gerente_a, sol_b):
        client = APIClient()
        client.force_authenticate(gerente_a)
        resp = client.get(_url(sol_b.id))
        assert resp.status_code == 404  # RED: 200

    def test_gerente_patch_outra_gerencia_404(self, gerente_a, sol_b):
        client = APIClient()
        client.force_authenticate(gerente_a)
        resp = client.patch(_url(sol_b.id), {"observacoes": "invadido"}, format="json")
        assert resp.status_code == 404  # RED: 200 e editava
        sol_b.refresh_from_db()
        assert sol_b.observacoes != "invadido"

    def test_gerente_delete_outra_gerencia_404(self, gerente_a, sol_b):
        client = APIClient()
        client.force_authenticate(gerente_a)
        resp = client.delete(_url(sol_b.id))
        assert resp.status_code == 404  # RED: 204 e excluía
        assert Solicitacao.objects.filter(pk=sol_b.id).exists()


class TestInScopeAndGlobalStillWork:
    def test_gerente_acessa_propria_gerencia(self, gerente_a, sol_a):
        client = APIClient()
        client.force_authenticate(gerente_a)
        resp = client.get(_url(sol_a.id))
        assert resp.status_code == 200
        assert resp.data["id"] == sol_a.id

    def test_superuser_ve_todas(self, sol_a, sol_b):
        su = UsuarioFactory(username="su_1623", cpf="78000000009", superuser=True)
        client = APIClient()
        client.force_authenticate(su)
        resp = client.get("/api/solicitacoes/")
        ids = {item["id"] for item in resp.data.get("results", resp.data)}
        assert sol_a.id in ids and sol_b.id in ids

    def test_gerente_da_superintendencia_ve_todas(self, sol_a, sol_b):
        """Aprovador composto (Gerente + Superintendência) é GLOBAL."""
        user = UsuarioFactory(username="gsuper_1623", cpf="78000000010")
        user.groups.add(GroupFactory(name="Gerente"), GroupFactory(name="Superintendência"))
        client = APIClient()
        client.force_authenticate(user)
        resp = client.get("/api/solicitacoes/")
        ids = {item["id"] for item in resp.data.get("results", resp.data)}
        assert sol_a.id in ids and sol_b.id in ids

    def test_dono_ve_a_propria_mesmo_fora_da_gerencia(self, sol_b):
        """O dono sempre vê a própria solicitação."""
        client = APIClient()
        client.force_authenticate(sol_b.usuario)
        resp = client.get(_url(sol_b.id))
        assert resp.status_code == 200
