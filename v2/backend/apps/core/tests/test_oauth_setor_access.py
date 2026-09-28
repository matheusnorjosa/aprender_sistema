"""A Apoio de Coordenação conecta a PRÓPRIA conta Google (#1656).

Os 7 endpoints OAuth eram só `CanUseGcal` (global). A Apoio — que publica os eventos do setor
(`publish_setor_solicitacao`, #2043) — não conseguia conectar a conta, então todo publish dela dava
403 `google_not_connected`. Abrem para ela só os 4 que agem sobre a credencial da própria pessoa
(start, callback, status, disconnect). `events`, `calendars` e `select-calendar` seguem fechados: o
calendário de publicação é o da organização, decidido no servidor.

Também: o retorno do OAuth leva a pessoa a uma página que ela consegue abrir (a Apoio não abre
/pre-agenda), quem não tem setor vigente não recebe token (M12-15), e o `status` diz se a pessoa
já pode publicar (`publish_ready` / `publish_block_reason`).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core import views_oauth
from apps.core.models import EquipeGerencia, Gerencia, GoogleOAuthCredential
from apps.core.rbac.policies import CanPublishSetorSolicitacao, CanUseGcal
from apps.core.services.oauth.oauth_flow import _is_safe_url
from apps.core.services.oauth.token_manager import encrypt_token
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

PAGINA_PUBLICACAO = "/solicitacoes/publicacao"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth?client_id=teste"
ORG = "org-formacoes@group.calendar.google.com"
TOKENS = {
    "email": "apoio@aprendereditora.com.br",
    "access_token": "acesso",
    "refresh_token": "refresh",
    "expires_in": 3600,
    "scope": "https://www.googleapis.com/auth/calendar",
}


@pytest.fixture
def gerencia_fluir():
    return Gerencia.objects.create(nome="GERENCIA 3 OAS", nome_setor="Fluir", setor_canonico="Fluir", ativo=True)


def _apoio(gerencia=None):
    user = UsuarioFactory()
    user.groups.add(GroupFactory(name="Apoio de Coordenação"))
    if gerencia is not None:
        EquipeGerencia.objects.create(usuario=user, gerencia=gerencia, papel="APOIO")
    return user


def _controle():
    user = UsuarioFactory()
    user.groups.add(GroupFactory(name="Controle"))
    return user


@pytest.fixture
def apoio_fluir(gerencia_fluir):
    return _apoio(gerencia_fluir)


def _cliente(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _conectar(user, default_calendar_id=""):
    return GoogleOAuthCredential.objects.create(
        user=user,
        google_email="conta@aprendereditora.com.br",
        access_token_encrypted=encrypt_token("acesso"),
        refresh_token_encrypted=encrypt_token("refresh"),
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id=default_calendar_id,
    )


# ---------------------------------------------------------------------------
# A. start
# ---------------------------------------------------------------------------


@patch("apps.core.views_oauth.build_authorization_url", return_value=GOOGLE_AUTH_URL)
def test_apoio_start_redireciona_ao_google(mock_build, apoio_fluir):
    resp = _cliente(apoio_fluir).get("/api/oauth/google/start/", {"return_to": PAGINA_PUBLICACAO})

    assert resp.status_code == status.HTTP_302_FOUND
    assert resp.url == GOOGLE_AUTH_URL
    assert mock_build.call_args.kwargs["return_to"] == PAGINA_PUBLICACAO


@patch("apps.core.views_oauth.build_authorization_url", return_value=GOOGLE_AUTH_URL)
def test_apoio_start_sem_return_to_grava_pagina_de_publicacao_no_state(mock_build, apoio_fluir):
    _cliente(apoio_fluir).get("/api/oauth/google/start/")

    assert mock_build.call_args.kwargs["return_to"] == PAGINA_PUBLICACAO


@patch("apps.core.views_oauth.build_authorization_url", return_value=GOOGLE_AUTH_URL)
def test_controle_start_sem_return_to_continua_em_pre_agenda(mock_build):
    """Guarda: para quem tem use_gcal nada muda — o retorno padrão segue /pre-agenda."""
    _cliente(_controle()).get("/api/oauth/google/start/")

    assert mock_build.call_args.kwargs["return_to"] == "/pre-agenda"


@patch("apps.core.views_oauth.build_authorization_url", return_value=GOOGLE_AUTH_URL)
def test_apoio_sem_setor_start_403_no_setor_scope(mock_build):
    """M12-15: quem não pode publicar nada (Apoio sem vínculo vigente) não recebe token Google."""
    resp = _cliente(_apoio(None)).get("/api/oauth/google/start/")

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.data["code"] == "no_setor_scope"
    mock_build.assert_not_called()


# ---------------------------------------------------------------------------
# B. callback
# ---------------------------------------------------------------------------


@patch("apps.core.views_oauth.exchange_code_for_tokens", return_value=TOKENS)
@patch("apps.core.services.google_oauth.validate_oauth_state")
def test_apoio_callback_cria_credencial_e_volta_para_return_to(mock_validate, _mock_exchange, apoio_fluir):
    mock_validate.return_value = {"valid": True, "return_to": PAGINA_PUBLICACAO, "user_id": apoio_fluir.pk}

    resp = _cliente(apoio_fluir).get("/api/oauth/google/callback/", {"code": "c", "state": "s"})

    assert resp.status_code == status.HTTP_302_FOUND
    assert PAGINA_PUBLICACAO in resp.url
    assert "google=connected" in resp.url
    credencial = GoogleOAuthCredential.objects.get(user=apoio_fluir)
    assert not credencial.default_calendar_id  # o calendário é o da organização, não escolha dela


@patch("apps.core.views_oauth.exchange_code_for_tokens")
def test_apoio_callback_erro_do_google_volta_para_pagina_de_publicacao(mock_exchange, apoio_fluir):
    resp = _cliente(apoio_fluir).get("/api/oauth/google/callback/", {"error": "access_denied"})

    assert resp.status_code == status.HTTP_302_FOUND
    assert PAGINA_PUBLICACAO in resp.url
    assert "google=error" in resp.url
    assert "access_denied" in resp.url
    mock_exchange.assert_not_called()


@patch("apps.core.services.google_oauth.validate_oauth_state", return_value={"valid": False, "error": "x"})
def test_apoio_callback_state_invalido_volta_para_pagina_de_publicacao(_mock_validate, apoio_fluir):
    resp = _cliente(apoio_fluir).get("/api/oauth/google/callback/", {"code": "c", "state": "s"})

    assert resp.status_code == status.HTTP_302_FOUND
    assert PAGINA_PUBLICACAO in resp.url
    assert "invalid_state" in resp.url


@patch("apps.core.views_oauth.exchange_code_for_tokens", return_value=TOKENS)
@patch("apps.core.services.google_oauth.validate_oauth_state")
def test_apoio_sem_setor_callback_nao_grava_credencial(mock_validate, mock_exchange):
    """M12-15: o vínculo pode vencer entre o start e o callback (o state vive 10 min) — sem setor, sem token."""
    apoio = _apoio(None)
    mock_validate.return_value = {"valid": True, "return_to": PAGINA_PUBLICACAO, "user_id": apoio.pk}

    resp = _cliente(apoio).get("/api/oauth/google/callback/", {"code": "c", "state": "s"})

    assert resp.status_code == status.HTTP_302_FOUND
    assert "reason=no_setor_scope" in resp.url
    mock_exchange.assert_not_called()
    assert not GoogleOAuthCredential.objects.filter(user=apoio).exists()


@patch("apps.core.views_oauth.exchange_code_for_tokens")
def test_controle_callback_erro_continua_em_pre_agenda(_mock_exchange):
    resp = _cliente(_controle()).get("/api/oauth/google/callback/", {"error": "access_denied"})

    assert resp.status_code == status.HTTP_302_FOUND
    assert "/pre-agenda" in resp.url


# ---------------------------------------------------------------------------
# C. status + disconnect
# ---------------------------------------------------------------------------


@patch("apps.core.services.oauth.token_manager.requests.post", return_value=Mock(status_code=200))
def test_apoio_status_e_disconnect_200(_mock_google_revoke, apoio_fluir, settings):
    """O revoke real roda (só a chamada HTTP ao Google é simulada) e apaga a credencial do usuário."""
    settings.GCAL_AUTH_MODE = "oauth"
    settings.GCAL_OAUTH_CALENDAR_ID = ORG
    _conectar(apoio_fluir)
    client = _cliente(apoio_fluir)

    status_resp = client.get("/api/integrations/google/status/")
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.data["connected"] is True
    assert status_resp.data["publish_ready"] is True

    desconectar = client.post("/api/integrations/google/disconnect/")
    assert desconectar.status_code == status.HTTP_200_OK
    assert not GoogleOAuthCredential.objects.filter(user=apoio_fluir).exists()


def test_apoio_sem_pino_nao_usa_calendario_herdado_da_credencial(apoio_fluir, settings):
    """Sem pino, só quem tem use_gcal usa a própria seleção. A Apoio publica só no calendário da
    organização — nunca num calendário herdado de outro papel (credencial criada quando era Controle)."""
    settings.GCAL_AUTH_MODE = "oauth"
    settings.GCAL_OAUTH_CALENDAR_ID = ""
    _conectar(apoio_fluir, default_calendar_id="calendario-antigo@group.calendar.google.com")

    resp = _cliente(apoio_fluir).get("/api/integrations/google/status/")

    assert resp.data["publish_block_reason"] == "google_calendar_not_configured"
    assert resp.data["publish_ready"] is False


@pytest.mark.parametrize(
    "cenario, motivo",
    [
        ("apoio_sem_setor", "no_setor_scope"),
        ("apoio_sem_conexao", "google_not_connected"),
        ("apoio_conectada_sem_pino", "google_calendar_not_configured"),
        ("apoio_conectada_com_pino", None),
        ("controle_com_calendario_escolhido", None),
    ],
)
def test_status_publish_block_reason_matriz(cenario, motivo, gerencia_fluir, settings):
    settings.GCAL_AUTH_MODE = "oauth"
    settings.GCAL_OAUTH_CALENDAR_ID = ORG if cenario == "apoio_conectada_com_pino" else ""
    if cenario == "apoio_sem_setor":
        user = _apoio(None)
    elif cenario.startswith("apoio"):
        user = _apoio(gerencia_fluir)
        if "conectada" in cenario:
            _conectar(user)
    else:
        user = _controle()
        _conectar(user, default_calendar_id="formacoes@group.calendar.google.com")

    resp = _cliente(user).get("/api/integrations/google/status/")

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["publish_block_reason"] == motivo
    assert resp.data["publish_ready"] is (motivo is None)


# ---------------------------------------------------------------------------
# D. Superfície: só os 4 endpoints da própria credencial abrem
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nome", ["google_oauth_start", "google_oauth_callback", "google_oauth_status", "google_oauth_disconnect"]
)
def test_oauth_views_da_propria_credencial_abrem_para_a_apoio(nome):
    (permissao,) = getattr(views_oauth, nome).cls.permission_classes
    assert {permissao.op1_class, permissao.op2_class} == {CanUseGcal, CanPublishSetorSolicitacao}


@pytest.mark.parametrize(
    "nome", ["google_oauth_list_events", "google_oauth_list_calendars", "google_oauth_select_calendar"]
)
def test_oauth_views_de_calendario_seguem_so_use_gcal(nome):
    assert list(getattr(views_oauth, nome).cls.permission_classes) == [CanUseGcal]


@pytest.mark.parametrize(
    "metodo, url",
    [
        ("get", "/api/integrations/google/calendars/"),
        ("post", "/api/integrations/google/select-calendar/"),
        ("get", "/api/integrations/google/events/"),
    ],
)
def test_apoio_calendars_select_calendar_events_403(metodo, url, apoio_fluir):
    assert getattr(_cliente(apoio_fluir), metodo)(url).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "metodo, url",
    [
        ("get", "/api/oauth/google/start/"),
        ("get", "/api/oauth/google/callback/"),
        ("get", "/api/integrations/google/status/"),
        ("post", "/api/integrations/google/disconnect/"),
    ],
)
def test_formador_start_callback_status_disconnect_403(metodo, url):
    formador = UsuarioFactory()
    formador.groups.add(GroupFactory(name="Formador"))
    assert getattr(_cliente(formador), metodo)(url).status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# E. Sanitização do return_to
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    ["/\\evil.com", "\\/evil.com", "/\t/evil.com", "/solicitacoes/publicacao\r\nSet-Cookie: x=1", "/pre-agenda\x00"],
)
def test_is_safe_url_rejeita_barra_invertida_e_controle(url):
    """O navegador normaliza '/\\' para '//' (outro host). Controle CR/LF/NUL também sai."""
    assert _is_safe_url(url) is False


@pytest.mark.parametrize("url", ["/pre-agenda", PAGINA_PUBLICACAO, "/pre-agenda?tab=integrations"])
def test_is_safe_url_aceita_caminhos_relativos(url):
    assert _is_safe_url(url) is True
