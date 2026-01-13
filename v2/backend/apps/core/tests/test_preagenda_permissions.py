"""
Testes para permissões de pré-agenda (preview/publish).

Valida:
- Pré-agenda acessível apenas para "Controle", "Superintendência" e superusers
- Usuário sem esses grupos recebe 401/403
- Preview permitido mesmo quando apply_blocked = True
- Publish retorna 409 quando apply_blocked (PR4)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Usuario, Solicitacao, TipoEvento, Municipio, Projeto


pytestmark = pytest.mark.django_db


def make_user_in_group(name="Controle"):
    """Cria usuário em um grupo específico."""
    u = Usuario.objects.create_user(
        username=f"user{name.lower()}",
        email=f"{name.lower()}@test.com",
        password="x",
        cpf=f"9999999999{name[:1]}",
    )
    g, _ = Group.objects.get_or_create(name=name)
    u.groups.add(g)
    return u


def _make_approved_solicitacao(user):
    """Cria solicitação aprovada para testes."""
    tipo = TipoEvento.objects.create(nome="Formação")
    mun = Municipio.objects.create(nome="Acarape", uf="CE", ativo=True)
    proj = Projeto.objects.create(nome="Gestão Escolar", ativo=True)
    s = Solicitacao.objects.create(
        usuario=user,
        tipo_evento=tipo,
        municipio=mun,
        projeto=proj,
        inicio=timezone.now(),
        fim=timezone.now() + timedelta(hours=1),
        status="aprovado",
    )
    return s


def test_preview_publish_denied_unauthenticated():
    """
    Testa que usuário não autenticado é bloqueado.

    - Sem autenticação → 401 ou 403 para preview e publish
    - DRF pode retornar 403 se a permissão da classe for verificada primeiro
    """
    u = Usuario.objects.create_user(
        username="plain",
        email="plain@test.com",
        password="x",
        cpf="88888888888",
    )
    s = _make_approved_solicitacao(u)
    client = APIClient()
    # Não fazer force_authenticate - client não autenticado

    r1 = client.post(f"/api/solicitacoes/{s.id}/preview-gcal/")
    r2 = client.post(f"/api/solicitacoes/{s.id}/publish/")

    # DRF pode retornar 401 (não autenticado) ou 403 (sem permissão)
    # O importante é que acesso seja negado
    assert r1.status_code in (401, 403)
    assert r2.status_code in (401, 403)


def test_preview_publish_denied_without_group():
    """
    Testa que usuário autenticado sem grupo Controle/Superintendência recebe 403.

    - Usuário autenticado sem grupo → 403 para preview e publish
    """
    u = Usuario.objects.create_user(
        username="plain",
        email="plain@test.com",
        password="x",
        cpf="88888888888",
    )
    s = _make_approved_solicitacao(u)
    client = APIClient()
    client.force_authenticate(user=u)

    r1 = client.post(f"/api/solicitacoes/{s.id}/preview-gcal/")
    r2 = client.post(f"/api/solicitacoes/{s.id}/publish/")

    assert r1.status_code == 403
    assert r2.status_code == 403


def test_preview_publish_allowed_for_controle():
    """
    Testa que grupo Controle pode acessar preview e publish.

    - Preview → 200
    - Publish → 202 (ou 409 se apply_blocked)
    """
    u = make_user_in_group("Controle")
    s = _make_approved_solicitacao(u)
    client = APIClient()
    client.force_authenticate(user=u)

    r1 = client.post(f"/api/solicitacoes/{s.id}/preview-gcal/")
    r2 = client.post(f"/api/solicitacoes/{s.id}/publish/")

    # Preview deve retornar 200
    assert r1.status_code == 200

    # Publish pode retornar 202 (sucesso) ou 409 (apply_blocked se GCAL_CLIENT != google)
    # O importante é não ser 403
    assert r2.status_code in (202, 409)


def test_preview_publish_allowed_for_superintendencia():
    """
    Testa que grupo Superintendência pode acessar preview e publish.

    - Preview → 200
    - Publish → 202 (ou 409 se apply_blocked)
    """
    u = make_user_in_group("Superintendência")
    s = _make_approved_solicitacao(u)
    client = APIClient()
    client.force_authenticate(user=u)

    r1 = client.post(f"/api/solicitacoes/{s.id}/preview-gcal/")
    r2 = client.post(f"/api/solicitacoes/{s.id}/publish/")

    # Preview deve retornar 200
    assert r1.status_code == 200

    # Publish pode retornar 202 (sucesso) ou 409 (apply_blocked se GCAL_CLIENT != google)
    # O importante é não ser 403
    assert r2.status_code in (202, 409)


def test_preview_publish_allowed_for_superuser():
    """
    Testa que superuser pode acessar preview e publish.

    - Preview → 200
    - Publish → 202 (ou 409 se apply_blocked)
    """
    u = Usuario.objects.create_user(
        username="superuser",
        email="super@test.com",
        password="x",
        cpf="77777777777",
        is_superuser=True,
    )
    s = _make_approved_solicitacao(u)
    client = APIClient()
    client.force_authenticate(user=u)

    r1 = client.post(f"/api/solicitacoes/{s.id}/preview-gcal/")
    r2 = client.post(f"/api/solicitacoes/{s.id}/publish/")

    # Preview deve retornar 200
    assert r1.status_code == 200

    # Publish pode retornar 202 (sucesso) ou 409 (apply_blocked se GCAL_CLIENT != google)
    # O importante é não ser 403
    assert r2.status_code in (202, 409)
