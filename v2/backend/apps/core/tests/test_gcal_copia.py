"""Cópia Google → Sistema (PR-B): `decidir`, `sincronizar`, PATCH da descrição e `trocar_modo`.

Usa o `FakeCalendarClient` fiel ao Google (DELETE soft, horas em -03:00, log de mudanças). A
"edição feita no Google" é um `fake.update` (PATCH: só troca o que vem no payload).

Gotcha (por que handler direto e não caplog): o logger `apps` tem propagate=False, então o
registro não sobe até a raiz onde o caplog escuta (mesmo padrão de test_gcal_insert_log_lgpd.py).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportIndexIssue=false, reportOperatorIssue=false, reportArgumentType=false, reportCallIssue=false, reportPrivateUsage=false

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Any

from django.db import IntegrityError, OperationalError, connection
from django.utils import timezone

import pytest

from apps.core.models import AuditLog, GCalCopiaCursor, Participation, Solicitacao
from apps.core.services.gcal import copia
from apps.core.services.gcal.copia import decidir, sincronizar, trocar_modo
from apps.core.services.gcal.payload import compute_payload_hash
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.tests.factories import ProjetoFactory, SolicitacaoFactory, UsuarioFactory

PINO = "agenda-org@group.calendar.google.com"
FORTALEZA = dt_timezone(timedelta(hours=-3))
NOME_SECRETO = "Fulana Secreta da Silva"
EMAIL_SECRETO = "fulana.secreta@example.com"
TITULO_SECRETO = "Formação com Fulana Secreta"


@pytest.fixture(autouse=True)
def _pino(settings):
    settings.GCAL_OAUTH_CALENDAR_ID = PINO


@pytest.fixture
def agora() -> datetime:
    return timezone.now().replace(microsecond=0)


@pytest.fixture
def fake() -> FakeCalendarClient:
    return FakeCalendarClient()


@pytest.fixture
def enfileirados(monkeypatch) -> list[tuple[int, int]]:
    """Captura o `.delay` da task do PATCH da descrição (nada vai para o broker)."""
    chamadas: list[tuple[int, int]] = []
    from apps.core import tasks

    monkeypatch.setattr(tasks.task_gcal_copia_descricao, "delay", lambda sid, oid: chamadas.append((sid, oid)))
    return chamadas


def _hora(agora: datetime, dias: int, hora: int = 12) -> datetime:
    return (agora + timedelta(days=dias)).replace(hour=hora, minute=0, second=0)


def _publicada(agora: datetime, eid: str = "evt1", dias: int = 3, **kw: Any) -> Solicitacao:
    inicio = kw.pop("inicio", _hora(agora, dias))
    dados: dict[str, Any] = {
        "status": Solicitacao.Status.APROVADO,
        "gcal_status": Solicitacao.GCalStatus.PUBLISHED,
        "external_event_id": eid,
        "inicio": inicio,
        "fim": inicio + timedelta(hours=2),
        **kw,
    }
    return SolicitacaoFactory(**dados)


def _no_google(fake: FakeCalendarClient, s: Solicitacao) -> None:
    """Evento como o sistema publicou: horas em UTC (o fake devolve em -03:00)."""
    fake.insert(
        PINO,
        s.external_event_id,
        {
            "summary": TITULO_SECRETO,
            "description": "📅 Data: antiga",
            "attendees": [{"email": EMAIL_SECRETO}],
            "start": {"dateTime": s.inicio.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": s.fim.isoformat(), "timeZone": "UTC"},
        },
    )


def _mover_no_google(fake: FakeCalendarClient, eid: str, inicio: datetime, fim: datetime) -> None:
    """Alguém muda o horário pela tela do Google (horas em -03:00, fuso da agenda)."""
    fake.update(
        PINO,
        eid,
        {
            "start": {"dateTime": inicio.astimezone(FORTALEZA).isoformat(), "timeZone": "America/Fortaleza"},
            "end": {"dateTime": fim.astimezone(FORTALEZA).isoformat(), "timeZone": "America/Fortaleza"},
        },
    )


def _cursor(**kw: Any) -> GCalCopiaCursor:
    dados: dict[str, Any] = {"calendar_id": PINO, "ativo": True, "modo": "copiar", "operador": UsuarioFactory()}
    dados.update(kw)
    return GCalCopiaCursor.objects.create(**dados)


def _linha_de_base(cursor: GCalCopiaCursor, fake: FakeCalendarClient, agora: datetime) -> None:
    """1ª rodada: leitura completa, tudo eco; deixa o token gravado."""
    r = sincronizar(cursor, fake, escrever=True, agora=agora)
    assert r.status == "OK", r.erro
    cursor.refresh_from_db()
    assert cursor.sync_token


@contextmanager
def _logs() -> Iterator[list[logging.LogRecord]]:
    capturados: list[logging.LogRecord] = []

    class _Cap(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capturados.append(record)

    handler = _Cap(level=logging.DEBUG)
    copia.logger.addHandler(handler)
    nivel = copia.logger.level
    copia.logger.setLevel(logging.DEBUG)
    try:
        yield capturados
    finally:
        copia.logger.removeHandler(handler)
        copia.logger.setLevel(nivel)


# --- decidir (puro, sem banco) ---


def _linha(agora: datetime, **kw: Any) -> Solicitacao:
    inicio = kw.pop("inicio", _hora(agora, 3))
    dados: dict[str, Any] = {
        "status": "aprovado",
        "gcal_status": "PUBLISHED",
        "external_event_id": "evt1",
        "inicio": inicio,
        "fim": inicio + timedelta(hours=2),
        **kw,
    }
    return Solicitacao(**dados)


def _evento(inicio: datetime | None, fim: datetime | None, **kw: Any) -> dict[str, Any]:
    evento: dict[str, Any] = {"id": "evt1", "status": "confirmed"}
    if inicio is not None and fim is not None:
        evento["start"] = {"dateTime": inicio.astimezone(FORTALEZA).isoformat()}
        evento["end"] = {"dateTime": fim.astimezone(FORTALEZA).isoformat()}
    evento.update(kw)
    return evento


def test_decidir_sem_linha_e_sem_vinculo(agora):
    assert decidir(_evento(None, None), [], agora).motivo == "sem_vinculo"


def test_decidir_id_duplicado_vem_antes_do_status(agora):
    linhas = [_linha(agora), _linha(agora, status="pendente", gcal_status="NONE")]
    assert decidir(_evento(None, None), linhas, agora).motivo == "id_duplicado"


@pytest.mark.parametrize(
    ("campos", "motivo"),
    [
        ({"status": "pendente"}, "nao_aprovada"),
        ({"status": "reprovado"}, "nao_aprovada"),
        ({"gcal_status": "ERROR"}, "erro_gcal"),
        ({"gcal_status": "PENDING"}, "pendente_gcal"),
        ({"gcal_status": "NONE"}, "nao_publicada"),
    ],
)
def test_decidir_so_aprovada_e_publicada_entra(agora, campos, motivo):
    s = _linha(agora, **campos)
    novo = _hora(agora, 4)
    assert decidir(_evento(novo, novo + timedelta(hours=1)), [s], agora).motivo == motivo


def test_decidir_recorrente(agora):
    s = _linha(agora)
    novo = _hora(agora, 4)
    assert decidir(_evento(novo, novo + timedelta(hours=1), recurringEventId="r1"), [s], agora).motivo == "recorrente"
    assert decidir(_evento(novo, novo + timedelta(hours=1), recurrence=["RRULE:x"]), [s], agora).motivo == "recorrente"


def test_decidir_dia_inteiro(agora):
    s = _linha(agora)
    evento = {"id": "evt1", "status": "confirmed", "start": {"date": "2026-12-01"}, "end": {"date": "2026-12-02"}}
    assert decidir(evento, [s], agora).motivo == "dia_inteiro"


def test_decidir_cancelado_futuro_e_passado(agora):
    lapide = {"id": "evt1", "status": "cancelled"}
    assert decidir(lapide, [_linha(agora)], agora).motivo == "cancelado"
    assert decidir(lapide, [_linha(agora, inicio=agora - timedelta(hours=1))], agora).motivo == "passado"


def test_decidir_fim_antes_do_inicio(agora):
    novo = _hora(agora, 4)
    assert decidir(_evento(novo, novo), [_linha(agora)], agora).motivo == "fim_antes_inicio"


def test_decidir_eco_compara_instantes_nao_texto(agora):
    s = _linha(agora)
    evento_z = {
        "id": "evt1",
        "start": {"dateTime": s.inicio.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")},
        "end": {"dateTime": s.fim.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")},
    }
    assert decidir(evento_z, [s], agora).motivo == "eco"
    assert decidir(_evento(s.inicio, s.fim), [s], agora).motivo == "eco", "-03:00 e Z são o mesmo instante"


def test_decidir_passado_e_em_andamento_ficam_de_fora(agora):
    novo = _hora(agora, 4)
    passado = _linha(agora, inicio=agora - timedelta(days=1))
    em_andamento = _linha(agora, inicio=agora - timedelta(minutes=30))
    assert decidir(_evento(novo, novo + timedelta(hours=1)), [passado], agora).motivo == "passado"
    assert decidir(_evento(novo, novo + timedelta(hours=1)), [em_andamento], agora).motivo == "passado"


def test_decidir_futuro_movido_para_o_passado(agora):
    ontem = agora - timedelta(days=1)
    assert decidir(_evento(ontem, ontem + timedelta(hours=1)), [_linha(agora)], agora).motivo == "movido_para_passado"


def test_decidir_copiar_horario_em_utc(agora):
    novo = _hora(agora, 5, hora=9)
    d = decidir(_evento(novo, novo + timedelta(hours=3)), [_linha(agora)], agora)
    assert d.motivo == "copiar_horario"
    assert d.inicio == novo and d.inicio.utcoffset() == timedelta(0)
    assert d.fim == novo + timedelta(hours=3)


# --- sincronizar: cópia de horário ---


@pytest.mark.django_db
def test_eco_nao_grava_nada_e_mantem_updated_at(agora, fake, enfileirados, django_capture_on_commit_callbacks):
    s = _publicada(agora)
    _no_google(fake, s)
    antes = Solicitacao.objects.get(pk=s.pk).updated_at
    cursor = _cursor()

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "OK"
    assert r.resumo["contagens"] == {"eco": 1}
    assert Solicitacao.objects.get(pk=s.pk).updated_at == antes
    assert not AuditLog.objects.filter(action="GCAL_COPIA_GOOGLE").exists()
    assert callbacks == [] and enfileirados == []


@pytest.mark.django_db
def test_copia_horario_grava_utc_auditlog_e_enfileira_descricao(
    agora, fake, enfileirados, django_capture_on_commit_callbacks
):
    s = _publicada(agora)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6, hora=8)
    _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=4))

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "OK" and r.resumo["contagens"] == {"copiar_horario": 1}
    assert r.resumo["ids"]["copiar_horario"] == [f"s{s.pk}"]
    s.refresh_from_db()
    assert s.inicio == novo and s.fim == novo + timedelta(hours=4)
    assert s.status == "aprovado" and s.gcal_status == "PUBLISHED"
    log = AuditLog.objects.get(action="GCAL_COPIA_GOOGLE")
    assert log.usuario is None
    assert log.details["solicitacao_id"] == s.pk and log.details["campo"] == "horario"
    assert log.details["depois"] == {"inicio": novo.isoformat(), "fim": (novo + timedelta(hours=4)).isoformat()}
    assert log.details["depois"]["inicio"].endswith("+00:00"), "grava em UTC"
    assert log.details["choque"] == []
    assert "mudou_material_sem_reaprovacao" not in log.details
    assert len(callbacks) == 1 and enfileirados == [(s.pk, cursor.operador_id)]


@pytest.mark.django_db
def test_super_aprovada_movida_continua_aprovada_e_marca_o_log(agora, fake, enfileirados):
    s = _publicada(agora, projeto=ProjetoFactory(super=True))
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6)
    _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=1))

    sincronizar(cursor, fake, escrever=True, agora=agora)

    s.refresh_from_db()
    assert s.status == "aprovado" and s.inicio == novo
    log = AuditLog.objects.get(action="GCAL_COPIA_GOOGLE")
    assert log.details["aprovada_como_super"] is True
    assert log.details["mudou_material_sem_reaprovacao"] is True


@pytest.mark.django_db
def test_choque_de_horario_copia_e_grava_so_ids_e_codigos(agora, fake, enfileirados):
    formador = UsuarioFactory(first_name="Fulana", last_name="Secreta da Silva")
    novo = _hora(agora, 6)
    outro = _publicada(agora, eid="outro", inicio=novo)
    Participation.objects.create(solicitacao=outro, usuario=formador, role=Participation.Role.FORMADOR)
    s = _publicada(agora)
    Participation.objects.create(solicitacao=s, usuario=formador, role=Participation.Role.FORMADOR)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=1))

    sincronizar(cursor, fake, escrever=True, agora=agora)

    s.refresh_from_db()
    assert s.inicio == novo, "D3: copia mesmo com choque"
    log = AuditLog.objects.get(action="GCAL_COPIA_GOOGLE")
    assert {"usuario_id": formador.pk, "codigo": "X"} in log.details["choque"]
    assert all(set(c) == {"usuario_id", "codigo"} for c in log.details["choque"])
    assert NOME_SECRETO not in str(log.details) and "Fulana" not in str(log.details)


@pytest.mark.django_db
def test_hash_nulo_fica_nulo_e_nao_nulo_so_muda_depois_do_patch(agora, fake, enfileirados):
    adotada = _publicada(agora, eid="adotada", gcal_payload_hash=None)
    publicada = _publicada(agora, eid="publicada")
    em_dia = compute_payload_hash(publicada)  # em dia com o Google antes da cópia
    Solicitacao.objects.filter(pk=publicada.pk).update(gcal_payload_hash=em_dia)
    for s in (adotada, publicada):
        _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 7)
    for s in (adotada, publicada):
        _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=1))

    sincronizar(cursor, fake, escrever=True, agora=agora)

    adotada.refresh_from_db()
    publicada.refresh_from_db()
    assert adotada.gcal_payload_hash is None
    assert publicada.gcal_payload_hash == em_dia, "a cópia não recalcula o hash"

    for s in (adotada, publicada):
        assert copia.atualizar_descricao_no_google(s.pk, cursor.operador_id, client=fake) == "ok"

    adotada.refresh_from_db()
    publicada.refresh_from_db()
    assert adotada.gcal_payload_hash is None, "D5: linha adotada segue com hash nulo"
    assert publicada.gcal_payload_hash == compute_payload_hash(publicada)
    evento = fake.get(PINO, "publicada")
    assert "📅 Data:" in evento["description"] and "antiga" not in evento["description"]
    assert evento["summary"] == TITULO_SECRETO, "o PATCH só troca a descrição"
    assert datetime.fromisoformat(evento["start"]["dateTime"]) == novo


@pytest.mark.django_db
def test_hash_ja_divergente_vira_nulo_na_copia_e_o_patch_nao_o_recalcula(agora, fake, enfileirados):
    """Título ou convidados já fora de dia: o PATCH só da descrição não os acerta; o Reapply manda tudo."""
    s = _publicada(agora, gcal_payload_hash="a" * 40)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 7)
    _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=1))

    sincronizar(cursor, fake, escrever=True, agora=agora)
    s.refresh_from_db()
    assert s.inicio == novo and s.gcal_payload_hash is None

    assert copia.atualizar_descricao_no_google(s.pk, cursor.operador_id, client=fake) == "ok"
    s.refresh_from_db()
    assert s.gcal_payload_hash is None


@pytest.mark.django_db
def test_patch_da_descricao_com_refresh_morto_apaga_a_credencial_fora_da_transacao(agora, settings):
    """invalid_grant no refresh: a credencial sai e o GOOGLE_DISCONNECT fica, mesmo com o ValueError."""
    from unittest.mock import Mock, patch

    import requests

    from apps.core.models import GoogleOAuthCredential
    from apps.core.services.oauth import token_manager
    from apps.core.services.oauth.token_manager import encrypt_token

    settings.GCAL_CLIENT = "google"
    settings.GCAL_AUTH_MODE = "oauth"
    s = _publicada(agora)
    operador = UsuarioFactory()
    GoogleOAuthCredential.objects.create(
        user=operador,
        google_email="operador@example.invalid",
        access_token_encrypted=encrypt_token("velho"),
        refresh_token_encrypted=encrypt_token("revogado"),
        token_expiry=timezone.now() - timedelta(hours=2),
        scope="https://www.googleapis.com/auth/calendar",
    )
    resposta = Mock(status_code=400)
    resposta.json.return_value = {"error": "invalid_grant"}

    with (
        patch.dict("os.environ", {"GCAL_OAUTH_CLIENT_ID": "id", "GCAL_OAUTH_CLIENT_SECRET": "segredo"}),
        patch.object(token_manager.requests, "post") as post,
    ):
        post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resposta)
        with pytest.raises(ValueError):
            copia.atualizar_descricao_no_google(s.pk, operador.pk)

    assert not GoogleOAuthCredential.objects.filter(user=operador).exists()
    assert AuditLog.objects.filter(action="GOOGLE_DISCONNECT", usuario=operador).exists()


@pytest.mark.django_db
def test_patch_da_descricao_falho_nao_recalcula_hash(agora, fake):
    s = _publicada(agora, gcal_payload_hash="a" * 40)

    def _falha(*a, **k):
        raise RuntimeError("google fora")

    fake.patch_descricao = _falha
    with pytest.raises(RuntimeError):
        copia.atualizar_descricao_no_google(s.pk, 1, client=fake)
    s.refresh_from_db()
    assert s.gcal_payload_hash == "a" * 40


@pytest.mark.django_db
def test_patch_da_descricao_pula_linha_que_mudou_depois(agora, fake):
    s = _publicada(agora, status=Solicitacao.Status.REPROVADO)
    assert copia.atualizar_descricao_no_google(s.pk, 1, client=fake) == "pulado"


@pytest.mark.django_db
def test_depois_do_patch_a_rodada_seguinte_e_eco(agora, fake, enfileirados):
    s = _publicada(agora, gcal_payload_hash="a" * 40)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6)
    _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=1))
    sincronizar(cursor, fake, escrever=True, agora=agora)
    copia.atualizar_descricao_no_google(s.pk, cursor.operador_id, client=fake)
    cursor.refresh_from_db()
    antes = Solicitacao.objects.get(pk=s.pk).updated_at

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"] == {"eco": 1}
    assert Solicitacao.objects.get(pk=s.pk).updated_at == antes


@pytest.mark.django_db
def test_rollback_do_item_nao_enfileira_e_desfaz_a_escrita(
    agora, fake, enfileirados, monkeypatch, django_capture_on_commit_callbacks
):
    s = _publicada(agora)
    inicio_antes = s.inicio
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6)
    _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=1))

    def _quebra(*a, **k):
        raise IntegrityError("violação")

    monkeypatch.setattr(copia, "check_solicitacao_availability", _quebra)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "OK", "erro de domínio não aborta a rodada"
    assert r.resumo["falhas"] == [{"event_id": "evt1", "motivo": "IntegrityError"}]
    s.refresh_from_db()
    assert s.inicio == inicio_antes
    assert callbacks == [] and enfileirados == []
    assert not AuditLog.objects.filter(action="GCAL_COPIA_GOOGLE").exists()
    cursor.refresh_from_db()
    assert cursor.sync_token == r.token_novo, "erro de domínio: o token avança"


# --- D2: cancelado no Google vira reprovado ---


@pytest.mark.django_db
def test_cancelado_no_google_vira_reprovado_sem_autoridade_e_sai_do_google(
    agora, fake, enfileirados, django_capture_on_commit_callbacks
):
    s = _publicada(agora, gcal_payload_hash="a" * 40, meet_link="https://meet.google.com/x")
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    fake.delete(PINO, "evt1")

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"] == {"cancelado": 1}
    s.refresh_from_db()
    assert s.status == "reprovado"
    assert s.external_event_id is None and s.gcal_payload_hash is None and s.meet_link is None
    assert s.gcal_status == "NONE"
    rejeicao = AuditLog.objects.get(action="REJECT")
    assert rejeicao.usuario is None
    assert rejeicao.details == {
        "solicitacao_id": s.pk,
        "origem": "gcal_copia",
        "motivo": "cancelado_no_google",
        "status_anterior": "aprovado",
        "event_id_antigo": "evt1",
    }
    assert "autoridade" not in rejeicao.details, "não conta como decisão humana da PA-02"
    linha_do_tempo = AuditLog.objects.get(action="GCAL_COPIA_GOOGLE")
    assert linha_do_tempo.details["campo"] == "status"
    assert linha_do_tempo.details["depois"] == {"status": "reprovado"}
    assert callbacks == [] and enfileirados == []


@pytest.mark.django_db
def test_cancelado_de_evento_passado_fica_de_fora(agora, fake):
    s = _publicada(agora, inicio=agora - timedelta(days=2))
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    fake.delete(PINO, "evt1")

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"] == {"passado": 1}
    s.refresh_from_db()
    assert s.status == "aprovado" and s.external_event_id == "evt1"


@pytest.mark.django_db
def test_timeline_mostra_a_copia(agora, fake, enfileirados):
    from apps.core.serializers.solicitacao import EventDetailSerializer

    s = _publicada(agora)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    fake.delete(PINO, "evt1")
    sincronizar(cursor, fake, escrever=True, agora=agora)

    timeline = EventDetailSerializer(Solicitacao.objects.get(pk=s.pk)).data["timeline"]
    assert "GCAL_COPIA_GOOGLE" in [t["action"] for t in timeline]


# --- freio de massa ---


def _cancelamentos(agora, fake, n: int) -> tuple[GCalCopiaCursor, list[Solicitacao]]:
    linhas = [_publicada(agora, eid=f"c{i}") for i in range(n)]
    movida = _publicada(agora, eid="movida")
    for s in (*linhas, movida):
        _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    for s in linhas:
        fake.delete(PINO, s.external_event_id)
    novo = _hora(agora, 8)
    _mover_no_google(fake, "movida", novo, novo + timedelta(hours=1))
    return cursor, [*linhas, movida]


@pytest.mark.django_db
def test_freio_mais_de_5_cancelamentos_nao_aplica_nenhum_e_segura_o_token(agora, fake, enfileirados):
    cursor, linhas = _cancelamentos(agora, fake, copia.FREIO_CANCELAMENTOS + 1)
    token_antes = cursor.sync_token

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "OK"
    assert r.resumo["contagens"] == {"freio": 6, "copiar_horario": 1}
    assert r.resumo["freio"] == 6
    assert all(Solicitacao.objects.get(pk=s.pk).status == "aprovado" for s in linhas[:-1])
    assert not AuditLog.objects.filter(action="REJECT").exists()
    assert Solicitacao.objects.get(pk=linhas[-1].pk).inicio == _hora(agora, 8), "horário segue sendo copiado"
    cursor.refresh_from_db()
    assert cursor.ultimo_erro == "freio: 6 cancelamentos"
    assert cursor.sync_token == token_antes, "a linha de base fica para a próxima rodada"

    r2 = sincronizar(cursor, fake, escrever=True, agora=agora)
    assert r2.resumo["contagens"] == {"freio": 6, "eco": 1}, "os cancelamentos voltam na rodada seguinte"


@pytest.mark.django_db
def test_freio_segue_puxado_quando_a_contagem_cai_sem_o_dono_liberar(agora, fake, enfileirados):
    """Um dos 6 começa e vira passado: os 5 que sobram continuam segurados até o `--liberar-freio`."""
    linhas = [_publicada(agora, eid=f"c{i}") for i in range(copia.FREIO_CANCELAMENTOS)]
    linhas.append(_publicada(agora, eid="logo", inicio=agora + timedelta(hours=1)))
    for s in linhas:
        _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    for s in linhas:
        fake.delete(PINO, s.external_event_id)
    r1 = sincronizar(cursor, fake, escrever=True, agora=agora)
    assert r1.resumo["contagens"] == {"freio": 6}
    cursor.refresh_from_db()
    token_segurado = cursor.sync_token

    r2 = sincronizar(cursor, fake, escrever=True, agora=agora + timedelta(hours=2))

    assert r2.status == "OK"
    assert r2.resumo["contagens"] == {"freio": 5, "passado": 1}
    assert not AuditLog.objects.filter(action="REJECT").exists()
    assert all(Solicitacao.objects.get(pk=s.pk).status == "aprovado" for s in linhas)
    cursor.refresh_from_db()
    assert cursor.sync_token == token_segurado and cursor.ultimo_erro == "freio: 5 cancelamentos"


@pytest.mark.django_db
def test_freio_liberado_pelo_dono_aplica(agora, fake, enfileirados):
    cursor, _ = _cancelamentos(agora, fake, copia.FREIO_CANCELAMENTOS + 1)
    r1 = sincronizar(cursor, fake, escrever=True, agora=agora)
    assert r1.resumo["freio"] == 6
    cursor.refresh_from_db()

    r = sincronizar(cursor, fake, escrever=True, agora=agora, liberar_freio=True)

    assert r.resumo["contagens"]["cancelado"] == 6
    assert AuditLog.objects.filter(action="REJECT").count() == 6
    cursor.refresh_from_db()
    assert cursor.ultimo_erro == ""


@pytest.mark.django_db
def test_liberar_sem_rodada_segurada_nao_solta_o_freio(agora, fake, enfileirados):
    """Sem rodada segurada antes, o dono não viu a contagem: o freio segura como sempre."""
    cursor, _ = _cancelamentos(agora, fake, copia.FREIO_CANCELAMENTOS + 1)

    r = sincronizar(cursor, fake, escrever=True, agora=agora, liberar_freio=True)

    assert r.resumo["freio"] == 6
    assert not AuditLog.objects.filter(action="REJECT").exists()


@pytest.mark.django_db
def test_liberar_nao_cobre_cancelamentos_que_chegaram_depois(agora, fake, enfileirados):
    """6 segurados, mais 20 cancelados no Google: a liberação dos 6 não aplica os 26."""
    cursor, _ = _cancelamentos(agora, fake, copia.FREIO_CANCELAMENTOS + 1)
    mais = [_publicada(agora, eid=f"d{i}") for i in range(20)]
    for s in mais:
        _no_google(fake, s)
    sincronizar(cursor, fake, escrever=True, agora=agora)  # segura os 6; os 20 novos entram na base
    cursor.refresh_from_db()
    assert cursor.resumo["freio"] == 6
    token_segurado = cursor.sync_token
    for s in mais:
        fake.delete(PINO, s.external_event_id)

    r = sincronizar(cursor, fake, escrever=True, agora=agora, liberar_freio=True)

    assert r.resumo["freio"] == 26
    assert not AuditLog.objects.filter(action="REJECT").exists()
    cursor.refresh_from_db()
    assert cursor.sync_token == token_segurado and cursor.ultimo_erro == "freio: 26 cancelamentos"


@pytest.mark.django_db
def test_freio_no_observar_avisa_mas_avanca_o_token(agora, fake, enfileirados):
    cursor, linhas = _cancelamentos(agora, fake, copia.FREIO_CANCELAMENTOS + 1)
    trocar_modo(cursor, "observar")
    token_antes = cursor.sync_token

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"] == {"freio": 6, "copiar_horario": 1}
    cursor.refresh_from_db()
    assert cursor.ultimo_erro == "freio: 6 cancelamentos", "o freio segue como aviso"
    assert cursor.sync_token != token_antes, "no observar nada é aplicado: o token avança"

    sincronizar(cursor, fake, escrever=True, agora=agora)
    cursor.refresh_from_db()
    assert cursor.resumo["contagens"] == {"freio": 6, "copiar_horario": 1}, "a mesma mudança não conta 2x"
    assert cursor.resumo["futuro"] == 7
    assert all(Solicitacao.objects.get(pk=s.pk).status == "aprovado" for s in linhas)


@pytest.mark.django_db
def test_5_cancelamentos_passam_pelo_freio(agora, fake, enfileirados):
    cursor, _ = _cancelamentos(agora, fake, copia.FREIO_CANCELAMENTOS)

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"]["cancelado"] == 5
    assert AuditLog.objects.filter(action="REJECT").count() == 5


# --- erros ---


@pytest.mark.django_db
def test_erro_de_infra_aborta_sem_mexer_no_token(agora, fake, enfileirados, monkeypatch):
    a = _publicada(agora, eid="a")
    b = _publicada(agora, eid="b")
    for s in (a, b):
        _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    token_antes = cursor.sync_token
    novo = _hora(agora, 6)
    for s in (a, b):
        _mover_no_google(fake, s.external_event_id, novo, novo + timedelta(hours=1))
    chamadas = {"n": 0}
    original = copia.check_solicitacao_availability

    def _segundo_cai(s, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 2:
            raise OperationalError("conexão caiu")
        return original(s, **k)

    monkeypatch.setattr(copia, "check_solicitacao_availability", _segundo_cai)

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "ERROR" and r.erro == "OperationalError"
    cursor.refresh_from_db()
    assert cursor.sync_token == token_antes
    assert cursor.ultimo_erro == "OperationalError"


@pytest.mark.django_db
def test_erro_de_infra_na_leitura_do_google(agora, fake):
    from googleapiclient.errors import HttpError
    from httplib2 import Response

    cursor = _cursor()

    def _cai(*a, **k):
        raise HttpError(Response({"status": 500}), b'{"error": {"message": "fulana@example.com"}}')

    fake.list_changes = _cai
    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "ERROR" and r.erro == "HttpError 500"
    cursor.refresh_from_db()
    assert cursor.sync_token is None and cursor.ultimo_erro == "HttpError 500"


@pytest.mark.django_db
def test_calendario_diferente_do_pino_nao_le(agora, fake, settings):
    cursor = _cursor(calendar_id="outra-agenda")
    fake.list_changes = lambda *a, **k: pytest.fail("não podia ler")

    assert sincronizar(cursor, fake, escrever=True, agora=agora).status == "ERROR"
    settings.GCAL_OAUTH_CALENDAR_ID = "primary"
    assert sincronizar(_cursor(calendar_id="primary"), fake, escrever=True, agora=agora).status == "ERROR"


@pytest.mark.django_db
def test_copiar_sem_operador_e_erro(agora, fake):
    cursor = _cursor(operador=None)
    assert sincronizar(cursor, fake, escrever=True, agora=agora).status == "ERROR"


# --- adiados ---


@pytest.mark.django_db
def test_adiado_pendente_e_relido_e_aplicado_quando_libera(agora, fake, enfileirados):
    s = _publicada(agora)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    Solicitacao.objects.filter(pk=s.pk).update(gcal_status=Solicitacao.GCalStatus.PENDING)
    novo = _hora(agora, 6)
    _mover_no_google(fake, "evt1", novo, novo + timedelta(hours=1))

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"] == {"pendente_gcal": 1}
    cursor.refresh_from_db()
    assert cursor.adiados == [{"event_id": "evt1", "tentativas": 1}]
    token = cursor.sync_token

    Solicitacao.objects.filter(pk=s.pk).update(gcal_status=Solicitacao.GCalStatus.PUBLISHED)
    assert fake.list_changes(PINO, token)[0] == [], "o syncToken não devolve a mudança de novo"
    r2 = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r2.resumo["contagens"] == {"copiar_horario": 1}
    assert Solicitacao.objects.get(pk=s.pk).inicio == novo
    cursor.refresh_from_db()
    assert cursor.adiados == []


@pytest.mark.django_db
def test_adiado_5_vezes_vira_falha(agora, fake):
    s = _publicada(agora, gcal_status=Solicitacao.GCalStatus.PENDING)
    _no_google(fake, s)
    cursor = _cursor(adiados=[{"event_id": "evt1", "tentativas": copia.MAX_TENTATIVAS_ADIADO - 1}])

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert {"event_id": "evt1", "motivo": "adiado_5x"} in r.resumo["falhas"]
    cursor.refresh_from_db()
    assert cursor.adiados == []


@pytest.mark.django_db
def test_linha_travada_vira_adiado(agora, fake, enfileirados, monkeypatch):
    s = _publicada(agora)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6)
    _mover_no_google(fake, "evt1", novo, novo + timedelta(hours=1))
    monkeypatch.setattr(copia, "_travar_linha", lambda pk: None)

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"] == {"trava_ocupada": 1}
    cursor.refresh_from_db()
    assert cursor.adiados == [{"event_id": "evt1", "tentativas": 1}]


# --- token: 410 e compare-and-set ---


@pytest.mark.django_db
def test_410_refaz_leitura_completa_na_mesma_rodada(agora, fake, enfileirados):
    s = _publicada(agora)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6)
    _mover_no_google(fake, "evt1", novo, novo + timedelta(hours=1))
    fake.sync_token_expirado = True

    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "OK" and r.resumo["leitura_completa"] is True
    assert r.resumo["contagens"] == {"copiar_horario": 1}
    cursor.refresh_from_db()
    assert cursor.sync_token == r.token_novo


@pytest.mark.django_db
def test_token_so_avanca_se_ninguem_mexeu_nele(agora, fake):
    cursor = _cursor()
    original = fake.list_changes

    def _troca_no_meio(cal, token):
        GCalCopiaCursor.objects.filter(pk=cursor.pk).update(sync_token="mexido-por-outro")
        return original(cal, token)

    fake.list_changes = _troca_no_meio
    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "ERROR"
    cursor.refresh_from_db()
    assert cursor.sync_token == "mexido-por-outro"


@pytest.mark.django_db
def test_troca_de_modo_no_meio_da_rodada_sem_token_descarta_o_resultado(agora, fake):
    """Sem token, `trocar_modo(copiar)` grava nulo de novo: só o token não pegaria a troca."""
    cursor = _cursor(modo="observar")
    original = fake.list_changes

    def _troca_no_meio(cal, token):
        trocar_modo(GCalCopiaCursor.objects.get(pk=cursor.pk), "copiar")
        return original(cal, token)

    fake.list_changes = _troca_no_meio
    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.status == "ERROR"
    cursor.refresh_from_db()
    assert cursor.modo == "copiar" and cursor.sync_token is None, "a 1ª rodada do copiar relê tudo"


@pytest.mark.django_db
def test_volta_ao_observar_antes_da_trava_nao_aplica(agora, fake, enfileirados):
    """O cursor foi carregado em `copiar`, mas o dono mandou parar antes de a rodada pegar a trava."""
    s = _publicada(agora)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    velho = GCalCopiaCursor.objects.get(pk=cursor.pk)
    trocar_modo(cursor, "observar")
    novo = _hora(agora, 6)
    _mover_no_google(fake, "evt1", novo, novo + timedelta(hours=1))

    r = sincronizar(velho, fake, escrever=True, agora=agora)

    assert r.status == "OK", r.erro
    assert r.resumo["modo"] == "observar"
    assert Solicitacao.objects.get(pk=s.pk).inicio == s.inicio
    assert not AuditLog.objects.filter(action="GCAL_COPIA_GOOGLE").exists()


@pytest.mark.django_db
def test_linha_republicada_depois_da_leitura_vira_adiado(agora, fake, enfileirados):
    """Lápide lida e a linha republicada antes da trava: o item lido já não vale."""
    s = _publicada(agora)
    _no_google(fake, s)
    cursor = _cursor()
    _linha_de_base(cursor, fake, agora)
    fake.delete(PINO, "evt1")
    original = fake.list_changes

    def _republica_no_meio(cal, token):
        lido = original(cal, token)
        Solicitacao.objects.get(pk=s.pk).mark_gcal(status=Solicitacao.GCalStatus.PUBLISHED)
        return lido

    fake.list_changes = _republica_no_meio
    r = sincronizar(cursor, fake, escrever=True, agora=agora)

    assert r.resumo["contagens"] == {"pendente_gcal": 1}
    atual = Solicitacao.objects.get(pk=s.pk)
    assert (atual.status, atual.external_event_id) == ("aprovado", "evt1")
    assert not AuditLog.objects.filter(action="REJECT").exists()
    cursor.refresh_from_db()
    assert cursor.adiados == [{"event_id": "evt1", "tentativas": 1}]


# --- observar e trocar_modo ---


@pytest.mark.django_db
def test_observar_nao_escreve_no_sistema_avanca_token_e_junta_o_resumo(
    agora, fake, enfileirados, django_capture_on_commit_callbacks
):
    a = _publicada(agora, eid="a")
    b = _publicada(agora, eid="b")
    for s in (a, b):
        _no_google(fake, s)
    cursor = _cursor(modo="observar")
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6)
    _mover_no_google(fake, "a", novo, novo + timedelta(hours=1))
    fake.delete(PINO, "b")
    token_antes = cursor.sync_token

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        sincronizar(cursor, fake, escrever=True, agora=agora)
        cursor.refresh_from_db()
        _mover_no_google(fake, "a", novo + timedelta(hours=1), novo + timedelta(hours=2))
        sincronizar(cursor, fake, escrever=True, agora=agora)

    for s in (a, b):
        atual = Solicitacao.objects.get(pk=s.pk)
        assert (atual.inicio, atual.status, atual.external_event_id) == (s.inicio, "aprovado", s.external_event_id)
    assert not AuditLog.objects.filter(action__in=["GCAL_COPIA_GOOGLE", "REJECT"]).exists()
    assert callbacks == [] and enfileirados == []
    cursor.refresh_from_db()
    assert cursor.sync_token != token_antes
    assert cursor.resumo["modo"] == "observar" and cursor.resumo["rodadas"] == 3
    assert cursor.resumo["ids"]["copiar_horario"] == [f"s{a.pk}"], "s<id> sem repetição"
    assert cursor.resumo["ids"]["cancelado"] == [f"s{b.pk}"]
    assert cursor.resumo["contagens"]["copiar_horario"] == 2


@pytest.mark.django_db
def test_trocar_modo_para_copiar_zera_o_token():
    cursor = _cursor(modo="observar", sync_token="t1")

    trocar_modo(cursor, "observar")
    cursor.refresh_from_db()
    assert cursor.sync_token == "t1"

    trocar_modo(cursor, "copiar")
    cursor.refresh_from_db()
    assert cursor.modo == "copiar" and cursor.sync_token is None


@pytest.mark.django_db
def test_dry_run_nao_escreve_nada(agora, fake, enfileirados, django_capture_on_commit_callbacks):
    s = _publicada(agora)
    _no_google(fake, s)
    novo = _hora(agora, 6)
    _mover_no_google(fake, "evt1", novo, novo + timedelta(hours=1))
    cursor = _cursor()

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        r = sincronizar(cursor, fake, escrever=False, agora=agora)

    assert r.resumo["contagens"] == {"copiar_horario": 1}
    assert Solicitacao.objects.get(pk=s.pk).inicio == s.inicio
    assert not AuditLog.objects.exists()
    assert callbacks == [] and enfileirados == []
    cursor.refresh_from_db()
    assert cursor.sync_token is None and cursor.resumo == {}


# --- trava ---


@pytest.mark.django_db
def test_trava_ocupada_da_skipped(agora, fake):
    cursor = _cursor()
    outra = connection.copy()
    try:
        with outra.cursor() as c:
            c.execute("SELECT pg_advisory_lock(%s, %s)", list(copia._TRAVA_COPIA))
        fake.list_changes = lambda *a, **k: pytest.fail("não podia ler")

        r = sincronizar(cursor, fake, escrever=True, agora=agora)

        assert r.status == "SKIPPED"
    finally:
        outra.close()


@pytest.mark.django_db
def test_trava_sai_mesmo_com_erro(agora, fake):
    cursor = _cursor()

    def _cai(*a, **k):
        raise RuntimeError("Google não devolveu nextSyncToken na última página")

    fake.list_changes = _cai
    assert sincronizar(cursor, fake, escrever=True, agora=agora).status == "ERROR"

    outra = connection.copy()
    try:
        with outra.cursor() as c:
            c.execute("SELECT pg_try_advisory_lock(%s, %s)", list(copia._TRAVA_COPIA))
            assert c.fetchone()[0] is True, "a trava saiu no finally"
            c.execute("SELECT pg_advisory_unlock(%s, %s)", list(copia._TRAVA_COPIA))
    finally:
        outra.close()


# --- dado pessoal ---


@pytest.mark.django_db
def test_sem_dado_pessoal_no_auditlog_e_no_log(agora, fake, enfileirados):
    operador = UsuarioFactory(first_name="Operadora", last_name="Secreta", email="operadora.secreta@example.com")
    autor = UsuarioFactory(first_name="Fulana", last_name="Secreta da Silva", email=EMAIL_SECRETO)
    movida = _publicada(agora, eid="movida", usuario=autor, observacoes=NOME_SECRETO)
    cancelada = _publicada(agora, eid="cancelada", usuario=autor)
    for s in (movida, cancelada):
        _no_google(fake, s)
    cursor = _cursor(operador=operador)
    _linha_de_base(cursor, fake, agora)
    novo = _hora(agora, 6)
    _mover_no_google(fake, "movida", novo, novo + timedelta(hours=1))
    fake.delete(PINO, "cancelada")

    with _logs() as logs:
        r = sincronizar(cursor, fake, escrever=True, agora=agora)
        copia.atualizar_descricao_no_google(movida.pk, operador.pk, client=fake)

    assert r.resumo["contagens"] == {"copiar_horario": 1, "cancelado": 1}
    textos = [str(log.details) for log in AuditLog.objects.all()]
    textos += [rec.getMessage() for rec in logs]
    cursor.refresh_from_db()
    textos += [str(cursor.resumo), cursor.ultimo_erro, str(cursor.adiados)]
    assert logs, "a rodada loga o resumo"
    tudo = "\n".join(textos)
    for segredo in ("Fulana", "Secreta", EMAIL_SECRETO, "operadora.secreta", TITULO_SECRETO, autor.cpf):
        assert segredo not in tudo, segredo


# --- fake: update é PATCH ---


def test_fake_update_e_merge_e_mantem_hangout_link():
    fake = FakeCalendarClient()
    fake.insert("cal", "asv21", {"summary": "t", "description": "d", "conferenceData": {"createRequest": {}}})
    assert fake.get("cal", "asv21")["hangoutLink"] == "https://meet.google.com/fake-1"

    fake.update("cal", "asv21", {"description": "nova"})

    evento = fake.get("cal", "asv21")
    assert evento["summary"] == "t" and evento["description"] == "nova"
    assert evento["hangoutLink"] == "https://meet.google.com/fake-1"


def test_patch_descricao_do_cliente_oauth_manda_so_a_descricao_sem_convite(settings):
    from types import SimpleNamespace

    from apps.core.services.gcal_oauth_client import OAuthCalendarClient

    settings.GCAL_SEND_UPDATES = "all"
    chamadas: list[dict[str, Any]] = []

    class _Requisicao:
        def execute(self) -> dict[str, Any]:
            return {"id": "evt1"}

    class _Eventos:
        def patch(self, **params: Any) -> _Requisicao:
            chamadas.append(params)
            return _Requisicao()

    class _Servico:
        def events(self) -> _Eventos:
            return _Eventos()

    cliente = OAuthCalendarClient.__new__(OAuthCalendarClient)
    cliente.service = _Servico()
    cliente.credential = SimpleNamespace(google_email="conta@example.com", user_id=7)

    cliente.patch_descricao(PINO, "evt1", "nova")

    assert chamadas == [{"calendarId": PINO, "eventId": "evt1", "body": {"description": "nova"}, "sendUpdates": "none"}]
