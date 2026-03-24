"""
Testes para /api/me/ com grupos e flag is_superintendencia.

Cobertura:
- Endpoint inclui lista de grupos
- Flag is_superintendencia = True apenas para usuários do grupo "Superintendência"
- Case-sensitive para nome do grupo
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import GroupClassificacao, PermissaoFuncional, Usuario

pytestmark = pytest.mark.django_db


def test_me_includes_groups_and_flag():
    """
    /api/me/ deve retornar groups (lista) e is_superintendencia (bool).
    """
    user = Usuario.objects.create_user(username="u1", email="u1@x.com", password="x", cpf="11111111111")
    group1, _ = Group.objects.get_or_create(name="Coordenador")
    group2, _ = Group.objects.get_or_create(name="Formador")
    user.groups.add(group1, group2)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    data = res.json()

    assert "groups" in data, "Missing 'groups' field"
    assert "is_superintendencia" in data, "Missing 'is_superintendencia' field"
    assert "permissions" in data, "Missing 'permissions' field"

    assert isinstance(data["groups"], list), "groups should be a list"
    assert isinstance(data["permissions"], list), "permissions should be a list"
    assert set(data["groups"]) == {"Coordenador", "Formador"}
    assert all(isinstance(item, str) for item in data["permissions"])
    assert data["is_superintendencia"] is False, "User not in Superintendência"


def test_is_superintendencia_true_only_for_group():
    """
    is_superintendencia = True apenas se usuário pertence ao grupo "Superintendência" (case-sensitive).
    """
    user = Usuario.objects.create_user(username="u2", email="u2@x.com", password="x", cpf="22222222222")
    super_group, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(super_group)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["is_superintendencia"] is True, "User in Superintendência should have flag = True"
    assert "Superintendência" in data["groups"]


def test_is_superintendencia_false_for_similar_name():
    """
    Grupo com nome parecido (ex: "superintendencia" minúsculo) não ativa flag.
    """
    user = Usuario.objects.create_user(username="u3", email="u3@x.com", password="x", cpf="33333333333")
    fake_group, _ = Group.objects.get_or_create(name="superintendencia")  # minúsculo
    user.groups.add(fake_group)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["is_superintendencia"] is False, "Name must match exactly (case-sensitive)"
    assert "superintendencia" in data["groups"]


def test_me_no_groups_returns_empty_list():
    """
    Usuário sem grupos retorna groups=[] e is_superintendencia=False.
    """
    user = Usuario.objects.create_user(username="u4", email="u4@x.com", password="x", cpf="44444444444")

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["groups"] == []
    assert data["permissions"] == []
    assert data["is_superintendencia"] is False


def test_superuser_always_has_access():
    """
    Superusers sempre têm is_superintendencia=True, mesmo sem grupo.
    """
    user = Usuario.objects.create_superuser(username="admin", email="admin@x.com", password="x", cpf="55555555555")

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["is_superuser"] is True
    assert data["is_superintendencia"] is True, "Superuser should always have access"


def test_me_returns_effective_functional_permissions():
    """
    /api/me/ deve retornar permissions (codenames) vindos do mapeamento funcional.
    """
    user = Usuario.objects.create_user(username="u5", email="u5@x.com", password="x", cpf="66666666666")
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(dat_group)

    perm = PermissaoFuncional.objects.create(
        codename="acoes.notificacao.manage",
        label="Gerenciar notificações",
        description="Teste de permissões efetivas",
        category="acoes",
        is_system=False,
    )
    perm.groups.add(dat_group)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    assert "permissions" in data
    assert "acoes.notificacao.manage" in data["permissions"]


def test_me_classifies_dynamic_funcao_group():
    """
    Grupo classificado dinamicamente como função deve aparecer em funcoes.
    """
    user = Usuario.objects.create_user(username="u6", email="u6@x.com", password="x", cpf="77777777777")
    dynamic_group, _ = Group.objects.get_or_create(name="Analista de Campo")
    GroupClassificacao.objects.update_or_create(
        group=dynamic_group,
        defaults={"tipo": GroupClassificacao.Tipo.FUNCAO},
    )
    user.groups.add(dynamic_group)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    assert "Analista de Campo" in data["groups"]
    assert "Analista de Campo" in data["funcoes"]
    assert "Analista de Campo" not in data["setores"]
