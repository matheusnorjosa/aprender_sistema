"""
Regression tests — Deslocamento IDOR + write-side authorization (#1454).

Contexto
--------
O `DeslocamentoViewSet` regrediu no PR #1250 (`git log -L`): a permissão saiu de
`HasPerm("operate_preagenda")` para `[IsAuthenticated]` puro. O `get_queryset`
passou a escopar a LEITURA por `EquipeGerencia`, mas a ESCRITA ficou sem trava:
`perform_create`/`perform_update` faziam `serializer.save()` sem forçar `usuario`,
e o campo `usuario` era gravável no serializer.

Efeito: qualquer usuário autenticado podia criar/editar deslocamento em nome de
terceiro (IDOR).

Regra de negócio (stakeholder, 2026-07-09)
------------------------------------------
Cada pessoa registra a PRÓPRIA viagem (norma). Às vezes o Controle é solicitado a
registrar a viagem de outro (delegação). Modelo híbrido, espelhando o PR #1318
(`AvailabilityBlock`):

- Sem `usuario` (ou == request.user): self-service → `usuario = request.user`.
- Com `usuario != request.user`: exige capability de delegação
  (`user_can_delegate_deslocamento` — `operate_preagenda | view_all_availability`).
  Sem a capability → 403 (IDOR bloqueado). Com a capability → grava para o alvo +
  AuditLog com flag `delegated`.

Estes testes travam a regra e falham se o IDOR reabrir.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportIndexIssue=false, reportMissingTypeArgument=false

from __future__ import annotations

from datetime import date, timedelta

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Deslocamento, EquipeGerencia, Gerencia
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


_CPF_COUNTER = {"i": 0}


def _next_cpf() -> str:
    _CPF_COUNTER["i"] += 1
    return f"77766{_CPF_COUNTER['i']:06d}"


def _make_user(username: str, group_names: list[str]):
    user = UsuarioFactory(username=username, email=f"{username}@example.com", password="testpass123", cpf=_next_cpf())
    for gname in group_names:
        user.groups.add(GroupFactory(name=gname))
    return user


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    """Invalida cache de RBAC entre testes (grupos semeados via conftest session)."""
    cache.clear()
    yield
    cache.clear()


def _payload(**overrides) -> dict:
    base = {
        "origem": "Fortaleza",
        "destino": "Sobral",
        "start_date": "2025-03-10",
        "end_date": "2025-03-12",
        "observacao": "Viagem de formação",
    }
    base.update(overrides)
    return base


class TestDeslocamentoSelfService:
    """Self-service: cada um registra a própria viagem."""

    def test_create_without_usuario_forces_request_user(self):
        """POST sem `usuario` → grava para o próprio request.user."""
        coord = _make_user("coord_self", ["Coordenador"])
        client = APIClient()
        client.force_authenticate(user=coord)

        response = client.post("/api/deslocamentos/", _payload(), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["usuario"] == coord.id
        assert Deslocamento.objects.get(id=response.data["id"]).usuario_id == coord.id

    def test_create_with_own_usuario_is_allowed(self):
        """POST com `usuario` == self é self-service (não delegação)."""
        coord = _make_user("coord_ownid", ["Coordenador"])
        client = APIClient()
        client.force_authenticate(user=coord)

        response = client.post("/api/deslocamentos/", _payload(usuario=coord.id), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["usuario"] == coord.id


class TestDeslocamentoIdorBlocked:
    """IDOR: quem não pode delegar não grava em nome de terceiro."""

    def test_coordenador_cannot_create_for_other_user(self):
        """
        REGRESSÃO #1454: Coord (sem capability de delegação) tentando criar
        deslocamento para outro usuário → 403. Antes do fix retornava 201 (IDOR).
        """
        coord = _make_user("coord_attacker", ["Coordenador"])
        victim = _make_user("victim_formador", ["Formador"])
        client = APIClient()
        client.force_authenticate(user=coord)

        response = client.post("/api/deslocamentos/", _payload(usuario=victim.id), format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Deslocamento.objects.filter(usuario=victim).exists()

    def test_formador_cannot_create_for_other_user(self):
        """Formador puro também não delega."""
        formador = _make_user("formador_attacker", ["Formador"])
        victim = _make_user("victim2", ["Formador"])
        client = APIClient()
        client.force_authenticate(user=formador)

        response = client.post("/api/deslocamentos/", _payload(usuario=victim.id), format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Deslocamento.objects.filter(usuario=victim).exists()

    def test_update_cannot_reassign_usuario_to_third_party(self):
        """
        REGRESSÃO #1454 (update): dono não-delegador não pode reatribuir o
        `usuario` de um deslocamento para terceiro via PATCH.
        """
        coord = _make_user("coord_owner", ["Coordenador"])
        victim = _make_user("victim3", ["Formador"])
        desloc = Deslocamento.objects.create(
            usuario=coord,
            origem="Fortaleza",
            destino="Sobral",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        client = APIClient()
        client.force_authenticate(user=coord)

        response = client.patch(f"/api/deslocamentos/{desloc.id}/", {"usuario": victim.id}, format="json")

        desloc.refresh_from_db()
        # Ou 403, ou o campo é ignorado — mas NUNCA reatribui para a vítima.
        assert desloc.usuario_id == coord.id
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN)


class TestDeslocamentoDelegation:
    """Delegação: Controle registra a viagem de outro, com auditoria."""

    def test_controle_can_create_for_other_user(self):
        """Controle (operate_preagenda + view_all_availability via seed) delega."""
        controle = _make_user("controle_deleg", ["Controle"])
        formador = _make_user("formador_target", ["Formador"])
        client = APIClient()
        client.force_authenticate(user=controle)

        response = client.post("/api/deslocamentos/", _payload(usuario=formador.id), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["usuario"] == formador.id
        assert Deslocamento.objects.get(id=response.data["id"]).usuario_id == formador.id

    def test_delegated_create_writes_auditlog_flag(self):
        """Delegação registra AuditLog CREATE_DESLOCAMENTO com flag `delegated`."""
        controle = _make_user("controle_audit", ["Controle"])
        formador = _make_user("formador_audit", ["Formador"])
        client = APIClient()
        client.force_authenticate(user=controle)

        response = client.post("/api/deslocamentos/", _payload(usuario=formador.id), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        audit = AuditLog.objects.filter(
            action="CREATE_DESLOCAMENTO", details__deslocamento_id=response.data["id"]
        ).first()
        assert audit is not None
        assert audit.usuario_id == controle.id
        assert audit.details.get("delegated") is True


def _in_gerencia(user, gerencia):
    EquipeGerencia.objects.create(usuario=user, gerencia=gerencia)
    return user


def _own_deslocamento(user):
    return Deslocamento.objects.create(
        usuario=user,
        origem="Fortaleza",
        destino="Sobral",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
    )


class TestDeslocamentoWriteOwnerForced:
    """#1454 (residual do audit 2026-07-10): a ESCRITA é owner-forced mesmo dentro
    do escopo de LEITURA.

    Um Coordenador com vínculo EquipeGerencia VÊ os deslocamentos dos colegas da
    gerência (leitura escopada, intencional — RD/mapa). Mas NÃO pode editá-los nem
    removê-los: só o próprio dono ou quem tem delegação
    (`user_can_delegate_deslocamento`). Sem o gate objeto-nível, `get_queryset`
    entregava o registro do colega e `perform_update`/`perform_destroy` o alteravam
    (200/204) sem 403 — mesma família do IDOR do CREATE, mas na mutação/remoção.
    """

    def _colleague_setup(self, coord_name="coord_scoped", victim_name="victim_scoped"):
        gerencia = Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
        coord = _in_gerencia(_make_user(coord_name, ["Coordenador"]), gerencia)
        victim = _in_gerencia(_make_user(victim_name, ["Formador"]), gerencia)
        return coord, victim, _own_deslocamento(victim)

    def test_scoped_coord_sees_but_cannot_delete_colleague(self):
        """Leitura escopada ENXERGA o registro do colega (200), mas o DELETE é 403."""
        coord, _victim, desloc = self._colleague_setup()
        client = APIClient()
        client.force_authenticate(user=coord)

        # sanity: o escopo de leitura de fato entrega o registro do colega
        assert client.get(f"/api/deslocamentos/{desloc.id}/").status_code == status.HTTP_200_OK

        response = client.delete(f"/api/deslocamentos/{desloc.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Deslocamento.objects.filter(id=desloc.id).exists()

    def test_scoped_coord_cannot_edit_colleague(self):
        """PATCH em campo comum (sem reatribuir usuário) de registro do colega → 403."""
        coord, _victim, desloc = self._colleague_setup("coord_edit", "victim_edit")
        client = APIClient()
        client.force_authenticate(user=coord)

        response = client.patch(f"/api/deslocamentos/{desloc.id}/", {"origem": "Juazeiro"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        desloc.refresh_from_db()
        assert desloc.origem == "Fortaleza"

    def test_owner_can_delete_own(self):
        coord = _make_user("owner_del", ["Coordenador"])
        desloc = _own_deslocamento(coord)
        client = APIClient()
        client.force_authenticate(user=coord)

        assert client.delete(f"/api/deslocamentos/{desloc.id}/").status_code == status.HTTP_204_NO_CONTENT
        assert not Deslocamento.objects.filter(id=desloc.id).exists()

    def test_owner_can_edit_own(self):
        coord = _make_user("owner_edit", ["Coordenador"])
        desloc = _own_deslocamento(coord)
        client = APIClient()
        client.force_authenticate(user=coord)

        response = client.patch(f"/api/deslocamentos/{desloc.id}/", {"origem": "Juazeiro"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        desloc.refresh_from_db()
        assert desloc.origem == "Juazeiro"

    def test_delegate_can_delete_colleague(self):
        """Controle (operate_preagenda | view_all_availability) remove viagem de outro."""
        gerencia = Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
        controle = _make_user("controle_del", ["Controle"])
        victim = _in_gerencia(_make_user("victim_deleg", ["Formador"]), gerencia)
        desloc = _own_deslocamento(victim)
        client = APIClient()
        client.force_authenticate(user=controle)

        response = client.delete(f"/api/deslocamentos/{desloc.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Deslocamento.objects.filter(id=desloc.id).exists()
