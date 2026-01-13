"""
Testes para /api/me/ com grupos e flag is_superintendencia.

Cobertura:
- Endpoint inclui lista de grupos
- Flag is_superintendencia = True apenas para usuários do grupo "Superintendência"
- Case-sensitive para nome do grupo
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.models import Usuario

pytestmark = pytest.mark.django_db


def test_me_includes_groups_and_flag():
    """
    /api/me/ deve retornar groups (lista) e is_superintendencia (bool).
    """
    user = Usuario.objects.create_user(
        username="u1", email="u1@x.com", password="x", cpf="11111111111"
    )
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

    assert isinstance(data["groups"], list), "groups should be a list"
    assert set(data["groups"]) == {"Coordenador", "Formador"}
    assert data["is_superintendencia"] is False, "User not in Superintendência"


def test_is_superintendencia_true_only_for_group():
    """
    is_superintendencia = True apenas se usuário pertence ao grupo "Superintendência" (case-sensitive).
    """
    user = Usuario.objects.create_user(
        username="u2", email="u2@x.com", password="x", cpf="22222222222"
    )
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
    user = Usuario.objects.create_user(
        username="u3", email="u3@x.com", password="x", cpf="33333333333"
    )
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
    user = Usuario.objects.create_user(
        username="u4", email="u4@x.com", password="x", cpf="44444444444"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["groups"] == []
    assert data["is_superintendencia"] is False


def test_superuser_always_has_access():
    """
    Superusers sempre têm is_superintendencia=True, mesmo sem grupo.
    """
    user = Usuario.objects.create_superuser(
        username="admin", email="admin@x.com", password="x", cpf="55555555555"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:current-user")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data["is_superuser"] is True
    assert data["is_superintendencia"] is True, "Superuser should always have access"
