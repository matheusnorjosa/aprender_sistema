"""
PR B1 (anti-escalada c) — `_apply_lotacao` audita a concessão e a revogação do poder
de aprovar solicitações.

Com o B1, lotar alguém como GERENTE na SUPERINTENDENCIA pelo formulário de usuário
(superuser-only) dá poder de aprovar. A troca de grupos já era auditada
(`ASSIGN_GROUPS`), mas o vínculo não — e é ele que passa a conceder a autoridade.
O AuditLog registra `details.autoridade_aprovacao = "concedida" | "revogada"`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportUnusedFunction=false

from __future__ import annotations

from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Gerencia, Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def root() -> Usuario:
    return UsuarioFactory(superuser=True)


@pytest.fixture
def g1() -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    return gerencia


@pytest.fixture
def g_vidas() -> Gerencia:
    return Gerencia.objects.create(nome="GERENCIA VIDAS B1", nome_setor="Vidas")


def _lotar(root: Usuario, alvo: Usuario, gerencia: Gerencia, captura) -> None:
    client = APIClient()
    client.force_authenticate(user=root)
    with captura(execute=True):
        resp = client.patch(
            f"/api/usuarios-admin/{alvo.id}/",
            {"group_ids": [GroupFactory(name="Gerente").id], "gerencia_id": gerencia.id},
            format="json",
        )
    assert resp.status_code == 200, resp.content


def _logs_autoridade(alvo: Usuario) -> list[AuditLog]:
    return list(
        AuditLog.objects.filter(
            model_name="Usuario",
            details__target_user_id=alvo.id,
            details__has_key="autoridade_aprovacao",
        ).order_by("id")
    )


def test_lotar_como_gerente_em_g1_audita_concessao(root, g1, django_capture_on_commit_callbacks):
    alvo = UsuarioFactory()

    _lotar(root, alvo, g1, django_capture_on_commit_callbacks)

    (log,) = _logs_autoridade(alvo)
    assert log.usuario_id == root.id
    assert log.action == AuditLog.Action.USER_PRIVILEGE_CHANGED
    assert log.details["autoridade_aprovacao"] == "concedida"


def test_tirar_de_g1_audita_revogacao(root, g1, g_vidas, django_capture_on_commit_callbacks):
    alvo = UsuarioFactory()
    _lotar(root, alvo, g1, django_capture_on_commit_callbacks)

    _lotar(root, alvo, g_vidas, django_capture_on_commit_callbacks)

    concessao, revogacao = _logs_autoridade(alvo)
    assert concessao.details["autoridade_aprovacao"] == "concedida"
    assert revogacao.details["autoridade_aprovacao"] == "revogada"


def test_lotacao_sem_efeito_na_autoridade_nao_audita(root, g_vidas, django_capture_on_commit_callbacks):
    alvo = UsuarioFactory()

    _lotar(root, alvo, g_vidas, django_capture_on_commit_callbacks)

    assert _logs_autoridade(alvo) == []
