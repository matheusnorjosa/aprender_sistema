"""
M10-04 (#1626) — validação de shape de `extra_participants` no UPDATE.

O create já era blindado pelo `_ExtraParticipantsSerializer` (#1626), mas o
`perform_update`/`_update_formadores` ainda lia o dict cru:
- `{"formador_ids": "abc"}` → `_update_formadores` itera a string, monta
  `id__in={'a','b','c'}` e estoura `ValueError` no `Usuario.objects.filter`
  (`views_solicitacao.py`) → HTTP 500;
- `{"formador_ids": {...}}` (Mapping) → mesmo caminho → 500;
- listas sem `max_length` (DoS de materialização no PATCH).

Contrato: o UPDATE valida `extra_participants` pelo MESMO serializer do create
(listas limitadas de ids inteiros positivos) → payload malformado vira 400,
nunca 500. Preserva a semântica "campo ausente = não mexer neste papel":
enviar só `formador_ids` NÃO apaga os COORD_ACOMPANHA (e vice-versa).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, Participation
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_HASH = itertools.count(1)
_CPF = itertools.count(79000000001)


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_1626u", cpf=str(next(_CPF)))
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza 1626u", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao M1626u")


@pytest.fixture
def projeto(municipio):
    proj = ProjetoFactory(nome="Projeto 1626u", codigo="P1626U", fluxo="NAO_SUPER", ativo=True)
    # #1738: criar exige Compra para o par município+projeto.
    Compra.objects.create(
        codigo="C-1626U",
        projeto=proj,
        municipio=municipio,
        quantidade=1,
        data=date(2026, 3, 1),
        uso="teste",
        external_hash=f"{next(_HASH):064d}",
    )
    return proj


@pytest.fixture
def client_coord(coordenador):
    c = APIClient()
    c.force_authenticate(coordenador)
    return c


def _formador(n):
    u = UsuarioFactory(username=f"form_1626u_{n}", cpf=str(next(_CPF)))
    u.groups.add(GroupFactory(name="Formador"))
    return u


def _create_sol(client, municipio, projeto, tipo_evento, extra):
    inicio = timezone.now() + timedelta(days=3)
    resp = client.post(
        "/api/solicitacoes/",
        {
            "municipio": municipio.id,
            "projeto": projeto.id,
            "tipo_evento": tipo_evento.id,
            "tipo": "PRESENCIAL",
            "inicio": inicio.isoformat(),
            "fim": (inicio + timedelta(hours=2)).isoformat(),
            "extra_participants": extra,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    return resp.json()["id"]


def _ids(sol_id, role):
    return set(
        Participation.objects.filter(solicitacao_id=sol_id, role=role, usuario_id__isnull=False).values_list(
            "usuario_id", flat=True
        )
    )


class TestUpdateMalformedShape:
    def test_formador_ids_string_returns_400_not_500(self, client_coord, municipio, projeto, tipo_evento):
        """RED: `{"formador_ids": "abc"}` no PATCH itera a string → id__in inválido → 500."""
        f_a = _formador("s1")
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"formador_ids": [f_a.id]})

        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": "abc"}},
            format="json",
        )
        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"
        # O formador válido pré-existente continua (rollback do PATCH inválido).
        assert _ids(sol_id, "FORMADOR") == {f_a.id}

    def test_formador_ids_dict_returns_400_not_500(self, client_coord, municipio, projeto, tipo_evento):
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"formador_ids": []})
        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": {"a": 1}}},
            format="json",
        )
        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"

    def test_formador_ids_non_int_item_returns_400(self, client_coord, municipio, projeto, tipo_evento):
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"formador_ids": []})
        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": ["abc"]}},
            format="json",
        )
        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"

    def test_formador_ids_over_max_returns_400(self, client_coord, municipio, projeto, tipo_evento):
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"formador_ids": []})
        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": list(range(1, 202))}},  # 201 > _MAX(200)
            format="json",
        )
        assert resp.status_code == 400, f"esperado 400 (max_length), obteve {resp.status_code}"


class TestUpdateAbsentKeyDoesNotTouchOtherRole:
    def test_patch_only_formador_preserves_coord_acompanha(self, client_coord, municipio, projeto, tipo_evento):
        """A validação NÃO pode transformar 'coord_acompanha ausente' em 'lista vazia = apagar'."""
        f_a = _formador("k1")
        coord_a = _formador("k2")
        f_b = _formador("k3")
        sol_id = _create_sol(
            client_coord,
            municipio,
            projeto,
            tipo_evento,
            {"formador_ids": [f_a.id], "coord_acompanha_ids": [coord_a.id]},
        )
        assert _ids(sol_id, "FORMADOR") == {f_a.id}
        assert _ids(sol_id, "COORD_ACOMPANHA") == {coord_a.id}

        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": [f_b.id]}},  # coord_acompanha_ids AUSENTE
            format="json",
        )
        assert resp.status_code in (200, 202), resp.data
        assert _ids(sol_id, "FORMADOR") == {f_b.id}
        assert _ids(sol_id, "COORD_ACOMPANHA") == {coord_a.id}, "campo ausente não pode apagar o outro papel"

    def test_patch_valid_formador_ids_still_works(self, client_coord, municipio, projeto, tipo_evento):
        """Não-regressão: shape válido segue reconciliando FORMADOR por id."""
        f_a = _formador("v1")
        f_b = _formador("v2")
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"formador_ids": [f_a.id]})
        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": [f_b.id]}},
            format="json",
        )
        assert resp.status_code in (200, 202), resp.data
        assert _ids(sol_id, "FORMADOR") == {f_b.id}
