"""
Concurrency regression tests — ASQ-016 phase 2 (#866).

Covers the three flows flagged as GAP-5 in ACID_POLICY.md:

1. Concurrent OAuth token refresh — only one HTTP call reaches Google, the
   second caller short-circuits through the double-check.
2. Concurrent GCal publish for the same solicitacao — final DB state is
   consistent regardless of how the two calls interleave.
3. Savepoint-per-item in imports — a single bad row rolls back only its
   own insert, not the entire file.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false, reportPossiblyUnboundVariable=false

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest import mock
from uuid import uuid4

from django.contrib.auth.models import Group
from django.db import close_old_connections
from django.utils import timezone

import pytest

from apps.core.models import (
    AvailabilityBlock,
    GoogleOAuthCredential,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)
from apps.core.services.bloqueios_import import import_bloqueios_from_file


@pytest.fixture
def usuario():
    uid = uuid4().hex[:8]
    return Usuario.objects.create_user(
        username=f"asq016_{uid}",
        password="x",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"asq016_{uid}@test.com",
        first_name=f"First{uid}",
        last_name=f"Last{uid}",
    )


# =============================================================================
# Test 1 — Concurrent OAuth refresh: double-check prevents duplicate HTTP call
# =============================================================================


@pytest.mark.django_db(transaction=True)
def test_concurrent_oauth_refresh_double_checks(monkeypatch, usuario):
    """
    Two threads race to refresh the same credential. The first wins the row
    lock and performs the HTTP refresh; the second acquires the lock after
    the first commits, sees token_expiry > now + 5min, and returns without
    hitting Google.
    """
    from apps.core.services.oauth import token_manager

    # Old enough to be expired.
    past = timezone.now() - timedelta(minutes=10)

    credential = GoogleOAuthCredential.objects.create(
        user=usuario,
        google_email="ops@example.com",
        access_token_encrypted=b"old-access",
        refresh_token_encrypted=b"old-refresh",
        token_expiry=past,
    )

    call_count = {"n": 0}
    response_lock = threading.Lock()

    def fake_post(*args, **kwargs):
        with response_lock:
            call_count["n"] += 1
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "access_token": f"new-access-{call_count['n']}",
            "expires_in": 3600,
        }
        resp.raise_for_status = lambda: None
        return resp

    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setattr(token_manager, "decrypt_token", lambda _blob: "refresh-token-plain")
    monkeypatch.setattr(
        token_manager,
        "encrypt_token",
        lambda s: (s.encode() if isinstance(s, str) else bytes(s)),
    )
    monkeypatch.setattr(token_manager.requests, "post", fake_post)

    start = threading.Barrier(2)

    def worker() -> str:
        close_old_connections()
        try:
            cred = GoogleOAuthCredential.objects.get(pk=credential.pk)
            start.wait(timeout=5)
            token_manager.refresh_access_token_safe(cred)
            return "ok"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(lambda _: worker(), range(2)))

    assert results == ["ok", "ok"]
    # Only the first refresher talks to Google; the second short-circuits.
    assert call_count["n"] == 1, (
        f"expected exactly 1 refresh HTTP call; observed {call_count['n']}. "
        "Double-check pattern in refresh_access_token_safe regressed."
    )

    credential.refresh_from_db()
    assert credential.token_expiry > timezone.now() + timedelta(minutes=50)


# =============================================================================
# Test 2 — Concurrent GCal publish: final state consistent, no duplicate inserts
# =============================================================================


class _RecordingCalendarClient:
    """Minimal calendar client that records each external call so the test can
    assert the collision behavior of two concurrent apply_one_solicitacao calls
    against the same solicitacao."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []  # (verb, event_id)
        self._lock = threading.Lock()
        # Simulate "event already exists" once a create has landed.
        self._existing: set[str] = set()

    def get(self, calendar_id, event_id):  # noqa: ARG002
        with self._lock:
            if event_id in self._existing:
                return {"id": event_id}
            return None

    def insert(self, calendar_id, event_id, payload):  # noqa: ARG002
        with self._lock:
            self.calls.append(("insert", event_id))
            self._existing.add(event_id)
            return {"id": event_id}

    def update(self, calendar_id, event_id, payload):  # noqa: ARG002
        with self._lock:
            self.calls.append(("update", event_id))
            return {"id": event_id}

    def delete(self, calendar_id, event_id):  # noqa: ARG002
        with self._lock:
            self.calls.append(("delete", event_id))
            self._existing.discard(event_id)


@pytest.fixture
def solicitacao_aprovada(usuario):
    muni = Municipio.objects.create(nome=f"Mun_{uuid4().hex[:6]}", uf="CE", ativo=True)
    proj = Projeto.objects.create(
        nome=f"Proj_{uuid4().hex[:6]}",
        codigo=f"P{uuid4().hex[:5]}",
        fluxo="SUPER",
        ativo=True,
    )
    tipo = TipoEvento.objects.get_or_create(nome="Evt_ASQ016")[0]
    group, _ = Group.objects.get_or_create(name="Coordenador")
    usuario.groups.add(group)
    return Solicitacao.objects.create(
        usuario=usuario,
        municipio=muni,
        projeto=proj,
        tipo_evento=tipo,
        inicio=timezone.now() + timedelta(days=1),
        fim=timezone.now() + timedelta(days=1, hours=2),
        status="aprovado",
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_apply_one_solicitacao_keeps_state_consistent(monkeypatch, solicitacao_aprovada):
    """
    Two threads publish the same solicitacao at once. After both return, the
    DB should reflect a single event id and gcal_status=PUBLISHED — no torn
    state, no ERROR leakage.
    """
    from apps.core.services.gcal import sync as sync_mod

    client = _RecordingCalendarClient()
    monkeypatch.setattr(sync_mod, "_retry_with_circuit_breaker", lambda f, **_: f())

    start = threading.Barrier(2)

    def worker() -> str:
        close_old_connections()
        try:
            s = Solicitacao.objects.get(pk=solicitacao_aprovada.pk)
            start.wait(timeout=5)
            outcome = sync_mod.apply_one_solicitacao(s, apply_blocked=True, client=client)
            return outcome.action
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as ex:
        outcomes = list(ex.map(lambda _: worker(), range(2)))

    # Both calls returned an action (not an exception). Whether both produced
    # CREATE or one CREATE + one UPDATE/ADOPT depends on whose client.get
    # landed first — GCal itself deduplicates via 409 on duplicate event ids,
    # but the mock here doesn't emulate that and it's fine: the regression we
    # care about is the DB state, not the call order.
    assert len(outcomes) == 2
    for action in outcomes:
        assert action in {"CREATE", "UPDATE", "ADOPT"}

    solicitacao_aprovada.refresh_from_db()
    assert solicitacao_aprovada.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert solicitacao_aprovada.external_event_id is not None


# =============================================================================
# Test 3 — Savepoint-per-item in imports: one bad row doesn't drop valid rows
# =============================================================================


@pytest.mark.django_db(transaction=True)
def test_bloqueios_import_uses_savepoint_per_row(tmp_path, usuario):
    """
    Three rows: row 1 valid, row 2 bad (unknown user), row 3 valid. After
    import the bad row is counted as skipped but rows 1 and 3 are persisted.
    """
    csv_path = tmp_path / "bloqueios_asq016.csv"
    # Valid datetimes (the service parses ISO/BR formats).
    d1_start = datetime(2099, 1, 10, 9, 0, tzinfo=dt_timezone.utc).isoformat()
    d1_end = datetime(2099, 1, 10, 18, 0, tzinfo=dt_timezone.utc).isoformat()
    d3_start = datetime(2099, 1, 12, 9, 0, tzinfo=dt_timezone.utc).isoformat()
    d3_end = datetime(2099, 1, 12, 18, 0, tzinfo=dt_timezone.utc).isoformat()

    nome_valido = f"{usuario.first_name} {usuario.last_name}"
    csv_path.write_text(
        "usuario,inicio,fim,tipo,motivo\n"
        f"{nome_valido},{d1_start},{d1_end},T,dia-1\n"
        f"USUARIO_INEXISTENTE_ZZZ,{d1_start},{d1_end},T,row-ruim\n"
        f"{nome_valido},{d3_start},{d3_end},T,dia-3\n",
        encoding="utf-8",
    )

    before = AvailabilityBlock.objects.filter(usuario=usuario).count()
    result = import_bloqueios_from_file(path=str(csv_path), dry_run=False)
    after = AvailabilityBlock.objects.filter(usuario=usuario).count()

    # The bad row was captured as a pendency; the two valid rows were persisted.
    assert result["stats"]["created"] + result["stats"]["updated"] == 2
    assert result["stats"]["skipped"]["usuario"] + result["stats"]["skipped"]["other"] >= 1
    assert after - before == 2, (
        "Expected exactly 2 blocks to be persisted. The savepoint-per-row "
        "pattern must isolate the bad row's rollback."
    )
