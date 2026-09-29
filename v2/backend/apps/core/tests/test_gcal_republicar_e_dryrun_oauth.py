"""Republicar depois de remover e dry-run no modo OAuth (#1656, smoke em produção de 28/09).

1. Publicar → remover → publicar de novo deixava o evento OCULTO. O DELETE do Google é soft-delete:
   o evento fica `status=cancelled` e o GET pelo id determinístico (`asv2{id}`) ainda o devolve. O
   segundo publish o adotava (ADOPT → PATCH) e marcava PUBLISHED, mas o payload não mandava `status`,
   então o PATCH não "descancelava" e o evento seguia invisível no calendário.
2. O dry-run no modo OAuth pulava o cliente do operador e caía na service account, que não existe em
   produção ("Service Account credentials not found"). No dry-run a falha ainda gravava ERROR numa
   linha que ninguém marcou PENDING.

A borda falsa é o `service` do Google por trás do OAuthCalendarClient real. A maioria dos testes
entrega esse cliente pela fábrica; o da credencial do operador monta o cliente de verdade a partir do
banco e só troca o `build` do googleapiclient.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportMissingTypeStubs=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone

import pytest
from googleapiclient.errors import HttpError

from apps.core.models import AuditLog, GoogleOAuthCredential, Solicitacao
from apps.core.services.gcal.payload import build_event_payload
from apps.core.services.gcal_oauth_client import OAuthCalendarClient
from apps.core.services.google_oauth import _encrypt_token
from apps.core.tasks import (
    _MSG_SEM_ACESSO_CALENDARIO,
    task_cancel_solicitacao_from_gcal,
    task_publish_solicitacao_to_gcal,
)
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

ORG = "org-formacoes@group.calendar.google.com"
OAUTH = override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID=ORG)
FABRICA_OAUTH = "apps.core.services.gcal_client_factory.get_oauth_client_for_user"
FABRICA_SERVICE_ACCOUNT = "apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id"
CAMPOS_GCAL = (
    "gcal_status",
    "gcal_payload_hash",
    "gcal_last_error",
    "gcal_last_sync_at",
    "external_event_id",
    "last_synced_at",
    "last_sync_action",
    "last_sync_error",
    "meet_link",
)


def _http_error(codigo: int) -> HttpError:
    return HttpError(resp=Mock(status=codigo, reason="x"), content=b'{"error": {"message": "x"}}')


class _Chamada:
    def __init__(self, funcao):
        self._funcao = funcao

    def execute(self):
        return self._funcao()


class _EventosGoogle:
    """`events()` do Google em memória, com a semântica de que o bug depende.

    - delete é soft-delete: o evento fica `status=cancelled` e o get AINDA o devolve;
    - patch troca só os campos enviados (sem `status` no corpo, o cancelado continua cancelado);
    - insert de um id que já existe (mesmo cancelado) é 409.

    `erro_no_get` faz só o get falhar com esse código (403 de cota, 5xx); `sem_acesso` faz toda
    operação responder 403, como para uma conta que não vê o calendário.
    """

    def __init__(self):
        self.eventos: dict[str, dict] = {}
        self.escritas: list[str] = []
        self.erro_no_get: int | None = None
        self.sem_acesso = False

    def _checar_acesso(self):
        if self.sem_acesso:
            raise _http_error(403)

    def get(self, calendarId, eventId):
        def _get():
            self._checar_acesso()
            if self.erro_no_get:
                raise _http_error(self.erro_no_get)
            if eventId not in self.eventos:
                raise _http_error(404)
            return dict(self.eventos[eventId])

        return _Chamada(_get)

    def insert(self, calendarId, body, **_kwargs):
        def _insert():
            self._checar_acesso()
            self.escritas.append("insert")
            if body["id"] in self.eventos:
                raise _http_error(409)
            self.eventos[body["id"]] = {"status": "confirmed", **body}
            return dict(self.eventos[body["id"]])

        return _Chamada(_insert)

    def patch(self, calendarId, eventId, body, **_kwargs):
        def _patch():
            self._checar_acesso()
            self.escritas.append("patch")
            if eventId not in self.eventos:
                raise _http_error(404)
            self.eventos[eventId].update(body)
            return dict(self.eventos[eventId])

        return _Chamada(_patch)

    def delete(self, calendarId, eventId, **_kwargs):
        def _delete():
            self._checar_acesso()
            self.escritas.append("delete")
            if eventId not in self.eventos:
                raise _http_error(404)
            self.eventos[eventId]["status"] = "cancelled"

        return _Chamada(_delete)


class _ServiceGoogle:
    """`sem_acesso`: a conta não vê o calendário da organização (o Google responde 403 a tudo).

    `calendarios_consultados` guarda os ids passados a `calendars().get`, para provar QUAL calendário a
    checagem de acesso olhou (o da organização, não o pessoal da conta).
    """

    def __init__(self, sem_acesso: bool = False):
        self.eventos_api = _EventosGoogle()
        self.sem_acesso = sem_acesso
        self.eventos_api.sem_acesso = sem_acesso
        self.calendarios_consultados: list[str] = []

    def events(self):
        return self.eventos_api

    def calendars(self):
        def _get_calendario(calendarId):
            self.calendarios_consultados.append(calendarId)
            if self.sem_acesso:
                raise _http_error(403)
            return {"id": calendarId}

        return SimpleNamespace(get=lambda calendarId: _Chamada(lambda: _get_calendario(calendarId)))


def _cliente_oauth(service: _ServiceGoogle) -> OAuthCalendarClient:
    """OAuthCalendarClient real, sem __init__ (nada de refresh/rede), sobre o `service` falso."""
    cliente = OAuthCalendarClient.__new__(OAuthCalendarClient)
    cliente.credential = SimpleNamespace(
        google_email="operador@aprendereditora.com.br",
        default_calendar_id="",
        user_id=1,
        user=SimpleNamespace(is_authenticated=True, is_superuser=True),
    )
    cliente.service = service
    return cliente


def _estado_gcal(sol: Solicitacao) -> dict:
    sol.refresh_from_db()
    return {campo: getattr(sol, campo) for campo in CAMPOS_GCAL}


def _audits_gcal(sol: Solicitacao) -> int:
    return AuditLog.objects.filter(
        action__in=[AuditLog.Action.PUBLISH_GCAL, AuditLog.Action.PUBLISH_GCAL_ERROR],
        details__solicitacao_id=sol.id,
    ).count()


def _linha_publicada() -> Solicitacao:
    """Linha já PUBLISHED: um ERROR gravado por uma prévia apareceria nela."""
    sol = SolicitacaoFactory(status="aprovado", external_event_id="asv2publicado")
    sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    sol.save(update_fields=["gcal_status"])
    return sol


def _credencial(usuario, access_token: str) -> GoogleOAuthCredential:
    """Credencial real no banco, com token válido por 1 h (o cliente não faz refresh)."""
    return GoogleOAuthCredential.objects.create(
        user=usuario,
        google_email=f"{usuario.username}@example.invalid",
        access_token_encrypted=_encrypt_token(access_token),
        refresh_token_encrypted=_encrypt_token(f"refresh-{access_token}"),
        token_expiry=timezone.now() + timedelta(hours=1),
    )


# ---------------------------------------------------------------------------
# 1. Republicar depois de remover volta a `confirmed`
# ---------------------------------------------------------------------------


def test_payload_de_publicacao_manda_status_confirmed():
    """O PATCH só "descancela" um evento removido se o corpo trouxer o status."""
    sol = SolicitacaoFactory(status="aprovado")

    assert build_event_payload(sol)["status"] == "confirmed"
    assert build_event_payload(sol, enable_meet=True)["status"] == "confirmed"


@OAUTH
def test_publicar_remover_publicar_de_novo_deixa_o_evento_visivel():
    operador = UsuarioFactory()
    service = _ServiceGoogle()
    sol = SolicitacaoFactory(status="aprovado")
    event_id = f"asv2{sol.id}"

    with patch(FABRICA_OAUTH, return_value=(_cliente_oauth(service), ORG)):
        publicado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)
        assert publicado["action"] == "CREATE"
        assert service.eventos_api.eventos[event_id]["status"] == "confirmed"

        removido = task_cancel_solicitacao_from_gcal(sol.id, operator_user_id=operador.pk)
        assert removido["action"] == "DELETE"
        assert service.eventos_api.eventos[event_id]["status"] == "cancelled"  # soft-delete, como o Google

        republicado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    assert republicado["action"] == "ADOPT"  # o id determinístico ainda existe (cancelado) no Google
    assert service.eventos_api.eventos[event_id]["status"] == "confirmed"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert sol.external_event_id == event_id


@OAUTH
@pytest.mark.parametrize(("caso", "acao_esperada"), [("removido", "ADOPT"), ("editado", "UPDATE")])
def test_republicar_com_o_get_falhando_ainda_aplica_o_payload(caso, acao_esperada):
    """GET que falha sem ser 404 (403 de cota, 5xx, rede) vira CREATE; o insert de um id que já existe
    (mesmo cancelado) volta 409, tratado como sucesso. Sem o PATCH depois do 409, a linha virava
    PUBLISHED com o Google desatualizado: o evento removido seguia cancelado (oculto) e o editado
    seguia com o horário antigo."""
    operador = UsuarioFactory()
    service = _ServiceGoogle()
    sol = SolicitacaoFactory(status="aprovado")
    event_id = f"asv2{sol.id}"

    with patch(FABRICA_OAUTH, return_value=(_cliente_oauth(service), ORG)):
        task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)
        if caso == "removido":
            task_cancel_solicitacao_from_gcal(sol.id, operator_user_id=operador.pk)
        else:
            sol.refresh_from_db()
            sol.fim = sol.fim + timedelta(hours=1)
            sol.save(update_fields=["fim"])
        service.eventos_api.erro_no_get = 403
        republicado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    assert republicado["error"] is None, republicado
    assert republicado["action"] == acao_esperada
    assert service.eventos_api.escritas[-1] == "patch"
    evento = service.eventos_api.eventos[event_id]
    assert evento["status"] == "confirmed"
    sol.refresh_from_db()
    assert evento["end"] == build_event_payload(sol)["end"]
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert sol.external_event_id == event_id


@OAUTH
def test_republicar_sem_mudanca_com_o_get_falhando_nao_manda_patch():
    """#1722: linha publicada com o mesmo payload não gera PATCH (nem e-mail de "atualizado"), também
    quando o GET falha e o insert volta 409 (ex.: "Reaplicar" em lote, que não zera o hash)."""
    operador = UsuarioFactory()
    service = _ServiceGoogle()
    sol = SolicitacaoFactory(status="aprovado")

    with patch(FABRICA_OAUTH, return_value=(_cliente_oauth(service), ORG)):
        task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)
        service.eventos_api.erro_no_get = 403
        de_novo = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    assert de_novo["action"] == "SKIP"
    assert "patch" not in service.eventos_api.escritas
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED


# ---------------------------------------------------------------------------
# 2. Dry-run no modo OAuth usa o cliente do operador e não mexe na Solicitacao
# ---------------------------------------------------------------------------


@OAUTH
def test_dry_run_oauth_monta_o_cliente_com_a_credencial_do_operador(monkeypatch):
    """A fábrica e o cliente são reais: prova que a prévia usa a credencial DO OPERADOR."""
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "client-id-teste")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "client-secret-teste")
    operador = UsuarioFactory()
    _credencial(operador, "token-do-operador")
    _credencial(UsuarioFactory(), "token-de-outro")  # a prévia não pode pegar credencial emprestada
    service = _ServiceGoogle()
    tokens_usados: list[str] = []

    def _build(*_args, http, **_kwargs):
        tokens_usados.append(http.credentials.token)
        return service

    sol = SolicitacaoFactory(status="aprovado")
    antes = _estado_gcal(sol)

    with (
        patch("apps.core.services.gcal_oauth_client.build", side_effect=_build),
        patch(FABRICA_SERVICE_ACCOUNT) as fabrica_service_account,
    ):
        resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=operador.pk)

    assert resultado["error"] is None, resultado
    assert resultado["action"] == "CREATE"  # a prévia: o evento ainda não existe no calendário
    assert tokens_usados == ["token-do-operador"]
    assert service.calendarios_consultados == [ORG]  # a checagem de acesso olhou o calendário da organização
    fabrica_service_account.assert_not_called()
    assert service.eventos_api.escritas == []  # dry-run lê o Google, não escreve
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0


@OAUTH
@pytest.mark.parametrize("dry_run", [True, False], ids=["previa", "publicacao"])
def test_operador_sem_acesso_ao_calendario_da_erro_na_previa_e_na_publicacao(dry_run):
    """A prévia não pode dar verde para quem a publicação real recusa (403 do Google)."""
    operador = UsuarioFactory()
    service = _ServiceGoogle(sem_acesso=True)
    sol = SolicitacaoFactory(status="aprovado")
    antes = _estado_gcal(sol)

    with patch(FABRICA_OAUTH, return_value=(_cliente_oauth(service), ORG)):
        resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=dry_run, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    if dry_run:
        assert "acesso ao calendário" in resultado["error"]
        assert service.calendarios_consultados == [ORG]
        assert _estado_gcal(sol) == antes
        assert _audits_gcal(sol) == 0
    else:
        assert service.calendarios_consultados == []  # a checagem é só da prévia; aqui o 403 vem do insert
        sol.refresh_from_db()
        assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
        assert sol.gcal_last_error == _MSG_SEM_ACESSO_CALENDARIO


@OAUTH
@pytest.mark.parametrize("dry_run", [True, False], ids=["previa", "publicacao"])
def test_so_a_publicacao_real_trava_a_linha_da_solicitacao(dry_run):
    """A prévia não escreve na linha e faz até 3 chamadas ao Google: com o lock preso, um publish, cancel
    ou edição real da mesma linha esperaria por uma simulação."""
    from django.db.models import QuerySet

    operador = UsuarioFactory()
    sol = SolicitacaoFactory(status="aprovado")
    original = QuerySet.select_for_update

    with (
        patch(FABRICA_OAUTH, return_value=(_cliente_oauth(_ServiceGoogle()), ORG)),
        patch.object(QuerySet, "select_for_update", autospec=True, side_effect=original) as travas,
    ):
        task_publish_solicitacao_to_gcal(sol.id, dry_run=dry_run, operator_user_id=operador.pk)

    travou_a_linha = any(chamada.args[0].model is Solicitacao for chamada in travas.call_args_list)
    assert travou_a_linha is not dry_run


@OAUTH
def test_dry_run_oauth_sem_operador_devolve_erro_sem_gravar_error():
    sol = _linha_publicada()
    antes = _estado_gcal(sol)

    resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True)

    assert resultado["action"] == "ERROR"
    assert resultado["error"] == "missing_operator_user_id"
    assert _estado_gcal(sol) == antes  # a linha publicada não vira ERROR por causa de uma prévia
    assert _audits_gcal(sol) == 0


@OAUTH
def test_dry_run_oauth_operador_inexistente_devolve_erro_sem_gravar_error():
    sol = _linha_publicada()
    antes = _estado_gcal(sol)

    resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=999_999_999)

    assert resultado["action"] == "ERROR"
    assert resultado["error"] == "operator_not_found"
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0


@OAUTH
def test_dry_run_oauth_sem_credencial_devolve_erro_sem_gravar_error():
    operador = UsuarioFactory()  # sem GoogleOAuthCredential
    _credencial(UsuarioFactory(), "token-de-outro")  # a de outro usuário não serve
    sol = _linha_publicada()
    antes = _estado_gcal(sol)

    resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    assert resultado["error"] == "oauth_credential_missing"
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0


@OAUTH
def test_dry_run_oauth_com_erro_de_rede_no_cliente_devolve_erro_sem_gravar_error():
    """O refresh do token levanta Exception genérica em erro de rede (token_manager)."""
    operador = UsuarioFactory()
    sol = _linha_publicada()
    antes = _estado_gcal(sol)

    with patch(FABRICA_OAUTH, side_effect=Exception("falha de rede no refresh")):
        resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    assert resultado["error"] == "oauth_client_error"
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID="")
def test_dry_run_com_falha_na_publicacao_devolve_erro_sem_gravar_error():
    """A saída de erro genérica da task também respeita o dry-run (antes marcava ERROR mesmo assim)."""
    operador = UsuarioFactory()
    sol = _linha_publicada()
    antes = _estado_gcal(sol)

    # Sem pino e sem escolha na credencial: o cliente recusa resolver o calendário (falha fechada).
    with patch(FABRICA_OAUTH, return_value=(_cliente_oauth(_ServiceGoogle()), "")):
        resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    assert "não configurado" in resultado["error"]
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0
