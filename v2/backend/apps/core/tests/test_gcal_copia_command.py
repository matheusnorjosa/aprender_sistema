"""Comando `gcal_copia` (PR-B): dry-run por padrão, `--apply`, `--operador` e saída sem dado pessoal."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false, reportArgumentType=false

from __future__ import annotations

import hashlib
from datetime import timedelta
from datetime import timezone as dt_timezone
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

import pytest

from apps.core.management.commands import gcal_copia as comando
from apps.core.models import AuditLog, GCalCopiaCursor, Solicitacao
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

PINO = "agenda-org@group.calendar.google.com"
FORTALEZA = dt_timezone(timedelta(hours=-3))
TITULO_SECRETO = "Formação com Fulana Secreta"
EMAIL_SECRETO = "fulana.secreta@example.com"


@pytest.fixture(autouse=True)
def _pino(settings):
    settings.GCAL_OAUTH_CALENDAR_ID = PINO


@pytest.fixture
def fake(monkeypatch) -> FakeCalendarClient:
    cliente = FakeCalendarClient()
    monkeypatch.setattr(comando, "get_oauth_client_for_user", lambda user: (cliente, "primary"))
    return cliente


@pytest.fixture
def movida(fake) -> Solicitacao:
    """Evento aprovado e publicado cujo horário mudou no Google."""
    autor = UsuarioFactory(first_name="Fulana", last_name="Secreta", email=EMAIL_SECRETO)
    inicio = (timezone.now() + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
    s = SolicitacaoFactory(
        usuario=autor,
        status="aprovado",
        gcal_status="PUBLISHED",
        external_event_id="evt1",
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
    )
    novo = inicio + timedelta(days=1)
    fake.insert(
        PINO,
        "evt1",
        {
            "summary": TITULO_SECRETO,
            "attendees": [{"email": EMAIL_SECRETO}],
            "start": {"dateTime": novo.astimezone(FORTALEZA).isoformat()},
            "end": {"dateTime": (novo + timedelta(hours=1)).astimezone(FORTALEZA).isoformat()},
        },
    )
    return s


def _rodar(*args: str) -> str:
    out = StringIO()
    call_command("gcal_copia", *args, stdout=out)
    return out.getvalue()


def test_dry_run_nao_grava_solicitacao_auditlog_nem_cursor(movida):
    operador = UsuarioFactory()
    inicio = movida.inicio

    saida = _rodar("--operador", str(operador.pk))

    assert "dry-run" in saida and f"copiar_horario: 1 [s{movida.pk}]" in saida
    assert "futuro=1" in saida
    assert Solicitacao.objects.get(pk=movida.pk).inicio == inicio
    assert not AuditLog.objects.exists()
    assert not GCalCopiaCursor.objects.exists()


def test_saida_sem_dado_pessoal(movida):
    saida = _rodar("--operador", str(UsuarioFactory(email="operadora@example.com").pk))

    for segredo in ("Fulana", "Secreta", EMAIL_SECRETO, "operadora@example.com", TITULO_SECRETO):
        assert segredo not in saida


def test_apply_cria_o_cursor_desligado_em_observar_e_nao_mexe_no_evento(movida):
    operador = UsuarioFactory()

    saida = _rodar("--apply", "--operador", str(operador.pk))

    cursor = GCalCopiaCursor.objects.get(calendar_id=PINO)
    assert (cursor.ativo, cursor.modo, cursor.operador_id) == (False, "observar", operador.pk)
    assert cursor.sync_token and cursor.resumo["ids"]["copiar_horario"] == [f"s{movida.pk}"]
    assert "modo=observar apply" in saida
    assert Solicitacao.objects.get(pk=movida.pk).inicio == movida.inicio


def test_apply_em_copiar_usa_o_operador_do_cursor(movida, monkeypatch):
    from apps.core import tasks

    monkeypatch.setattr(tasks.task_gcal_copia_descricao, "delay", lambda *a: None)
    operador = UsuarioFactory()
    GCalCopiaCursor.objects.create(calendar_id=PINO, modo="copiar", operador=operador)

    _rodar("--apply")

    assert Solicitacao.objects.get(pk=movida.pk).inicio == movida.inicio + timedelta(days=1)


def test_sem_operador_e_erro(fake):
    with pytest.raises(CommandError, match="operador"):
        _rodar()


def test_pino_vazio_ou_primary_e_erro(fake, settings):
    for pino in ("", "primary"):
        settings.GCAL_OAUTH_CALENDAR_ID = pino
        with pytest.raises(CommandError, match="GCAL_OAUTH_CALENDAR_ID"):
            _rodar("--operador", str(UsuarioFactory().pk))


def test_liberar_freio_exige_apply(fake):
    with pytest.raises(CommandError, match="--apply"):
        _rodar("--liberar-freio", "abc123abc123", "--operador", str(UsuarioFactory().pk))


def test_freio_mostra_a_lista_e_o_digest_e_libera_so_com_ele(fake):
    inicio = (timezone.now() + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
    eids = [f"c{i}" for i in range(6)]
    for eid in eids:
        SolicitacaoFactory(
            status="aprovado",
            gcal_status="PUBLISHED",
            external_event_id=eid,
            inicio=inicio,
            fim=inicio + timedelta(hours=2),
        )
        fim = inicio + timedelta(hours=2)
        fake.insert(PINO, eid, {"start": {"dateTime": inicio.isoformat()}, "end": {"dateTime": fim.isoformat()}})
    GCalCopiaCursor.objects.create(calendar_id=PINO, modo="copiar", ativo=True, operador=UsuarioFactory())
    _rodar("--apply")  # linha de base
    for eid in eids:
        fake.delete(PINO, eid)
    digest = hashlib.sha256(" ".join(eids).encode()).hexdigest()[:12]

    previa = _rodar()

    assert f"freio: 6 cancelamentos, digest {digest} [{' '.join(eids)}]" in previa
    assert "freio=sim" in previa
    with pytest.raises(CommandError, match=rf"freio: 6 cancelamentos \({digest}\)"):
        _rodar("--apply")
    with pytest.raises(CommandError, match="freio"):
        _rodar("--apply", "--liberar-freio", "0" * 12)
    assert not AuditLog.objects.filter(action="REJECT").exists()
    assert GCalCopiaCursor.objects.get(calendar_id=PINO).ativo is False

    _rodar("--apply", "--liberar-freio", digest)  # a cópia desligada ainda roda à mão
    assert AuditLog.objects.filter(action="REJECT").count() == 6
