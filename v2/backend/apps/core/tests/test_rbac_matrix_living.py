"""
RBAC Living Matrix — backend tests parametrizados (Onda 3, 2026-04-27).

Lê `apps.core.rbac.matrix.ACCESS_MATRIX` e valida que cada (ator × recurso)
retorna o status code declarado. Falha CI imediato se código diverge da
matriz canônica — diff do test vira checklist no PR review.

Não cobre scope cases (Coord vs gerência X vs Y) — esses ficam em tests
dedicados (`test_deslocamento_rbac.py`, `test_availability_monthly_rbac.py`).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.rbac.matrix import (
    ACCESS_MATRIX,
    ACTOR_GROUPS,
    ACTORS,
    APOIO,
    ASST_ADMIN_CONTROLE,
    COORDENADOR,
    GERENTE,
    GERENTE_SUPER,
    RESOURCES,
    SUPERUSER,
    ResourceCase,
    expand_matrix,
    format_failure_message,
)
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


_USER_COUNTER = {"i": 0}


def _next_cpf() -> str:
    _USER_COUNTER["i"] += 1
    return f"99988{_USER_COUNTER['i']:06d}"


def _make_user_for_actor(actor: str) -> Usuario:
    """
    Cria user com grupos correspondentes ao ator. Superuser é caso especial.
    Cada test gera CPF/username único via atomic counter.

    D8 (2026-04-28): Coordenador e Apoio de Coordenação ganham EquipeGerencia
    ativa pré-criada. Sem o vínculo, eles cairiam em 403 pelo HasSectorAccess
    endurecido (sem cap global E sem gerência → DENY). Outros atores não
    precisam — Controle passa pela cap; DAT/Diretoria/Formador são DENY/ALLOW
    por design.

    D9 (2026-04-28): Gerente perde cap global e cai em scope via EquipeGerencia
    (igual Coord/Apoio). Fixture cria vínculo papel="GERENTE" para que o ator
    GERENTE retorne 200 na Matriz Viva. DAT recebe cap global (sem fixture).
    """
    if actor == SUPERUSER:
        return UsuarioFactory(
            superuser=True,
            cpf=_next_cpf(),
        )
    user = UsuarioFactory(
        username=f"matrix_{actor.lower().replace(' ', '_')}_{_USER_COUNTER['i']:06d}",
        email=f"matrix_{actor.lower().replace(' ', '_')}_{_USER_COUNTER['i']:06d}@example.com",
        cpf=_next_cpf(),
        groups=ACTOR_GROUPS[actor],
    )

    # D8 + D9 + PR 8: Coord/Apoio/Gerente* precisam de vínculo organizacional
    # para passar HasSectorAccess na grade mensal.
    if actor in (COORDENADOR, APOIO, GERENTE, GERENTE_SUPER):
        # Setor da gerência segue o ator (Vidas para pedagógico, Sup para
        # GERENTE_SUPER) — diferenciação importante para tests de scope.
        nome_setor = "Superintendência" if actor == GERENTE_SUPER else "Vidas"
        gerencia, _ = Gerencia.objects.get_or_create(
            nome=f"GERENCIA MATRIX {_USER_COUNTER['i']:06d}",
            defaults={"nome_setor": nome_setor},
        )
        if actor == COORDENADOR:
            # Coordenador: papel direto, sem supervisor.
            EquipeGerencia.objects.create(
                gerencia=gerencia,
                usuario=user,
                papel="COORDENADOR",
                ativo=True,
            )
        elif actor in (GERENTE, GERENTE_SUPER):
            # Gerente (pedagógico ou Sup): papel direto, sem supervisor.
            EquipeGerencia.objects.create(
                gerencia=gerencia,
                usuario=user,
                papel="GERENTE",
                ativo=True,
            )
        else:
            # Apoio: check constraint `apoio_requires_supervisor` exige
            # `coordenador_supervisor` (FK Usuario) não-nulo. Criamos um Coord
            # auxiliar para servir de supervisor.
            supervisor_user = UsuarioFactory(
                username=f"matrix_supervisor_{_USER_COUNTER['i']:06d}",
                email=f"matrix_supervisor_{_USER_COUNTER['i']:06d}@example.com",
                cpf=_next_cpf(),
            )
            EquipeGerencia.objects.create(
                gerencia=gerencia,
                usuario=supervisor_user,
                papel="COORDENADOR",
                ativo=True,
            )
            EquipeGerencia.objects.create(
                gerencia=gerencia,
                usuario=user,
                papel="APOIO",
                ativo=True,
                coordenador_supervisor=supervisor_user,
            )
    return user


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    """Cache RBAC entre tests (capabilities resolvidas via cache Redis)."""
    cache.clear()
    yield
    cache.clear()


# ============================================================================
# Test parametrizado principal — atores × recursos
# ============================================================================


_MATRIX_CASES = expand_matrix()
_MATRIX_IDS = [f"{actor}::{resource.name}::expected{expected}" for actor, resource, expected in _MATRIX_CASES]


@pytest.mark.parametrize("actor,resource,expected", _MATRIX_CASES, ids=_MATRIX_IDS)
def test_actor_can_or_cannot_access_resource(actor: str, resource: ResourceCase, expected: int):
    """
    Para cada (ator × recurso), valida que o status code bate com ACCESS_MATRIX.

    Falha indica:
    - Mudança não-documentada em permission_classes
    - Drift entre seed e matriz canônica
    - Renomeação de endpoint sem atualizar matriz
    - Capability removida/adicionada sem decisão consciente
    """
    user = _make_user_for_actor(actor)
    client = APIClient()
    client.force_authenticate(user=user)

    if resource.method == "GET":
        res = client.get(resource.full_url())
    elif resource.method == "POST":
        res = client.post(resource.full_url(), data=resource.body or {}, format="json")
    else:
        raise ValueError(f"Method {resource.method} não suportado pela matriz viva")

    body = res.content.decode("utf-8", errors="replace") if res.content else "(empty)"

    assert res.status_code == expected, format_failure_message(
        actor=actor,
        resource=resource,
        expected=expected,
        received=res.status_code,
        response_body=body,
    )


# ============================================================================
# Sanity — anonymous deve sempre ser bloqueado
# ============================================================================


@pytest.mark.parametrize("resource", RESOURCES, ids=lambda r: r.name)
def test_anonymous_is_always_blocked(resource: ResourceCase):
    """
    Anonymous nunca deve acessar nenhum dos recursos da matriz. Catches
    regressões onde alguém remova `IsAuthenticated` por engano.
    """
    client = APIClient()
    if resource.method == "GET":
        res = client.get(resource.full_url())
    else:
        res = client.post(resource.full_url(), data={}, format="json")
    assert res.status_code in (401, 403), (
        f"Anonymous deveria ser bloqueado em {resource.name} ({resource.method} {resource.url}). "
        f"Got {res.status_code}: pode ser removal acidental de IsAuthenticated."
    )


# ============================================================================
# Sanity — matriz é completa (toda combinação coberta)
# ============================================================================


def test_matrix_covers_all_actor_resource_combinations():
    """
    Garante que ACCESS_MATRIX tem entry para todos os (ator × recurso).
    Falha se alguém adicionar recurso sem atualizar matriz.
    """
    for resource in RESOURCES:
        assert resource.name in ACCESS_MATRIX, (
            f"Recurso '{resource.name}' falta em ACCESS_MATRIX. " f"Adicione em apps/core/rbac/matrix.py."
        )
        for actor in ACTORS:
            assert actor in ACCESS_MATRIX[resource.name], f"Ator '{actor}' falta em ACCESS_MATRIX['{resource.name}']."


def test_matrix_status_codes_are_valid():
    """Toda célula deve ser ALLOW (200), ALLOW_PAYLOAD_INVALID (400) ou DENY (403)."""
    for resource_name, actor_map in ACCESS_MATRIX.items():
        for actor, status in actor_map.items():
            assert status in (200, 400, 403), (
                f"ACCESS_MATRIX['{resource_name}']['{actor}'] = {status} é inválido. "
                "Use 200 (ALLOW), 400 (ALLOW_PAYLOAD_INVALID) ou 403 (DENY)."
            )
