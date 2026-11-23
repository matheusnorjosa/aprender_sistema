"""CON-08 B — "Cancelar evento" de formação: o título no Google ganha "(CANCELADO) " e a linha nunca mais vai ao Google.

Desenho aprovado em 23/11/2026 (relatório `con08b_desenho_2026-11-23.md`, com as decisões do dono: o botão fica ao
lado do "Tirar só do Google"; o Excluir de evento de formação no Google marca e apaga a linha; sem e-mail aos
convidados). O que se prova aqui:

- o pedido grava a marca `cancelado_na_agenda` sob a trava, já no PENDING, e só aceita evento de formação;
- nenhum caminho que publica, reenvia, reaplica ou tira do Google age sobre a linha marcada;
- o serviço só troca o título (PATCH de `summary`, `sendUpdates="none"`), põe o marcador uma vez, nunca traz de
  volta evento apagado e nunca esquece onde o evento está;
- a tarefa volta a linha a PUBLISHED, registra o desfecho e, na falha, marca ERROR sem enfileirar nova tentativa;
- o Excluir de evento de formação no Google marca o título e só então apaga a linha.

O Google é sempre simulado (cliente falso); nada sai da máquina. Títulos sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false, reportFunctionMemberAccess=false

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection, transaction
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.exceptions import ConflictError
from apps.core.models import AuditLog, Gerencia, Solicitacao
from apps.core.services.gcal.utils import _executar_uma_vez
from apps.core.services.gcal.validation import _event_id_for
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
)

CAL = "primary"
_HASH = "c" * 40
_TITULO = "EF - Presencial 3º encontro - Projeto Sintetico"
_MARCADO = f"(CANCELADO) {_TITULO}"
_PASSTHROUGH = "apps.core.services.gcal.sync._retry_with_circuit_breaker"
_FABRICA = "apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id"
_DELAY_CANCELAR_NA_AGENDA = "apps.core.tasks.task_cancelar_na_agenda.delay"
_DELAY_PUBLICAR = "apps.core.tasks.task_publish_solicitacao_to_gcal.delay"
_DELAY_TIRAR = "apps.core.tasks.task_cancel_solicitacao_from_gcal.delay"


# =============================================================================
# Ajudantes
# =============================================================================


def _formacao(*, tipo: str = "Presencial", **extra: Any) -> Solicitacao:
    """Evento de formação aprovado, futuro e publicado pelo sistema (id `asv2{id}`), salvo o que `extra` trocar."""
    inicio = timezone.now() + timedelta(days=3)
    dados: dict[str, Any] = {
        "status": "aprovado",
        "tipo_evento": TipoEventoFactory(nome=tipo),
        "encontro": "3",
        "inicio": inicio,
        "fim": inicio + timedelta(hours=2),
        "gcal_status": "PUBLISHED",
        "gcal_payload_hash": _HASH,
        **extra,
    }
    s = SolicitacaoFactory(**dados)
    if "external_event_id" not in extra:
        s.external_event_id = _event_id_for(s)
        s.save(update_fields=["external_event_id"])
    return s


def _no_google(fake: FakeCalendarClient, s: Solicitacao, titulo: str = _TITULO) -> None:
    fake.insert(
        CAL,
        s.external_event_id or _event_id_for(s),
        {
            "summary": titulo,
            "description": "descrição sintética",
            "start": {"dateTime": s.inicio.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": s.fim.isoformat(), "timeZone": "UTC"},
        },
    )


def _titulo(fake: FakeCalendarClient, s: Solicitacao) -> str:
    return fake.get(CAL, s.external_event_id or _event_id_for(s))["summary"]


class _Contador:
    """Embrulha o fake e conta as escritas no Google (insert, update, patch_titulo, delete)."""

    def __init__(self, fake: FakeCalendarClient) -> None:
        self.fake = fake
        self.chamadas: list[str] = []

    def __getattr__(self, nome: str) -> Any:
        alvo = getattr(self.fake, nome)
        if nome not in {"insert", "update", "patch_titulo", "patch_descricao", "delete"}:
            return alvo

        def _conta(*args: Any, **kwargs: Any) -> Any:
            self.chamadas.append(nome)
            return alvo(*args, **kwargs)

        return _conta


@pytest.fixture
def google(monkeypatch) -> Iterator[FakeCalendarClient]:
    """Fake na fábrica do service account e disjuntor transparente."""
    fake = FakeCalendarClient()
    monkeypatch.setattr(_FABRICA, lambda: (fake, CAL))
    with patch(_PASSTHROUGH, side_effect=lambda f, **_: f()):
        yield fake


@pytest.fixture
def modo_google(settings):
    settings.GCAL_CLIENT = "google"
    settings.GCAL_AUTH_MODE = "service_account"


def _api(user=None, **opcoes) -> APIClient:
    api = APIClient(**opcoes)
    api.force_authenticate(user or UsuarioFactory(superuser=True))
    return api


def _linha(s: Solicitacao) -> dict[str, Any]:
    return (
        Solicitacao.objects.filter(pk=s.pk)
        .values("gcal_status", "gcal_pedido", "gcal_payload_hash", "external_event_id", "cancelado_na_agenda")
        .get()
    )


# =============================================================================
# 1. O pedido grava a marca sob a trava
# =============================================================================


@pytest.mark.django_db
class TestPedido:
    def test_pedido_cancelar_na_agenda_marca_a_linha_sob_a_trava(self):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        s = _formacao()

        pedido = pedir_operacao_gcal(s.pk, "cancelar_na_agenda")

        linha = _linha(s)
        assert linha["cancelado_na_agenda"] is True
        assert linha["gcal_status"] == "PENDING"
        assert linha["gcal_pedido"] == pedido
        assert linha["gcal_payload_hash"] == _HASH, "o hash fica: a linha volta a PUBLISHED com ele"

    @pytest.mark.parametrize("estado", [{"gcal_status": "ERROR"}, {"gcal_status": "PENDING"}])
    def test_aceita_error_e_pending_com_id(self, estado):
        """Como o Tirar: o publicar pendente é substituído, e o ERROR com id pode ser cancelado."""
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        s = _formacao(**estado)

        pedir_operacao_gcal(s.pk, "cancelar_na_agenda")

        assert _linha(s)["cancelado_na_agenda"] is True

    def test_evento_que_nao_e_de_formacao_e_recusado_sem_gravar(self):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        s = _formacao(tipo="Reunião de Alinhamento")
        antes = _linha(s)

        with pytest.raises(ConflictError) as erro:
            pedir_operacao_gcal(s.pk, "cancelar_na_agenda")

        assert erro.value.details["code"] == "nao_e_evento_de_formacao"
        assert _linha(s) == antes

    def test_sem_id_e_sem_published_e_recusado(self):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        s = _formacao(gcal_status="NONE", external_event_id=None)
        antes = _linha(s)

        with pytest.raises(ConflictError) as erro:
            pedir_operacao_gcal(s.pk, "cancelar_na_agenda")

        assert erro.value.details["code"] == "not_published"
        assert _linha(s) == antes

    def test_tirar_do_google_recusa_linha_marcada(self):
        from apps.core.services.solicitacao_publish import pedir_operacao_gcal

        s = _formacao(cancelado_na_agenda=True)
        antes = _linha(s)

        with pytest.raises(ConflictError) as erro:
            pedir_operacao_gcal(s.pk, "cancelar")

        assert erro.value.details["code"] == "cancelado_na_agenda"
        assert _linha(s) == antes

    def test_o_campo_fica_fora_dos_formularios(self):
        assert Solicitacao._meta.get_field("cancelado_na_agenda").editable is False


# =============================================================================
# 2. motivo_nao_publicavel: a marca vem primeiro
# =============================================================================


@pytest.mark.django_db
def test_motivo_nao_publicavel_cancelado_na_agenda_primeiro():
    from apps.core.services.solicitacao_publish import MENSAGENS_NAO_PUBLICAVEL, motivo_nao_publicavel

    passado = timezone.now() - timedelta(days=3)
    s = _formacao(cancelado_na_agenda=True, inicio=passado, fim=passado + timedelta(hours=2), encontro=None)

    assert motivo_nao_publicavel(s) == "cancelado_na_agenda"
    assert motivo_nao_publicavel(s, reenvio=True) == "cancelado_na_agenda"
    assert "cancelado na agenda" in MENSAGENS_NAO_PUBLICAVEL["cancelado_na_agenda"]


# =============================================================================
# 3 e 4. Publicar, reenviar, reaplicar, lotes e Tirar recusam a linha marcada
# =============================================================================


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
@pytest.mark.parametrize("gcal_status", ["PUBLISHED", "ERROR"])
def test_publicar_reenviar_reaplicar_e_lotes_recusam_linha_cancelada(gcal_status):
    s = _formacao(cancelado_na_agenda=True, gcal_status=gcal_status)
    api = _api()

    with patch(_DELAY_PUBLICAR) as delay:
        publicar = api.post(f"/api/solicitacoes/{s.pk}/publish/", {}, format="json")
        reenviar = api.post(f"/api/solicitacoes/{s.pk}/resync-gcal/", {}, format="json")
        lotes = [
            api.post("/api/gcal/publish-batch/", {"solicitacao_ids": [s.pk]}, format="json"),
            api.post("/api/gcal/dashboard/batch/reapply/", {"ids": [s.pk]}, format="json"),
            api.post("/api/gcal/dashboard/batch/resync/", {"ids": [s.pk]}, format="json"),
        ]

    assert (publicar.status_code, publicar.data["code"]) == (400, "cancelado_na_agenda")
    assert (reenviar.status_code, reenviar.data["code"]) == (400, "cancelado_na_agenda")
    for resposta in lotes:
        assert resposta.data["queued"] == 0, resposta.data
        assert [e["code"] for e in resposta.data["errors"]] == ["cancelado_na_agenda"]
    delay.assert_not_called()
    assert _linha(s)["gcal_status"] == gcal_status


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
def test_tirar_do_google_recusa_linha_cancelada_na_agenda(google):
    s = _formacao(cancelado_na_agenda=True)
    _no_google(google, s, _MARCADO)

    with patch(_DELAY_TIRAR) as delay:
        resposta = _api().post(f"/api/solicitacoes/{s.pk}/cancel-gcal/", {}, format="json")

    assert resposta.status_code == 409, resposta.data
    assert resposta.data["errors"]["code"] == "cancelado_na_agenda"
    delay.assert_not_called()
    evento = google.get(CAL, s.external_event_id)
    assert (evento["summary"], evento["status"]) == (_MARCADO, "confirmed")


# =============================================================================
# 5 a 10. O serviço que marca o título
# =============================================================================


def _marcar(s: Solicitacao, client: Any = None):
    from apps.core.services.gcal_sync_service import marcar_cancelado_no_google

    return marcar_cancelado_no_google(s, client=client)


@pytest.mark.django_db
def test_marcar_poe_o_marcador_uma_vez(google):
    s = _formacao()
    _no_google(google, s)

    primeiro = _marcar(s)
    segundo = _marcar(s)

    assert (primeiro.action, primeiro.summary) == ("UPDATE", "marcado")
    assert (segundo.action, segundo.summary) == ("SKIP", "ja_marcado")
    assert _titulo(google, s) == _MARCADO
    evento = google.get(CAL, s.external_event_id)
    assert evento["description"] == "descrição sintética", "só o título muda"
    assert evento["status"] == "confirmed"


@pytest.mark.django_db
def test_marcador_digitado_a_mao_nao_e_repetido(google):
    s = _formacao()
    _no_google(google, s, "  (cancelado)x")

    assert _marcar(s).summary == "ja_marcado"
    assert _titulo(google, s) == "  (cancelado)x"


@pytest.mark.django_db
@pytest.mark.parametrize("como", ["apagado_brando", "nao_existe", "410"])
def test_marcar_nao_traz_de_volta_evento_apagado(google, como):
    s = _formacao()
    contador = _Contador(google)
    if como == "apagado_brando":
        _no_google(google, s)
        google.delete(CAL, s.external_event_id)
        contador.chamadas.clear()
    elif como == "410":
        erro = Exception("gone")
        erro.resp = SimpleNamespace(status=410)
        contador.get = lambda *_a, **_k: (_ for _ in ()).throw(erro)
    antes = _linha(s)

    resultado = _marcar(s, client=contador)

    assert (resultado.action, resultado.summary) == ("SKIP", "ja_saiu")
    assert contador.chamadas == [], "nada de insert, update nem patch"
    assert _linha(s) == antes, "a linha guarda o id e o hash (C0-2)"
    if como == "apagado_brando":
        assert google.get(CAL, s.external_event_id)["status"] == "cancelled"


@pytest.mark.django_db
def test_marcar_id_adotado_nao_achado_levanta(google):
    s = _formacao(external_event_id="0a1b2c3d4e5f6g7h8i9j0k1l2m")
    contador = _Contador(google)
    antes = _linha(s)

    with pytest.raises(ValueError, match="adotado"):
        _marcar(s, client=contador)

    assert contador.chamadas == []
    assert _linha(s) == antes


_ADOTADO = "0a1b2c3d4e5f6g7h8i9j0k1l2m"


def _apagado_no_google(fake: FakeCalendarClient, s: Solicitacao) -> Solicitacao:
    """Evento que alguém apagou direto no Google (DELETE brando): o GET ainda o acha, com `status: cancelled`."""
    _no_google(fake, s)
    fake.delete(CAL, s.external_event_id)
    return s


@pytest.mark.django_db
def test_marcar_id_adotado_apagado_no_google_da_ja_saiu(google):
    """Passo 5 do desenho: só o id adotado que o GET não acha levanta; achado e apagado, o evento já saiu."""
    s = _apagado_no_google(google, _formacao(external_event_id=_ADOTADO))
    contador = _Contador(google)
    antes = _linha(s)

    resultado = _marcar(s, client=contador)

    assert (resultado.action, resultado.summary) == ("SKIP", "ja_saiu")
    assert contador.chamadas == [], "nada de insert, update nem patch"
    assert _linha(s) == antes, "a linha guarda o id adotado e o hash"
    assert google.get(CAL, _ADOTADO)["status"] == "cancelled", "não traz de volta"


@pytest.mark.django_db
def test_marcar_sem_acesso_ao_calendario_levanta(google):
    s = _formacao()
    _no_google(google, s)
    google.calendar_accessible = lambda _cal: False

    with pytest.raises(ValueError, match="acesso ao calendário"):
        _marcar(s)

    assert _titulo(google, s) == _TITULO


@pytest.mark.django_db
def test_marcar_patch_engolido_confere_o_titulo(google):
    """409/412 no texto do erro (sem `resp`) vira sucesso no `_executar_uma_vez`: a releitura decide."""
    s = _formacao()
    _no_google(google, s)

    def _conflito(*_a, **_k):
        raise Exception("HTTP 409 conflict")

    google.patch_titulo = _conflito
    with patch(_PASSTHROUGH, side_effect=lambda f, **_: _executar_uma_vez(f)):
        with pytest.raises(RuntimeError, match="não confirmou"):
            _marcar(s)

    original = FakeCalendarClient.patch_titulo

    def _aplica_e_conflita(cal, eid, titulo):
        original(google, cal, eid, titulo)
        raise Exception("HTTP 412 precondition")

    google.patch_titulo = _aplica_e_conflita
    with patch(_PASSTHROUGH, side_effect=lambda f, **_: _executar_uma_vez(f)):
        resultado = _marcar(s)

    assert (resultado.action, resultado.summary) == ("UPDATE", "marcado")
    assert _titulo(google, s) == _MARCADO


@pytest.mark.django_db
def test_marcar_titulo_longo_corta_em_1000(google):
    s = _formacao()
    _no_google(google, s, "x" * 995)

    _marcar(s)

    titulo = _titulo(google, s)
    assert len(titulo) == 1000
    assert titulo.startswith("(CANCELADO) x") and titulo.endswith("...")


# =============================================================================
# 11 e 12. Os clientes
# =============================================================================


def test_fake_patch_titulo_evento_inexistente_404():
    fake = FakeCalendarClient()

    with pytest.raises(Exception) as erro:
        fake.patch_titulo(CAL, "asv2nao", "(CANCELADO) x")

    assert erro.value.resp.status == 404
    assert fake.get(CAL, "asv2nao") is None, "não cria evento fantasma"


def test_fake_patch_titulo_nao_mexe_no_status():
    fake = FakeCalendarClient()
    fake.insert(CAL, "asv21", {"summary": "t", "description": "d"})
    fake.delete(CAL, "asv21")

    fake.patch_titulo(CAL, "asv21", "novo")

    evento = fake.get(CAL, "asv21")
    assert (evento["summary"], evento["description"], evento["status"]) == ("novo", "d", "cancelled")


class _Requisicao:
    def execute(self, num_retries: int = 0) -> dict[str, Any]:
        return {"id": "evt1"}


def _servico(chamadas: list[dict[str, Any]]) -> Any:
    class _Eventos:
        def patch(self, **params: Any) -> _Requisicao:
            chamadas.append(params)
            return _Requisicao()

    class _Servico:
        def events(self) -> _Eventos:
            return _Eventos()

    return _Servico()


def test_patch_titulo_oauth_manda_so_summary(settings):
    from apps.core.services.gcal_oauth_client import OAuthCalendarClient

    settings.GCAL_SEND_UPDATES = "all"
    chamadas: list[dict[str, Any]] = []
    cliente = OAuthCalendarClient.__new__(OAuthCalendarClient)
    cliente.service = _servico(chamadas)
    cliente.credential = SimpleNamespace(google_email="conta@example.com", user_id=7)

    cliente.patch_titulo("org@group.calendar.google.com", "evt1", "(CANCELADO) t")

    assert chamadas == [
        {
            "calendarId": "org@group.calendar.google.com",
            "eventId": "evt1",
            "body": {"summary": "(CANCELADO) t"},
            "sendUpdates": "none",
        }
    ]


def test_patch_titulo_service_account_manda_so_summary(settings):
    from apps.core.services.gcal_google_client import GoogleCalendarClient

    settings.GCAL_SEND_UPDATES = "all"
    chamadas: list[dict[str, Any]] = []
    cliente = GoogleCalendarClient.__new__(GoogleCalendarClient)
    cliente.service = _servico(chamadas)

    cliente.patch_titulo("cal", "evt1", "(CANCELADO) t")

    assert chamadas == [
        {"calendarId": "cal", "eventId": "evt1", "body": {"summary": "(CANCELADO) t"}, "sendUpdates": "none"}
    ]


# =============================================================================
# 13 a 15. A tarefa
# =============================================================================


def _pedir(s: Solicitacao) -> str:
    from apps.core.services.solicitacao_publish import pedir_operacao_gcal

    with transaction.atomic():
        return pedir_operacao_gcal(s.pk, "cancelar_na_agenda")


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
def test_tarefa_marca_e_volta_a_published(google):
    from apps.core.tasks import task_cancelar_na_agenda

    s = _formacao()
    _no_google(google, s)
    pedido = _pedir(s)

    resultado = task_cancelar_na_agenda(s.pk, pedido=pedido)

    assert resultado["action"] == "UPDATE"
    assert _titulo(google, s) == _MARCADO
    linha = _linha(s)
    assert (linha["gcal_status"], linha["gcal_payload_hash"], linha["cancelado_na_agenda"]) == (
        "PUBLISHED",
        _HASH,
        True,
    )
    assert linha["external_event_id"] == s.external_event_id
    registro = AuditLog.objects.get(action="CANCELAR_NA_AGENDA", details__solicitacao_id=s.pk)
    assert registro.usuario is None
    assert registro.details["pedido"] == pedido
    assert registro.details["resultado"] == "marcado"
    assert _TITULO not in str(registro.details), "o título pode ter nome de pessoa (LGPD)"


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
@pytest.mark.parametrize(
    ("preparo", "resultado_esperado"),
    [("ja_marcado", "ja_marcado"), ("ja_saiu", "ja_saiu")],
)
def test_tarefa_skip_tambem_volta_a_published(google, preparo, resultado_esperado):
    from apps.core.tasks import task_cancelar_na_agenda

    s = _formacao()
    if preparo == "ja_marcado":
        _no_google(google, s, _MARCADO)
    pedido = _pedir(s)

    task_cancelar_na_agenda(s.pk, pedido=pedido)

    assert _linha(s)["gcal_status"] == "PUBLISHED"
    registro = AuditLog.objects.get(action="CANCELAR_NA_AGENDA", details__solicitacao_id=s.pk)
    assert registro.details["resultado"] == resultado_esperado


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
def test_tarefa_id_adotado_apagado_no_google_volta_a_published(google):
    """Sem isso a linha ficava presa em ERROR "Erro ao cancelar", e refazer dava o mesmo erro."""
    from apps.core.tasks import task_cancelar_na_agenda

    s = _apagado_no_google(google, _formacao(external_event_id=_ADOTADO))
    pedido = _pedir(s)

    resultado = task_cancelar_na_agenda(s.pk, pedido=pedido)

    assert resultado["action"] == "SKIP"
    linha = _linha(s)
    assert (linha["gcal_status"], linha["cancelado_na_agenda"], linha["external_event_id"]) == (
        "PUBLISHED",
        True,
        _ADOTADO,
    )
    registro = AuditLog.objects.get(action="CANCELAR_NA_AGENDA", details__solicitacao_id=s.pk)
    assert registro.details["resultado"] == "ja_saiu"
    assert not AuditLog.objects.filter(action="PUBLISH_GCAL_ERROR", details__solicitacao_id=s.pk).exists()


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
def test_tarefa_entregue_de_novo_nao_marca_duas_vezes(google):
    from apps.core.tasks import task_cancelar_na_agenda

    s = _formacao()
    _no_google(google, s)
    pedido = _pedir(s)
    patches: list[str] = []
    original = FakeCalendarClient.patch_titulo
    google.patch_titulo = lambda *a: (patches.append("p"), original(google, *a))[1]

    task_cancelar_na_agenda(s.pk, pedido=pedido)
    task_cancelar_na_agenda(s.pk, pedido=pedido)

    assert patches == ["p"]
    assert _titulo(google, s) == _MARCADO

    # Queda entre o PATCH e o commit: a linha segue PENDING com o mesmo pedido e o título já marcado.
    Solicitacao.objects.filter(pk=s.pk).update(gcal_status="PENDING")
    task_cancelar_na_agenda(s.pk, pedido=pedido)

    assert patches == ["p"]
    assert _titulo(google, s) == _MARCADO
    assert _linha(s)["gcal_status"] == "PUBLISHED"


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
def test_tarefa_erro_marca_error_e_nao_enfileira_retry(google):
    from apps.core.services.gcal.circuit_breaker import CircuitBreakerError
    from apps.core.tasks import task_cancelar_na_agenda

    s = _formacao()
    _no_google(google, s)
    pedido = _pedir(s)

    def _disjuntor(*_a, **_k):
        raise CircuitBreakerError("aberto")

    google.patch_titulo = _disjuntor
    with (
        patch("apps.core.tasks.queue_gcal_sync_retry.apply_async") as retry,
        patch("apps.core.tasks.queue_gcal_sync_retry.delay") as retry_delay,
    ):
        resultado = task_cancelar_na_agenda(s.pk, pedido=pedido)

    assert resultado["action"] == "ERROR"
    retry.assert_not_called()
    retry_delay.assert_not_called()
    linha = _linha(s)
    assert (linha["gcal_status"], linha["cancelado_na_agenda"]) == ("ERROR", True)
    assert linha["external_event_id"] == s.external_event_id
    erro = AuditLog.objects.get(action="PUBLISH_GCAL_ERROR", details__solicitacao_id=s.pk)
    assert erro.details["operation"] == "cancelar_na_agenda"
    assert _titulo(google, s) == _TITULO


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
def test_tarefa_de_pedido_superado_nao_faz_nada(google):
    from apps.core.tasks import task_cancelar_na_agenda

    s = _formacao()
    _no_google(google, s)
    antigo = _pedir(s)
    novo = _pedir(s)
    antes = _linha(s)

    resultado = task_cancelar_na_agenda(s.pk, pedido=antigo)

    assert resultado["action"] == "SKIP"
    assert _linha(s) == antes
    assert _titulo(google, s) == _TITULO
    assert novo != antigo


# =============================================================================
# 16. Nenhum sync reescreve a linha marcada
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["aprovado", "reprovado"])
def test_upsert_one_recusa_linha_cancelada(google, status):
    from apps.core.services.gcal.sync import CriacaoRecusada, upsert_one

    s = _formacao(cancelado_na_agenda=True, status=status)
    _no_google(google, s, _MARCADO)
    contador = _Contador(google)

    with pytest.raises(CriacaoRecusada) as erro:
        upsert_one(client=contador, calendar_id=CAL, s=s)

    assert erro.value.code == "cancelado_na_agenda"
    assert contador.chamadas == []
    evento = google.get(CAL, s.external_event_id)
    assert (evento["summary"], evento["status"]) == (_MARCADO, "confirmed")


@pytest.mark.django_db
def test_preagenda_to_gcal_pula_linha_cancelada():
    s = _formacao(cancelado_na_agenda=True, gcal_payload_hash=None)
    escritas: list[str] = []
    for nome in ("insert", "update"):
        original = getattr(FakeCalendarClient, nome)

        def _conta(self, cal, eid, payload, _nome=nome, _original=original):
            escritas.append(f"{_nome}:{eid}")
            return _original(self, cal, eid, payload)

        patch.object(FakeCalendarClient, nome, _conta).start()
    try:
        call_command("preagenda_to_gcal", "--client", "fake", "--calendar-id", "cal", "--json")
    finally:
        patch.stopall()

    assert not [e for e in escritas if e.endswith(f"asv2{s.pk}")]


@pytest.mark.django_db
def test_queue_gcal_sync_retry_nao_reescreve_cancelada(google, settings):
    from apps.core.tasks import queue_gcal_sync_retry

    settings.GCAL_CLIENT = "fake"
    s = _formacao(cancelado_na_agenda=True, gcal_status="ERROR", gcal_payload_hash=None)
    _no_google(google, s, _MARCADO)

    with patch("apps.core.services.gcal.circuit_breaker.bloqueado_agora", return_value=False):
        try:
            queue_gcal_sync_retry.apply(args=(s.pk,), kwargs={"apply_blocked": True})
        except Exception:  # noqa: BLE001 — o que importa é o Google intacto
            pass

    evento = google.get(CAL, s.external_event_id)
    assert (evento["summary"], evento["status"]) == (_MARCADO, "confirmed")


# =============================================================================
# 18 e 19. Edição e painel de divergência
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize("gcal_status", ["PUBLISHED", "ERROR"])
def test_edicao_recusa_linha_cancelada(gcal_status):
    s = _formacao(cancelado_na_agenda=True, gcal_status=gcal_status)

    resposta = _api().patch(f"/api/solicitacoes/{s.pk}/", {"observacoes": "mudou"}, format="json")

    assert resposta.status_code == 400, resposta.data
    assert "Este evento foi cancelado na agenda: não se edita nem se publica de novo." in str(resposta.data)


@pytest.mark.django_db
def test_drift_ignora_linha_cancelada():
    marcada = _formacao(cancelado_na_agenda=True, gcal_payload_hash=None)
    normal = _formacao(gcal_payload_hash=None)

    resposta = _api().get("/api/gcal/drift/")

    assert resposta.status_code == 200, resposta.data
    ids = {item["id"] for item in resposta.data["items"]}
    assert normal.pk in ids
    assert marcada.pk not in ids


# =============================================================================
# 21. Endpoint e permissão
# =============================================================================


@pytest.fixture
def gerencia():
    return Gerencia.objects.create(nome="GERENCIA CANCELAR NA AGENDA", nome_setor="Fluir", ativo=True)


@pytest.fixture
def apoio(gerencia):
    user = UsuarioFactory(username="apoio_cancelar_agenda", cpf="64000000011")
    com_papel(user, "APOIO", gerencia)
    return user


def _da_gerencia(gerencia, **extra) -> Solicitacao:
    projeto = ProjetoFactory(nome=f"Projeto Cancelar {gerencia.pk}", fluxo="NAO_SUPER", gerencia=gerencia)
    return _formacao(projeto=projeto, municipio=MunicipioFactory(), **extra)


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
class TestEndpoint:
    def test_apoio_da_gerencia_pede_e_recebe_202(self, apoio, gerencia):
        s = _da_gerencia(gerencia, usuario=UsuarioFactory())

        with patch(_DELAY_CANCELAR_NA_AGENDA) as delay:
            delay.return_value.id = "tarefa-cancelar"
            resposta = _api(apoio).post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json")

        assert resposta.status_code == 202, resposta.data
        linha = _linha(s)
        assert (linha["gcal_status"], linha["cancelado_na_agenda"]) == ("PENDING", True)
        delay.assert_called_once()
        assert delay.call_args.args == (s.pk,)
        assert delay.call_args.kwargs["pedido"] == linha["gcal_pedido"]
        registro = AuditLog.objects.get(action="CANCELAR_NA_AGENDA_REQUESTED", details__solicitacao_id=s.pk)
        assert registro.usuario == apoio
        assert registro.details["pedido"] == linha["gcal_pedido"]
        assert registro.details["task_id"] == "tarefa-cancelar"
        assert "ip_address" in registro.details

    def test_quem_nao_pode_tirar_do_google_recebe_403(self, gerencia):
        formador = UsuarioFactory(username="formador_cancelar_agenda", cpf="64000000012")
        com_papel(formador, "FORMADOR", gerencia)
        s = _da_gerencia(gerencia, usuario=formador)

        with patch(_DELAY_CANCELAR_NA_AGENDA) as delay:
            resposta = _api(formador).post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json")

        assert resposta.status_code == 403, resposta.data
        delay.assert_not_called()
        assert _linha(s)["cancelado_na_agenda"] is False

    def test_apoio_de_outra_gerencia_recebe_404(self, apoio):
        outra = Gerencia.objects.create(nome="GERENCIA OUTRA CANCELAR", nome_setor="Vidas", ativo=True)
        s = _da_gerencia(outra, usuario=UsuarioFactory())

        with patch(_DELAY_CANCELAR_NA_AGENDA) as delay:
            resposta = _api(apoio).post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json")

        assert resposta.status_code == 404
        delay.assert_not_called()

    def test_sem_conta_google_no_modo_oauth_recebe_403(self, settings):
        settings.GCAL_AUTH_MODE = "oauth"
        s = _formacao()

        with patch(_DELAY_CANCELAR_NA_AGENDA) as delay:
            resposta = _api().post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json")

        assert resposta.status_code == 403
        assert resposta.data["code"] == "google_not_connected"
        delay.assert_not_called()
        assert _linha(s)["cancelado_na_agenda"] is False

    def test_evento_que_nao_e_de_formacao_recebe_409(self):
        s = _formacao(tipo="Reunião de Alinhamento")

        with patch(_DELAY_CANCELAR_NA_AGENDA) as delay:
            resposta = _api().post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json")

        assert resposta.status_code == 409
        assert resposta.data["errors"]["code"] == "nao_e_evento_de_formacao"
        delay.assert_not_called()


# =============================================================================
# 23. Excluir evento de formação que está no Google: marca e apaga
# =============================================================================


def _acoes(sol_id: int) -> list[str]:
    return [
        a.action
        for a in AuditLog.objects.filter(model_name="Solicitacao").order_by("id")
        if (a.details or {}).get("solicitacao_id") == sol_id
        or ((a.details or {}).get("solicitacao_data") or {}).get("id") == sol_id
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
class TestExcluir:
    def test_formacao_no_google_marca_e_apaga(self, apoio, gerencia, google):
        s = _da_gerencia(gerencia, usuario=apoio)
        _no_google(google, s)
        sol_id, eid = s.pk, s.external_event_id

        resposta = _api(apoio).delete(f"/api/solicitacoes/{sol_id}/")

        assert resposta.status_code == 204, resposta.data
        assert not Solicitacao.objects.filter(pk=sol_id).exists()
        evento = google.get(CAL, eid)
        assert (evento["summary"], evento["status"]) == (_MARCADO, "confirmed"), "fica no Google, cancelado"
        assert _acoes(sol_id) == ["CANCELAR_NA_AGENDA", "DELETE"]
        marca = AuditLog.objects.get(action="CANCELAR_NA_AGENDA", details__solicitacao_id=sol_id)
        assert marca.details["origem"] == "exclusao"
        assert marca.usuario == apoio
        delete = AuditLog.objects.get(action="DELETE", details__solicitacao_data__id=sol_id)
        assert delete.details["cancelado_na_agenda"] is True
        assert "removido_do_google" not in delete.details

    def test_formacao_em_error_sem_id_e_sem_evento_apaga(self, apoio, gerencia, google):
        s = _da_gerencia(gerencia, usuario=apoio, gcal_status="ERROR", external_event_id=None)
        sol_id = s.pk

        resposta = _api(apoio).delete(f"/api/solicitacoes/{sol_id}/")

        assert resposta.status_code == 204, resposta.data
        assert google.get(CAL, f"asv2{sol_id}") is None, "não cria evento"

    def test_falha_no_google_nao_marca_nem_apaga(self, apoio, gerencia, google):
        s = _da_gerencia(gerencia, usuario=apoio)
        _no_google(google, s)

        def _fora(*_a, **_k):
            raise RuntimeError("google fora")

        google.patch_titulo = _fora
        resposta = _api(apoio).delete(f"/api/solicitacoes/{s.pk}/")

        assert resposta.status_code == 400, resposta.data
        assert _linha(s)["cancelado_na_agenda"] is False
        assert _titulo(google, s) == _TITULO
        assert _acoes(s.pk) == []

    def test_formacao_com_id_adotado_apagado_no_google_apaga(self, apoio, gerencia, google):
        """Evento da virada apagado direto no Google (GET devolve `cancelled`): o Excluir apaga a linha."""
        s = _apagado_no_google(google, _da_gerencia(gerencia, usuario=apoio, external_event_id=_ADOTADO))
        sol_id = s.pk

        resposta = _api(apoio).delete(f"/api/solicitacoes/{sol_id}/")

        assert resposta.status_code == 204, resposta.data
        assert not Solicitacao.objects.filter(pk=sol_id).exists()
        evento = google.get(CAL, _ADOTADO)
        assert (evento["summary"], evento["status"]) == (_TITULO, "cancelled"), "não traz de volta nem marca"

    def test_formacao_com_id_adotado_nao_achado_recusa(self, apoio, gerencia, google):
        """Id adotado que o GET não acha (404): recusa e nada some, como o `upsert_one`. Escolha em aberto com o dono
        (revisão da rodada 1): manter a recusa ou apagar a linha com o aviso de que o evento não foi achado."""
        s = _da_gerencia(gerencia, usuario=apoio, external_event_id=_ADOTADO)

        resposta = _api(apoio).delete(f"/api/solicitacoes/{s.pk}/")

        assert resposta.status_code == 400, resposta.data
        assert _linha(s)["cancelado_na_agenda"] is False
        assert _acoes(s.pk) == []

    def test_nao_formacao_segue_tirando_do_google(self, apoio, gerencia, google):
        s = _da_gerencia(gerencia, usuario=apoio)
        s.tipo_evento = TipoEventoFactory(nome="Reunião de Alinhamento")
        s.save(update_fields=["tipo_evento"])
        _no_google(google, s)

        resposta = _api(apoio).delete(f"/api/solicitacoes/{s.pk}/")

        assert resposta.status_code == 204, resposta.data
        assert google.get(CAL, f"asv2{s.pk}")["status"] == "cancelled"
        assert _titulo(google, s) == _TITULO

    def test_texto_do_motivo_que_impede_excluir_ramifica_pela_formacao(self):
        from apps.core.services.solicitacao_exclusao import motivo_que_impede_excluir

        formacao = _formacao()
        outro = _formacao(tipo="Reunião de Alinhamento")

        texto_formacao = motivo_que_impede_excluir(formacao, ja_decidida=False, pode_tirar_do_google=False)
        texto_outro = motivo_que_impede_excluir(outro, ja_decidida=False, pode_tirar_do_google=False)

        assert texto_formacao is not None and texto_outro is not None
        assert "(CANCELADO)" in texto_formacao and "tiraria de lá" not in texto_formacao
        assert "tiraria de lá" in texto_outro


# =============================================================================
# 24. Serializer, linha do tempo e importer
# =============================================================================


@pytest.mark.django_db
def test_o_campo_vem_na_lista():
    marcada = _formacao(cancelado_na_agenda=True)
    normal = _formacao()

    resposta = _api().get("/api/solicitacoes/", {"page_size": 100})

    assert resposta.status_code == 200, resposta.data
    itens = resposta.data["results"] if isinstance(resposta.data, dict) else resposta.data
    por_id = {item["id"]: item for item in itens}
    assert por_id[marcada.pk]["cancelado_na_agenda"] is True
    assert por_id[normal.pk]["cancelado_na_agenda"] is False


@pytest.mark.django_db
def test_o_campo_e_so_leitura_na_edicao():
    """Na linha NÃO marcada (a marcada já recusa toda edição): o PATCH passa, mas a marca não entra por ele."""
    s = _formacao(gcal_status="NONE", external_event_id=None, gcal_payload_hash=None)

    resposta = _api().patch(
        f"/api/solicitacoes/{s.pk}/", {"cancelado_na_agenda": True, "observacoes": "x"}, format="json"
    )

    assert resposta.status_code == 200, resposta.data
    s.refresh_from_db()
    assert (s.observacoes, s.cancelado_na_agenda) == ("x", False)


def test_acoes_novas_na_auditoria_linha_do_tempo_e_importer():
    from apps.core.services import export_contract_importer as importer

    assert AuditLog.Action.CANCELAR_NA_AGENDA_REQUESTED == "CANCELAR_NA_AGENDA_REQUESTED"
    assert AuditLog.Action.CANCELAR_NA_AGENDA == "CANCELAR_NA_AGENDA"
    assert "CANCELAR_NA_AGENDA_REQUESTED" in importer._ACOES_DE_PESSOA
    assert "CANCELAR_NA_AGENDA" in importer._ACOES_SEM_TRAVA


@pytest.mark.django_db
def test_linha_do_tempo_mostra_as_acoes_novas():
    from apps.core.serializers.solicitacao import EventDetailSerializer

    s = _formacao()
    for acao in ("CANCELAR_NA_AGENDA_REQUESTED", "CANCELAR_NA_AGENDA"):
        AuditLog.objects.create(action=acao, model_name="Solicitacao", details={"solicitacao_id": s.pk})

    acoes = {item["action"] for item in EventDetailSerializer().get_timeline(s)}

    assert {"CANCELAR_NA_AGENDA_REQUESTED", "CANCELAR_NA_AGENDA"} <= acoes


# =============================================================================
# 20. Corridas reais: duas conexões, banco de verdade
# =============================================================================


def _esperar_alguem_esperando_trava(quem: str, timeout: float = 15.0) -> None:
    limite = time.monotonic() + timeout
    with connection.cursor() as cursor:
        while time.monotonic() < limite:
            cursor.execute("""
                SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()
                """)
            if cursor.fetchone()[0]:
                return
            time.sleep(0.02)
    pytest.fail(f"{quem} não chegou a esperar a trava da linha")


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("modo_google")
def test_corrida_publicar_segura_a_linha_e_cancelar_espera():
    """A tarefa de publicar segura a trava: o pedido de cancelar espera, e depois marca a linha."""
    s = _formacao()
    api = _api()
    travou, liberar = threading.Event(), threading.Event()

    def tarefa_que_segura():
        try:
            with transaction.atomic():
                Solicitacao.objects.select_for_update().get(pk=s.pk)
                travou.set()
                liberar.wait(timeout=30)
        finally:
            connection.close()

    def cancelar():
        try:
            return api.post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json")
        finally:
            connection.close()

    with patch(_DELAY_CANCELAR_NA_AGENDA) as delay, ThreadPoolExecutor(max_workers=2) as executor:
        delay.return_value.id = "tarefa"
        segura = executor.submit(tarefa_que_segura)
        futuro = None
        try:
            assert travou.wait(timeout=15)
            futuro = executor.submit(cancelar)
            _esperar_alguem_esperando_trava("o pedido de cancelar")
        finally:
            liberar.set()
        segura.result(timeout=30)
        assert futuro is not None
        resposta = futuro.result(timeout=30)

    assert resposta.status_code == 202, resposta.data
    assert _linha(s)["cancelado_na_agenda"] is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("modo_google")
def test_corrida_cancelar_primeiro_e_publicar_recusado(monkeypatch):
    from apps.core.tasks import task_cancelar_na_agenda

    fake = FakeCalendarClient()
    monkeypatch.setattr(_FABRICA, lambda: (fake, CAL))
    monkeypatch.setattr("apps.core.services.gcal.sync._retry_with_circuit_breaker", lambda f, **_: f())
    s = _formacao(gcal_status="ERROR")
    _no_google(fake, s)
    api = _api()

    with patch(_DELAY_CANCELAR_NA_AGENDA) as delay:
        delay.return_value.id = "tarefa"
        assert api.post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json").status_code == 202
    pedido = _linha(s)["gcal_pedido"]

    with patch(_DELAY_PUBLICAR) as publicar:
        em_voo = api.post(f"/api/solicitacoes/{s.pk}/publish/", {}, format="json")
        task_cancelar_na_agenda(s.pk, pedido=pedido)
        depois = api.post(f"/api/solicitacoes/{s.pk}/resync-gcal/", {}, format="json")

    assert (em_voo.status_code, em_voo.data["code"]) == (400, "cancelado_na_agenda")
    assert (depois.status_code, depois.data["code"]) == (400, "cancelado_na_agenda")
    publicar.assert_not_called()
    assert _titulo(fake, s) == _MARCADO


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("modo_google")
def test_corrida_excluir_e_cancelar_marca_uma_vez_e_a_linha_some(monkeypatch):
    """O Excluir segura a linha enquanto marca o título; o pedido de Cancelar espera e entra entre o remover e o
    delete. O delete aceita a linha marcada, e a tarefa do Cancelar acha a linha apagada: título marcado uma vez."""
    from apps.core.tasks import task_cancelar_na_agenda

    fake = FakeCalendarClient()
    monkeypatch.setattr(_FABRICA, lambda: (fake, CAL))
    monkeypatch.setattr("apps.core.services.gcal.sync._retry_with_circuit_breaker", lambda f, **_: f())
    s = _formacao()
    _no_google(fake, s)
    api = _api()
    travou, liberar = threading.Event(), threading.Event()
    original = FakeCalendarClient.patch_titulo

    def patch_que_espera(cal, eid, titulo):
        travou.set()
        liberar.wait(timeout=30)
        return original(fake, cal, eid, titulo)

    fake.patch_titulo = patch_que_espera

    def excluir():
        try:
            return api.delete(f"/api/solicitacoes/{s.pk}/")
        finally:
            connection.close()

    def cancelar():
        try:
            return api.post(f"/api/solicitacoes/{s.pk}/cancelar-na-agenda/", {}, format="json")
        finally:
            connection.close()

    with patch(_DELAY_CANCELAR_NA_AGENDA) as delay, ThreadPoolExecutor(max_workers=2) as executor:
        delay.return_value.id = "tarefa"
        futuro_excluir = executor.submit(excluir)
        futuro_cancelar = None
        try:
            assert travou.wait(timeout=15), "o Excluir não chegou ao Google"
            futuro_cancelar = executor.submit(cancelar)
            _esperar_alguem_esperando_trava("o pedido de cancelar")
        finally:
            liberar.set()
        excluiu = futuro_excluir.result(timeout=30)
        assert futuro_cancelar is not None
        cancelou = futuro_cancelar.result(timeout=30)

    assert excluiu.status_code == 204, excluiu.data
    assert cancelou.status_code == 202, cancelou.data
    pedido = delay.call_args.kwargs["pedido"]
    resultado = task_cancelar_na_agenda(s.pk, pedido=pedido)
    assert resultado["error"] == "DoesNotExist"
    assert not Solicitacao.objects.filter(pk=s.pk).exists()
    assert _titulo(fake, s) == _MARCADO


# =============================================================================
# Pedido do serviço de entrada (fora da API)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.usefixtures("modo_google")
def test_servico_de_entrada_recusa_sem_formacao_antes_de_enfileirar():
    from apps.core.services.solicitacao_publish import cancelar_na_agenda

    s = _formacao(tipo="Reunião de Alinhamento")

    with patch(_DELAY_CANCELAR_NA_AGENDA) as delay, pytest.raises(ConflictError):
        cancelar_na_agenda(s, UsuarioFactory(), RequestFactory().post("/x/"))

    delay.assert_not_called()
