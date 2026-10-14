"""
M10-04 (#1626) — validação de shape de `extra_participants` no create.

`perform_create` lia `extra_participants` cru de request.data e passava direto
para `_create_participants`, sem serializer:
- um item não-string em *_emails estourava `.strip()` → HTTP 500;
- listas sem limite de tamanho (DoS de materialização);
- usuários INATIVOS viravam participantes por id.

Contrato: `extra_participants` é validado por `_ExtraParticipantsSerializer`
(listas limitadas de ids inteiros positivos / e-mails válidos); payload
malformado → 400 (nunca 500); só usuários ativos entram por id.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    liberar_par,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_1626", cpf="77000000001")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao M1626")


@pytest.fixture
def projeto(municipio):
    proj = ProjetoFactory(nome="Projeto 1626", codigo="P1626", fluxo="NAO_SUPER", ativo=True)
    # #1738: criar exige Compra para o par município+projeto.
    liberar_par(municipio, proj)
    return proj


@pytest.fixture
def client_coord(coordenador):
    c = APIClient()
    c.force_authenticate(coordenador)
    return c


def _payload(municipio, projeto, tipo_evento, extra):
    inicio = timezone.now() + timedelta(days=3)
    return {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_evento": tipo_evento.id,
        "coordenador_acompanha": False,
        "tipo": "PRESENCIAL",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
        "extra_participants": extra,
    }


class TestMalformedExtraParticipants:
    def test_non_str_email_returns_400_not_500(self, client_coord, municipio, projeto, tipo_evento):
        """RED: item não-string em *_emails estoura .strip() → 500."""
        resp = client_coord.post(
            "/api/solicitacoes/",
            _payload(municipio, projeto, tipo_evento, {"formador_emails": [12345]}),
            format="json",
        )
        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"

    def test_extra_participants_not_dict_returns_400(self, client_coord, municipio, projeto, tipo_evento):
        resp = client_coord.post(
            "/api/solicitacoes/",
            _payload(municipio, projeto, tipo_evento, "hax"),
            format="json",
        )
        assert resp.status_code == 400

    def test_formador_ids_non_int_returns_400(self, client_coord, municipio, projeto, tipo_evento):
        resp = client_coord.post(
            "/api/solicitacoes/",
            _payload(municipio, projeto, tipo_evento, {"formador_ids": ["abc"]}),
            format="json",
        )
        assert resp.status_code == 400


class TestParticipantResolution:
    def test_inactive_user_not_added_as_participant(self, client_coord, municipio, projeto, tipo_evento):
        inativo = UsuarioFactory(username="inativo_1626", cpf="77000000009", is_active=False)
        resp = client_coord.post(
            "/api/solicitacoes/",
            _payload(municipio, projeto, tipo_evento, {"formador_ids": [inativo.id]}),
            format="json",
        )
        assert resp.status_code == 201, resp.data
        sol_id = resp.json()["id"]
        parts = Participation.objects.filter(solicitacao_id=sol_id)
        # Só o COORDENADOR (o inativo não entra).
        assert parts.count() == 1
        assert parts.first().role == "COORDENADOR"

    def test_active_formador_added_as_participant(self, client_coord, municipio, projeto, tipo_evento):
        """Não-regressão: formador ativo válido vira participante."""
        formador = UsuarioFactory(username="form_1626", cpf="77000000010")
        formador.groups.add(GroupFactory(name="Formador"))
        payload = _payload(municipio, projeto, tipo_evento, {"formador_ids": [formador.id]})
        payload["pretende_avaliar_formador"] = False  # 05/10/2026: formador avaliável → pergunta obrigatória
        resp = client_coord.post("/api/solicitacoes/", payload, format="json")
        assert resp.status_code == 201, resp.data
        sol_id = resp.json()["id"]
        roles = set(Participation.objects.filter(solicitacao_id=sol_id).values_list("role", flat=True))
        assert "FORMADOR" in roles
