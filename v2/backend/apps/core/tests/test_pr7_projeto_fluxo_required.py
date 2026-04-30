"""
PR 7 hardening RBAC (2026-04-30): `Projeto.fluxo` exigido explicitamente
em criação via API e Admin.

Antes deste PR, o field model tinha `default="NAO_SUPER"`, e o
serializer/admin silenciosamente assumiam esse valor quando ausente.
Após este PR:

- `ProjetoSerializer.fluxo` é `ChoiceField(required=True)` — POST sem
  `fluxo` retorna 400.
- `ProjetoAdminForm` força escolha explícita — formulário sem `fluxo`
  retorna erro de validação.
- O default permanece no model para uso interno (fixtures de teste,
  ORM direto), mas API e Admin não dependem mais dele.

Regression check (status inicial de Solicitação):
- `fluxo == "SUPER"` → solicitação nasce `pendente`.
- `fluxo == "NAO_SUPER"` → solicitação nasce `aprovado`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import itertools

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import Projeto, Usuario
from apps.core.serializers.organizacao import ProjetoSerializer

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(30000000000)


def _dat_user() -> Usuario:
    """DAT puro — tem cap `manage_admin_registries` para acessar ProjetoViewSet."""
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = Usuario.objects.create_user(
        username=f"dat_pr7_{cpf}",
        email=f"dat_pr7_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
    )
    grupo, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(grupo)
    return user


# =============================================================================
# Serializer: fluxo é obrigatório em create
# =============================================================================


def test_serializer_create_without_fluxo_returns_validation_error():
    """ProjetoSerializer (sem `fluxo`) → invalid; mensagem do DRF."""
    serializer = ProjetoSerializer(data={"nome": "Sem fluxo", "ativo": True})
    assert not serializer.is_valid(), "Serializer deveria rejeitar payload sem fluxo"
    assert "fluxo" in serializer.errors


def test_serializer_create_with_invalid_fluxo_returns_validation_error():
    """Valor fora de SUPER/NAO_SUPER → invalid (choices)."""
    serializer = ProjetoSerializer(data={"nome": "Fluxo inválido", "ativo": True, "fluxo": "OUTROS"})
    assert not serializer.is_valid()
    assert "fluxo" in serializer.errors


@pytest.mark.parametrize("fluxo", ["SUPER", "NAO_SUPER"])
def test_serializer_create_with_valid_fluxo_passes(fluxo):
    """SUPER/NAO_SUPER explícitos → válidos."""
    serializer = ProjetoSerializer(data={"nome": f"Projeto {fluxo}", "fluxo": fluxo, "ativo": True})
    assert serializer.is_valid(), f"Serializer deveria aceitar fluxo={fluxo}, erros={serializer.errors}"


# =============================================================================
# API: POST /api/projetos/
# =============================================================================


def test_api_post_without_fluxo_returns_400():
    user = _dat_user()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/projetos/",
        {"nome": "API sem fluxo", "ativo": True},
        format="json",
    )
    assert response.status_code == 400
    body = response.json()
    errors = body.get("errors", body)
    assert "fluxo" in errors, f"Esperava erro em 'fluxo'; payload={body}"


def test_api_post_with_invalid_fluxo_returns_400():
    user = _dat_user()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/projetos/",
        {"nome": "API fluxo errado", "fluxo": "OUTROS", "ativo": True},
        format="json",
    )
    assert response.status_code == 400
    body = response.json()
    errors = body.get("errors", body)
    assert "fluxo" in errors, f"Esperava erro em 'fluxo'; payload={body}"


@pytest.mark.parametrize("fluxo", ["SUPER", "NAO_SUPER"])
def test_api_post_with_valid_fluxo_creates(fluxo):
    user = _dat_user()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/projetos/",
        {"nome": f"API com {fluxo}", "fluxo": fluxo, "ativo": True},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["fluxo"] == fluxo


# =============================================================================
# API: PATCH /api/projetos/{id}/
# =============================================================================


def test_api_patch_without_fluxo_keeps_current_value():
    """PATCH parcial não requer fluxo; valor atual permanece."""
    user = _dat_user()
    client = APIClient()
    client.force_authenticate(user=user)

    projeto = Projeto.objects.create(nome="P PATCH", fluxo="SUPER", ativo=True)

    response = client.patch(
        f"/api/projetos/{projeto.id}/",
        {"ativo": False},
        format="json",
    )
    assert response.status_code == 200, response.data
    projeto.refresh_from_db()
    assert projeto.fluxo == "SUPER", f"PATCH sem fluxo deveria preservar valor; got {projeto.fluxo}"
    assert projeto.ativo is False


def test_api_patch_with_invalid_fluxo_returns_400():
    user = _dat_user()
    client = APIClient()
    client.force_authenticate(user=user)

    projeto = Projeto.objects.create(nome="P PATCH inválido", fluxo="SUPER", ativo=True)

    response = client.patch(
        f"/api/projetos/{projeto.id}/",
        {"fluxo": "X"},
        format="json",
    )
    assert response.status_code == 400
    projeto.refresh_from_db()
    assert projeto.fluxo == "SUPER", "Valor original deveria permanecer após erro"


# =============================================================================
# Admin form: ProjetoAdminForm rejeita sem fluxo
# =============================================================================


def test_admin_form_without_fluxo_is_invalid():
    from apps.core.admin import ProjetoAdminForm

    form = ProjetoAdminForm(data={"nome": "Admin sem fluxo", "ativo": True})
    assert not form.is_valid(), "Admin form deveria rejeitar criação sem fluxo"
    assert "fluxo" in form.errors


@pytest.mark.parametrize("fluxo", ["SUPER", "NAO_SUPER"])
def test_admin_form_with_valid_fluxo_is_valid(fluxo):
    from apps.core.admin import ProjetoAdminForm

    form = ProjetoAdminForm(
        data={
            "nome": f"Admin {fluxo}",
            "codigo": "",
            "fluxo": fluxo,
            "ativo": True,
            "is_test": False,
            "descricao": "",
        }
    )
    assert form.is_valid(), f"Admin form deveria aceitar fluxo={fluxo}; erros={form.errors}"


# =============================================================================
# Regression: status inicial de Solicitação não muda
# =============================================================================


def test_resolve_initial_status_super_returns_pendente():
    """Regression: PR 7 não muda regra de status inicial — SUPER → pendente."""
    from apps.core.services.solicitacao_create import resolve_initial_status

    projeto = Projeto.objects.create(nome="P SUPER reg", fluxo="SUPER", ativo=True)
    decision = resolve_initial_status(projeto=projeto)
    assert decision.status == "pendente", f"got={decision.status}"


def test_resolve_initial_status_nao_super_returns_aprovado():
    """Regression: NAO_SUPER → aprovado (auto-aprovação preservada)."""
    from apps.core.services.solicitacao_create import resolve_initial_status

    projeto = Projeto.objects.create(nome="P NAO_SUPER reg", fluxo="NAO_SUPER", ativo=True)
    decision = resolve_initial_status(projeto=projeto)
    assert decision.status == "aprovado", f"got={decision.status}"
