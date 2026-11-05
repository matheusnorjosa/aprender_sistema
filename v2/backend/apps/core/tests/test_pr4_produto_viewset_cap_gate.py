"""
PR 4 hardening RBAC (2026-04-30, #1258): matriz consolidada para
`ProdutoViewSet`. Endpoint deixa de ser `IsAuthenticated` puro e passa a
exigir capability operacional/admin.

Endpoint: `GET/POST/PATCH/DELETE /api/produtos/`

Capability exigida (leitura e escrita): `manage_admin_registries` (DAT), a mesma da tela
/dat/admin/produtos. Decisão do dono (05/11/2026): o Controle saiu; antes lia pela composition com
`manage_purchases_and_materials | run_daily_operations` e escrevia com `manage_purchases_and_materials`,
sem ter a tela.

Personas:
- ✅ DAT, superuser → 200
- ❌ Controle, Formador, Coordenador, Apoio, Gerente pedagógico, Diretoria → 403
- Anonymous → 401/403

Para dropdowns de formulários (Coordenador/Apoio criando solicitação
ou Diretoria em dashboards), o endpoint paralelo `/api/options/produtos/`
permanece `IsAuthenticated` (cobertura existente em test_views_options.py).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import itertools

from rest_framework.test import APIClient

import pytest

from apps.core.models import Produto
from apps.core.tests.factories import ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


_CPF_COUNTER = itertools.count(60000000000)


def _user_in_groups(*group_names: str, label: str = "user"):
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    return UsuarioFactory(
        username=f"{label}_{cpf}",
        email=f"{label}_{cpf}@example.com",
        password="testpass",
        cpf=cpf,
        groups=list(group_names),
    )


@pytest.fixture
def produto():
    projeto = ProjetoFactory(nome="Projeto Test", codigo="PT", ativo=True)
    return Produto.objects.create(codigo="P001", nome="Produto Teste", projeto=projeto, ativo=True)


# =============================================================================
# ✅ Allowed personas (DAT, Controle, superuser)
# =============================================================================


ALLOWED_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    ("dat", ("DAT",)),
]


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_list_produtos(persona, produto):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/produtos/")

    assert (
        response.status_code == 200
    ), f"{label} ({group_names}) deveria listar produtos; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", ALLOWED_PERSONAS, ids=[p[0] for p in ALLOWED_PERSONAS])
def test_allowed_personas_can_retrieve_produto(persona, produto):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(f"/api/produtos/{produto.id}/")

    assert response.status_code == 200, f"{label} deveria fazer retrieve; recebeu {response.status_code}"


def test_superuser_can_list_produtos(produto):
    user = UsuarioFactory(superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/produtos/")
    assert response.status_code == 200


# =============================================================================
# ❌ Forbidden personas
# =============================================================================


FORBIDDEN_PERSONAS: list[tuple[str, tuple[str, ...]]] = [
    ("controle", ("Controle",)),
    ("asst_admin_controle", ("Controle", "Assistente Administrativo")),
    ("formador", ("Formador",)),
    ("coordenador", ("Coordenador",)),
    ("apoio", ("Apoio de Coordenação",)),
    ("gerente_pedagogico", ("Vidas", "Gerente")),
    ("diretoria", ("Diretoria",)),
]


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403_on_list(persona, produto):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/produtos/")

    assert (
        response.status_code == 403
    ), f"{label} ({group_names}) deveria receber 403 em list; recebeu {response.status_code}"


@pytest.mark.parametrize("persona", FORBIDDEN_PERSONAS, ids=[p[0] for p in FORBIDDEN_PERSONAS])
def test_forbidden_personas_get_403_on_retrieve(persona, produto):
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(f"/api/produtos/{produto.id}/")

    assert response.status_code == 403


def test_anonymous_blocked_on_list():
    client = APIClient()
    response = client.get("/api/produtos/")
    assert response.status_code in (401, 403)


# =============================================================================
# Write operations (POST/PATCH/DELETE) também restritos
# =============================================================================


def test_dat_can_create_produto():
    user = _user_in_groups("DAT", label="dat_writer")
    projeto = ProjetoFactory(nome="Proj W", codigo="PW", ativo=True)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/produtos/",
        {"codigo": "PNEW", "nome": "Novo", "projeto": projeto.id, "ativo": True},
        format="json",
    )
    assert response.status_code in (200, 201), response.data


def test_dat_can_update_and_delete_produto(produto):
    user = _user_in_groups("DAT", label="dat_editor")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.patch(f"/api/produtos/{produto.id}/", {"nome": "Renomeado"}, format="json")
    assert response.status_code == 200, response.data

    response = client.delete(f"/api/produtos/{produto.id}/")
    assert response.status_code == 204
    assert not Produto.objects.filter(pk=produto.pk).exists()


@pytest.mark.parametrize(
    "group_names", [("Controle",), ("Controle", "Assistente Administrativo")], ids=["controle", "asst_admin"]
)
def test_controle_cannot_write_produto(group_names, produto):
    """O Controle tem `manage_purchases_and_materials`, que não abre a tela de Produtos → 403 nas escritas."""
    user = _user_in_groups(*group_names, label="controle_writer")
    client = APIClient()
    client.force_authenticate(user=user)

    criar = client.post(
        "/api/produtos/",
        {"codigo": "PCTL", "nome": "X", "projeto": produto.projeto_id, "ativo": True},
        format="json",
    )
    editar = client.patch(f"/api/produtos/{produto.id}/", {"nome": "Y"}, format="json")
    excluir = client.delete(f"/api/produtos/{produto.id}/")

    assert (criar.status_code, editar.status_code, excluir.status_code) == (403, 403, 403)
    produto.refresh_from_db()
    assert produto.nome == "Produto Teste"
    assert not Produto.objects.filter(codigo="PCTL").exists()


def test_coordenador_cannot_create_produto():
    user = _user_in_groups("Coordenador", label="coord_writer")
    projeto = ProjetoFactory(nome="Proj W2", codigo="PW2", ativo=True)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/produtos/",
        {"codigo": "PCOO", "nome": "X", "projeto": projeto.id, "ativo": True},
        format="json",
    )
    assert response.status_code == 403


# =============================================================================
# Endpoint paralelo /api/options/produtos/ permanece IsAuthenticated
# =============================================================================


@pytest.mark.parametrize(
    "persona",
    [
        ("coordenador_options", ("Coordenador",)),
        ("apoio_options", ("Apoio de Coordenação",)),
        ("formador_options", ("Formador",)),
    ],
    ids=lambda p: p[0],
)
def test_options_produtos_remains_open_to_authenticated(persona, produto):
    """Endpoint paralelo `/api/options/produtos/` continua autenticado puro
    para suportar selects/dropdowns sem precisar de capability."""
    label, group_names = persona
    user = _user_in_groups(*group_names, label=label)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/options/produtos/")

    assert (
        response.status_code == 200
    ), f"{label} deveria acessar /api/options/produtos/; recebeu {response.status_code}"
