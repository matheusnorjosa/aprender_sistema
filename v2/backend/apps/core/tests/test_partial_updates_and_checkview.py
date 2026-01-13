"""
Testes de regressão para patches de PATCH parcial e AvailabilityCheckView.

Cobertura:
- PATCH parcial em Solicitacao (apenas observacoes, sem erro 500)
- PATCH parcial em AvailabilityBlock (apenas motivo, sem erro 500)
- AvailabilityCheckView com usuario_id inválido (400 em vez de crash)
- AvailabilityCheckView com municipio_id inválido (400 em vez de crash)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    AvailabilityBlock,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def municipio():
    """Fixture para criar município de teste."""
    return Municipio.objects.create(nome="Fortaleza", uf="CE")


@pytest.fixture
def tipo_evento():
    """Fixture para criar tipo de evento de teste."""
    return TipoEvento.objects.create(nome="Formação")


@pytest.fixture
def projeto():
    """Fixture para criar projeto de teste."""
    return Projeto.objects.create(nome="Projeto Teste", descricao="Desc")


def auth_client(user=None):
    """Helper para criar cliente autenticado."""
    client = APIClient()
    user = user or Usuario.objects.create_user(
        username="u1", email="u1@x.com", password="x"
    )
    client.force_authenticate(user=user)
    return client, user


def test_partial_update_solicitacao_only_observacoes_ok(municipio, tipo_evento):
    """
    PATCH parcial em Solicitacao (apenas observacoes) não deve causar erro 500.

    Antes do patch: KeyError porque validate() tentava acessar data['inicio']/data['fim']
    Depois do patch: 200/202 porque validate() busca na instância
    """
    c, u = auth_client()
    now = timezone.now()
    s = Solicitacao.objects.create(
        usuario=u,
        municipio=municipio,
        tipo_evento=tipo_evento,
        inicio=now,
        fim=now + timezone.timedelta(hours=2),
        status="pendente",
        observacoes="orig",
    )
    url = reverse("core:solicitacao-detail", args=[s.id])
    res = c.patch(url, {"observacoes": "novo"}, format="json")
    assert res.status_code in (200, 202), f"Expected 200/202, got {res.status_code}: {res.data}"
    s.refresh_from_db()
    assert s.observacoes == "novo"


def test_partial_update_block_only_motivo_ok():
    """
    PATCH parcial em AvailabilityBlock (apenas motivo) não deve causar erro 500.

    Antes do patch: KeyError porque validate() tentava acessar data['inicio']/data['fim']
    Depois do patch: 200/202 porque validate() busca na instância
    """
    c, u = auth_client()
    now = timezone.now()
    b = AvailabilityBlock.objects.create(
        usuario=u,
        inicio=now,
        fim=now + timezone.timedelta(hours=2),
        tipo="T",
        status="pendente",
        motivo="orig",
    )
    url = reverse("core:availability-block-detail", args=[b.id])
    res = c.patch(url, {"motivo": "novo"}, format="json")
    assert res.status_code in (200, 202), f"Expected 200/202, got {res.status_code}: {res.data}"
    b.refresh_from_db()
    assert b.motivo == "novo"


def test_availability_check_invalid_user_id_returns_400():
    """
    AvailabilityCheckView com usuario_id="abc" deve retornar 400, não crash.

    Antes do patch: ValueError não tratado causava 500
    Depois do patch: 400 com mensagem clara

    Para validar parâmetros (400), usuário deve ter permissão.
    Adiciona usuário ao grupo Controle para passar RBAC (403→400).
    """
    from django.contrib.auth.models import Group

    c, u = auth_client()

    # Dar permissão ao usuário (evitar 403 antes de validar parâmetros)
    grupo_controle, _ = Group.objects.get_or_create(name="Controle")
    u.groups.add(grupo_controle)

    now = timezone.now()
    url = reverse("core:availability-check")
    res = c.get(
        url,
        {
            "usuario_id": "abc",
            "inicio": now.isoformat(),
            "fim": (now + timezone.timedelta(hours=1)).isoformat(),
        },
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.data}"
    assert "usuario_id inválido" in res.json().get("detail", "").lower()


def test_availability_check_invalid_municipio_id_returns_400():
    """
    AvailabilityCheckView com municipio_id="zzz" deve retornar 400, não crash.

    Antes do patch: ValueError não tratado causava 500
    Depois do patch: 400 com mensagem clara

    Para validar parâmetros (400), usuário deve ter permissão.
    Adiciona usuário ao grupo Controle para passar RBAC (403→400).
    """
    from django.contrib.auth.models import Group

    c, u = auth_client()

    # Dar permissão ao usuário (evitar 403 antes de validar parâmetros)
    grupo_controle, _ = Group.objects.get_or_create(name="Controle")
    u.groups.add(grupo_controle)

    now = timezone.now()
    url = reverse("core:availability-check")
    res = c.get(
        url,
        {
            "usuario_id": u.id,
            "inicio": now.isoformat(),
            "fim": (now + timezone.timedelta(hours=1)).isoformat(),
            "municipio_id": "zzz",
        },
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.data}"
    assert "municipio_id inválido" in res.json().get("detail", "").lower()


def test_availability_check_missing_dates_returns_400():
    """
    AvailabilityCheckView sem inicio/fim deve retornar 400 claro.

    Para validar parâmetros (400), usuário deve ter permissão.
    Adiciona usuário ao grupo Controle para passar RBAC (403→400).
    """
    from django.contrib.auth.models import Group

    c, u = auth_client()

    # Dar permissão ao usuário (evitar 403 antes de validar parâmetros)
    grupo_controle, _ = Group.objects.get_or_create(name="Controle")
    u.groups.add(grupo_controle)

    url = reverse("core:availability-check")

    # Falta inicio
    res = c.get(url, {"usuario_id": u.id, "fim": timezone.now().isoformat()})
    assert res.status_code == 400
    assert "obrigatório" in res.json().get("detail", "").lower()

    # Falta fim
    res = c.get(url, {"usuario_id": u.id, "inicio": timezone.now().isoformat()})
    assert res.status_code == 400
    assert "obrigatório" in res.json().get("detail", "").lower()


def test_availability_check_fim_before_inicio_returns_400():
    """
    AvailabilityCheckView com fim <= inicio deve retornar 400.

    Nova validação adicionada no PATCH 2.

    Para validar parâmetros (400), usuário deve ter permissão.
    Adiciona usuário ao grupo Controle para passar RBAC (403→400).
    """
    from django.contrib.auth.models import Group

    c, u = auth_client()

    # Dar permissão ao usuário (evitar 403 antes de validar parâmetros)
    grupo_controle, _ = Group.objects.get_or_create(name="Controle")
    u.groups.add(grupo_controle)

    now = timezone.now()
    url = reverse("core:availability-check")
    res = c.get(
        url,
        {
            "usuario_id": u.id,
            "inicio": (now + timezone.timedelta(hours=2)).isoformat(),
            "fim": now.isoformat(),  # fim antes de inicio
        },
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.data}"
    assert "posterior" in res.json().get("detail", "").lower()
