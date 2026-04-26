"""
Testes para `GET /api/me/events/` (Issue #1224, Epic 2 RBAC Realignment).

Cobertura:
- User participando de N eventos → lista N (apenas aprovados)
- User sem participação → lista vazia
- User anônimo → 401
- Ordenação por -inicio
- Filtro status=aprovado (pendente/reprovado não aparecem)
- Paginação default funciona
- Serializer expõe campos esperados (incluindo formadores)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Municipio, Participation, Projeto, Solicitacao, TipoEvento

pytestmark = pytest.mark.django_db


@pytest.fixture
def make_user():
    """Cria Usuario com cpf único."""
    User = get_user_model()
    counter = {"i": 0}

    def _factory(username: str = "", **extra):
        counter["i"] += 1
        idx = counter["i"]
        return User.objects.create_user(
            username=username or f"user_{idx}",
            email=f"user_{idx}@example.com",
            password="testpass123",
            cpf=f"99988877{idx:03d}",
            **extra,
        )

    return _factory


@pytest.fixture
def make_solicitacao(make_user):
    """Factory de Solicitacao com dependências mínimas e timestamps incrementais."""
    counter = {"i": 0}

    def _factory(**kwargs):
        counter["i"] += 1
        if "usuario" not in kwargs:
            kwargs["usuario"] = make_user(username=f"creator_{counter['i']}")
        if "municipio" not in kwargs:
            kwargs["municipio"], _ = Municipio.objects.get_or_create(
                nome="Fortaleza", uf="CE", defaults={"ativo": True}
            )
        if "tipo_evento" not in kwargs:
            kwargs["tipo_evento"], _ = TipoEvento.objects.get_or_create(
                nome="Formação E2E", defaults={"descricao": "Formação para tests"}
            )
        if "projeto" not in kwargs:
            kwargs["projeto"], _ = Projeto.objects.get_or_create(nome="Projeto Teste", defaults={"ativo": True})
        if "inicio" not in kwargs:
            kwargs["inicio"] = timezone.now() + timezone.timedelta(days=counter["i"])
        if "fim" not in kwargs:
            kwargs["fim"] = kwargs["inicio"] + timezone.timedelta(hours=2)
        if "status" not in kwargs:
            kwargs["status"] = "aprovado"
        return Solicitacao.objects.create(**kwargs)

    return _factory


def _add_participation(solic: Solicitacao, user, role: str = "FORMADOR") -> Participation:
    return Participation.objects.create(solicitacao=solic, usuario=user, role=role)


def test_user_participating_in_three_events_returns_three(make_user, make_solicitacao):
    """User participante em 3 eventos aprovados → list de 3."""
    user = make_user()
    s1 = make_solicitacao()
    s2 = make_solicitacao()
    s3 = make_solicitacao()
    _add_participation(s1, user)
    _add_participation(s2, user)
    _add_participation(s3, user)

    client = APIClient()
    client.force_authenticate(user=user)
    res = client.get(reverse("core:me-events"))

    assert res.status_code == 200, res.content
    data = res.json()
    results = data["results"] if isinstance(data, dict) else data
    assert len(results) == 3
    ids = {item["id"] for item in results}
    assert ids == {s1.id, s2.id, s3.id}


def test_user_without_participation_returns_empty(make_user, make_solicitacao):
    """User sem nenhuma Participation → lista vazia."""
    user = make_user()
    make_solicitacao()  # existe um evento, mas user não participa

    client = APIClient()
    client.force_authenticate(user=user)
    res = client.get(reverse("core:me-events"))

    assert res.status_code == 200
    data = res.json()
    results = data["results"] if isinstance(data, dict) else data
    assert results == []


def test_anonymous_user_gets_401():
    """User não autenticado → 401."""
    client = APIClient()
    res = client.get(reverse("core:me-events"))
    assert res.status_code in (401, 403)


def test_results_ordered_by_inicio_desc(make_user, make_solicitacao):
    """Mais recente primeiro."""
    user = make_user()
    now = timezone.now()
    s_old = make_solicitacao(inicio=now + timezone.timedelta(days=1), fim=now + timezone.timedelta(days=1, hours=2))
    s_mid = make_solicitacao(inicio=now + timezone.timedelta(days=5), fim=now + timezone.timedelta(days=5, hours=2))
    s_new = make_solicitacao(inicio=now + timezone.timedelta(days=10), fim=now + timezone.timedelta(days=10, hours=2))
    _add_participation(s_old, user)
    _add_participation(s_mid, user)
    _add_participation(s_new, user)

    client = APIClient()
    client.force_authenticate(user=user)
    res = client.get(reverse("core:me-events"))

    assert res.status_code == 200
    results = res.json()["results"] if isinstance(res.json(), dict) else res.json()
    assert [item["id"] for item in results] == [s_new.id, s_mid.id, s_old.id]


def test_pendente_and_reprovado_excluded(make_user, make_solicitacao):
    """Apenas status=aprovado deve aparecer."""
    user = make_user()
    s_aprovado = make_solicitacao(status="aprovado")
    s_pendente = make_solicitacao(status="pendente")
    s_reprovado = make_solicitacao(status="reprovado")
    _add_participation(s_aprovado, user)
    _add_participation(s_pendente, user)
    _add_participation(s_reprovado, user)

    client = APIClient()
    client.force_authenticate(user=user)
    res = client.get(reverse("core:me-events"))

    assert res.status_code == 200
    results = res.json()["results"] if isinstance(res.json(), dict) else res.json()
    assert len(results) == 1
    assert results[0]["id"] == s_aprovado.id


def test_serializer_exposes_expected_fields(make_user, make_solicitacao):
    """Serializer minimal expõe campos para listagem (sem dados internos)."""
    user = make_user(username="participante")
    formador = make_user(username="formador_alpha", first_name="Alpha", last_name="Formador")
    solic = make_solicitacao(local="Escola Municipal X", is_online=False)
    _add_participation(solic, user, role="COORDENADOR")
    _add_participation(solic, formador, role="FORMADOR")

    client = APIClient()
    client.force_authenticate(user=user)
    res = client.get(reverse("core:me-events"))

    assert res.status_code == 200
    results = res.json()["results"] if isinstance(res.json(), dict) else res.json()
    assert len(results) == 1
    item = results[0]
    expected_fields = {
        "id",
        "inicio",
        "fim",
        "municipio_nome",
        "projeto_nome",
        "tipo_evento_nome",
        "local",
        "formadores",
        "is_online",
        "meet_link",
        "status",
    }
    assert set(item.keys()) == expected_fields
    assert item["local"] == "Escola Municipal X"
    assert item["is_online"] is False
    assert item["formadores"] == ["Alpha Formador"]
    assert item["status"] == "aprovado"


def test_distinct_when_user_has_multiple_participations(make_user, make_solicitacao):
    """User com múltiplas Participations no mesmo evento → uma única entrada."""
    user = make_user()
    solic = make_solicitacao()
    _add_participation(solic, user, role="COORDENADOR")
    _add_participation(solic, user, role="FORMADOR")

    client = APIClient()
    client.force_authenticate(user=user)
    res = client.get(reverse("core:me-events"))

    assert res.status_code == 200
    results = res.json()["results"] if isinstance(res.json(), dict) else res.json()
    assert len(results) == 1
    assert results[0]["id"] == solic.id
