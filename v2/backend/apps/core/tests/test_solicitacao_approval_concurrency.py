"""
Concurrency regression tests for solicitacao approval flows.

Issue #744: prevent double-approval races with transaction + select_for_update.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.contrib.auth.models import Group
from django.db import close_old_connections
from django.utils import timezone

import pytest

from apps.core.exceptions import ValidationAPIError
from apps.core.models import AuditLog, Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.services.solicitacao_approval import approve_solicitacao, batch_approve_solicitacoes


@pytest.fixture
def grupos():
    return {
        "Superintendência": Group.objects.get_or_create(name="Superintendência")[0],
        "Gerente": Group.objects.get_or_create(name="Gerente")[0],
        "Coordenador": Group.objects.get_or_create(name="Coordenador")[0],
    }


@pytest.fixture
def usuario_superintendencia(grupos):
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"super_conc_{uid}",
        password="senha123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"super_conc_{uid}@test.com",
    )
    user.groups.add(grupos["Superintendência"])
    user.groups.add(grupos["Gerente"])
    return user


@pytest.fixture
def usuario_coordenador(grupos):
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"coord_conc_{uid}",
        password="senha123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"coord_conc_{uid}@test.com",
    )
    user.groups.add(grupos["Coordenador"])
    return user


@pytest.fixture
def municipio():
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def projeto_super():
    uid = uuid4().hex[:8]
    return Projeto.objects.create(
        nome=f"Projeto Concorrencia {uid}",
        codigo=f"PC{uid[:5]}",
        fluxo="SUPER",
        ativo=True,
    )


@pytest.fixture
def tipo_evento():
    return TipoEvento.objects.get_or_create(nome="Formacao Concorrencia")[0]


@pytest.mark.django_db(transaction=True)
def test_approve_solicitacao_allows_single_winner_under_concurrency(
    usuario_superintendencia,
    usuario_coordenador,
    municipio,
    projeto_super,
    tipo_evento,
):
    """
    Two concurrent approvals on the same solicitacao must produce only one success.

    Regression target:
    - exactly 1 approval wins
    - exactly 1 AuditLog APPROVE is created for the solicitacao
    """
    solicitacao = Solicitacao.objects.create(
        usuario=usuario_coordenador,
        municipio=municipio,
        projeto=projeto_super,
        tipo_evento=tipo_evento,
        inicio=timezone.now() + timedelta(days=1),
        fim=timezone.now() + timedelta(days=1, hours=2),
        status="pendente",
    )
    AuditLog.objects.all().delete()

    start_barrier = threading.Barrier(2)

    def worker() -> str:
        close_old_connections()
        try:
            # Preload object before barrier to simulate stale snapshots in concurrent requests.
            sol = Solicitacao.objects.get(pk=solicitacao.id)
            user = Usuario.objects.get(pk=usuario_superintendencia.id)
            req = SimpleNamespace(META={"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "pytest"})
            start_barrier.wait(timeout=5)
            approve_solicitacao(
                solicitacao=sol,
                user=user,
                request=req,
                justificativa="concorrencia",
            )
            return "approved"
        except ValidationAPIError:
            return "blocked"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: worker(), range(2)))

    assert results.count("approved") == 1
    assert results.count("blocked") == 1

    solicitacao.refresh_from_db()
    assert solicitacao.status == "aprovado"

    assert AuditLog.objects.filter(action="APPROVE", details__solicitacao_id=solicitacao.id).count() == 1


@pytest.mark.django_db(transaction=True)
def test_batch_approve_solicitacoes_blocks_double_approval_race(
    monkeypatch,
    usuario_superintendencia,
    usuario_coordenador,
    municipio,
    projeto_super,
    tipo_evento,
):
    """
    Two concurrent batch approvals over the same ID must not double-approve.

    Regression target:
    - only one batch call approves
    - second call returns the item as already processed
    - only one APPROVE AuditLog is persisted
    """
    solicitacao = Solicitacao.objects.create(
        usuario=usuario_coordenador,
        municipio=municipio,
        projeto=projeto_super,
        tipo_evento=tipo_evento,
        inicio=timezone.now() + timedelta(days=2),
        fim=timezone.now() + timedelta(days=2, hours=2),
        status="pendente",
    )
    AuditLog.objects.all().delete()

    start_barrier = threading.Barrier(2)
    original_save = Solicitacao.save

    def delayed_save(self, *args, **kwargs):
        if self.pk == solicitacao.id and self.status == "aprovado":
            # Widen overlap window between concurrent callers.
            time.sleep(0.15)
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(Solicitacao, "save", delayed_save)

    def worker() -> tuple[int, int]:
        close_old_connections()
        try:
            user = Usuario.objects.get(pk=usuario_superintendencia.id)
            req = SimpleNamespace(META={"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "pytest"})
            start_barrier.wait(timeout=5)
            result = batch_approve_solicitacoes(
                ids=[solicitacao.id],
                user=user,
                request=req,
            )
            return result.approved_count, len(result.errors)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: worker(), range(2)))

    approved_counts = sorted([approved for approved, _ in outcomes], reverse=True)
    assert approved_counts == [1, 0]

    solicitacao.refresh_from_db()
    assert solicitacao.status == "aprovado"

    assert AuditLog.objects.filter(action="APPROVE", details__solicitacao_id=solicitacao.id).count() == 1
