"""Alerta de conta Google (#2039, épico #1656): credencial morta aparece no sistema.

Credenciais Google morriam em silêncio (em prod, 2 de 3 estavam mortas desde abril) e ninguém
percebia até um publish falhar. Aqui:

1. M12-10: `invalid_grant` no refresh apaga a credencial e audita — e isso agora fica gravado
   (antes o `raise` dentro do `transaction.atomic()` desfazia o delete e o audit).

Só o ponto de rede é simulado (`requests.post` do token_manager); nunca a função testada.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest
import requests

from apps.core.models import AuditLog, GoogleOAuthCredential
from apps.core.services.oauth import token_manager
from apps.core.services.oauth.token_manager import encrypt_token
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

TOKEN_URL = "https://oauth2.googleapis.com/token"


@pytest.fixture(autouse=True)
def oauth_client_env(monkeypatch):
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GCAL_OAUTH_CLIENT_SECRET", "segredo")


def _resposta(status: int, corpo: dict[str, Any]) -> requests.Response:
    """Resposta HTTP real do `requests` (o `raise_for_status` de verdade decide o erro)."""
    resposta = requests.Response()
    resposta.status_code = status
    resposta._content = json.dumps(corpo).encode()
    resposta.url = TOKEN_URL
    return resposta


INVALID_GRANT = {"error": "invalid_grant", "error_description": "Token has been expired or revoked."}


def _conectar(user, refresh_token: str = "refresh", *, expira_em: timedelta = timedelta(hours=-2)):
    return GoogleOAuthCredential.objects.create(
        user=user,
        google_email="conta@aprendereditora.com.br",
        access_token_encrypted=encrypt_token("acesso"),
        refresh_token_encrypted=encrypt_token(refresh_token),
        token_expiry=timezone.now() + expira_em,
        scope="https://www.googleapis.com/auth/calendar",
    )


# ---------------------------------------------------------------------------
# 1. M12-10 — invalid_grant apaga e audita DE VERDADE, e ainda levanta o erro
# ---------------------------------------------------------------------------


def test_invalid_grant_remove_credencial_grava_audit_e_levanta_erro():
    usuario = UsuarioFactory()
    cred = _conectar(usuario)

    with patch.object(token_manager.requests, "post", return_value=_resposta(400, INVALID_GRANT)):
        # Depois da remoção o card só oferece "Conectar": a mensagem não manda "Desconectar".
        with pytest.raises(ValueError, match=r"revogada\. Conecte sua conta Google de novo"):
            token_manager.refresh_access_token_safe(cred)

    assert not GoogleOAuthCredential.objects.filter(pk=cred.pk).exists()
    audit = AuditLog.objects.get(usuario=usuario, action=AuditLog.Action.GOOGLE_DISCONNECT)
    assert audit.details["status"] == "auto_removed"
    assert "invalid_grant" in audit.details["reason"]


def test_refresh_de_credencial_ja_removida_da_erro_de_reconexao_e_nao_de_orm():
    """Corrida: outra task removeu a credencial enquanto esta esperava o lock. A pessoa deve ver a
    mensagem de reconexão, não "GoogleOAuthCredential matching query does not exist."."""
    cred = _conectar(UsuarioFactory())
    GoogleOAuthCredential.objects.filter(pk=cred.pk).delete()

    with patch.object(token_manager.requests, "post") as post:
        with pytest.raises(ValueError, match="Conecte sua conta Google de novo"):
            token_manager.refresh_access_token_safe(cred, force=True)
    post.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Job diário: força o refresh de cada credencial e descobre as mortas
# ---------------------------------------------------------------------------


def _google_por_refresh_token(url, data, timeout):
    """Endpoint de token do Google simulado: a resposta depende do refresh_token enviado."""
    refresh_token = data["refresh_token"]
    if refresh_token == "rt-ok":
        return _resposta(200, {"access_token": "acesso-novo", "expires_in": 3600})
    if refresh_token == "rt-revogado":
        return _resposta(400, INVALID_GRANT)
    if refresh_token == "rt-google-fora":
        return _resposta(503, {"error": "backend_error"})
    if refresh_token == "rt-400-outro-erro":
        return _resposta(400, {"error": "invalid_request"})
    if refresh_token == "rt-cliente-invalido":
        return _resposta(401, {"error": "invalid_client"})
    raise requests.exceptions.ConnectionError("rede caiu")


def test_probe_so_remove_com_invalid_grant():
    """400 que não é invalid_grant e 401 (config do cliente OAuth) não provam que a credencial
    morreu: ficam, e contam como erro."""
    from apps.core.tasks import probe_google_credentials

    em_uma_hora = timedelta(hours=1)
    outro_400 = _conectar(UsuarioFactory(), "rt-400-outro-erro", expira_em=em_uma_hora)
    cliente_invalido = _conectar(UsuarioFactory(), "rt-cliente-invalido", expira_em=em_uma_hora)

    with patch.object(token_manager.requests, "post", side_effect=_google_por_refresh_token):
        resumo = probe_google_credentials()

    assert resumo == {"ok": 0, "removed": 0, "errors": 2}
    assert GoogleOAuthCredential.objects.filter(pk__in=[outro_400.pk, cliente_invalido.pk]).count() == 2


def test_probe_ignora_credencial_de_usuario_inativo():
    """Pessoa desligada: o refresh diário manteria o token vivo à toa (e ela nunca entra no aviso)."""
    from apps.core.tasks import probe_google_credentials

    _conectar(UsuarioFactory(is_active=False), "rt-ok", expira_em=timedelta(hours=1))

    with patch.object(token_manager.requests, "post", side_effect=_google_por_refresh_token) as post:
        resumo = probe_google_credentials()

    post.assert_not_called()
    assert resumo == {"ok": 0, "removed": 0, "errors": 0}


def test_probe_forca_refresh_remove_so_a_revogada_e_resume():
    """Tokens ainda válidos: sem forçar, o double-check do refresh nem chamaria o Google e a
    credencial revogada seguiria "conectada" até o próximo publish falhar."""
    from apps.core.tasks import probe_google_credentials

    em_uma_hora = timedelta(hours=1)
    ok = _conectar(UsuarioFactory(), "rt-ok", expira_em=em_uma_hora)
    revogada = _conectar(UsuarioFactory(), "rt-revogado", expira_em=em_uma_hora)
    sem_rede = _conectar(UsuarioFactory(), "rt-sem-rede", expira_em=em_uma_hora)
    google_fora = _conectar(UsuarioFactory(), "rt-google-fora", expira_em=em_uma_hora)

    with patch.object(token_manager.requests, "post", side_effect=_google_por_refresh_token) as post:
        resumo = probe_google_credentials()

    assert resumo == {"ok": 1, "removed": 1, "errors": 2}
    assert post.call_count == 4

    ok.refresh_from_db()
    assert token_manager.decrypt_token(ok.access_token_encrypted) == "acesso-novo"
    assert not GoogleOAuthCredential.objects.filter(pk=revogada.pk).exists()
    assert AuditLog.objects.filter(
        usuario=revogada.user, action=AuditLog.Action.GOOGLE_DISCONNECT, details__status="auto_removed"
    ).exists()
    # Erro de rede / 5xx não é prova de credencial morta: fica.
    assert GoogleOAuthCredential.objects.filter(pk__in=[sem_rede.pk, google_fora.pk]).count() == 2


def test_beat_agenda_o_probe_diario_de_madrugada():
    from celery.schedules import crontab

    from config.celery import app

    entrada = app.conf.beat_schedule["daily-google-credentials-probe"]
    assert entrada["task"] == "apps.core.tasks.probe_google_credentials"
    assert entrada["schedule"] == crontab(hour=5, minute=0)


# ---------------------------------------------------------------------------
# 3. status.reconnect_required — a pessoa vê que o SISTEMA removeu a conexão dela
# ---------------------------------------------------------------------------
# Cada história passa pelo caminho real (refresh, disconnect, callback); só a rede é simulada.


def _usuario(grupo: str = "Controle", **campos):
    user = UsuarioFactory(**campos)
    user.groups.add(GroupFactory(name=grupo))
    return user


def _controle(**campos):
    return _usuario("Controle", **campos)


def _cliente(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _status(user) -> Any:
    resp = _cliente(user).get("/api/integrations/google/status/")
    assert resp.status_code == status.HTTP_200_OK
    return resp.data


def _removida_pelo_sistema(user):
    cred = _conectar(user)
    with patch.object(token_manager.requests, "post", return_value=_resposta(400, INVALID_GRANT)):
        with pytest.raises(ValueError):
            token_manager.refresh_access_token_safe(cred)


def _desconectou_manual(user):
    _conectar(user)
    with patch.object(token_manager.requests, "post", return_value=_resposta(200, {})):  # /revoke do Google
        assert _cliente(user).post("/api/integrations/google/disconnect/").status_code == status.HTTP_200_OK


def _reconectou(user):
    tokens = {
        "email": "conta@aprendereditora.com.br",
        "access_token": "acesso",
        "refresh_token": "refresh-novo",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/calendar",
    }
    state = {"valid": True, "return_to": "/pre-agenda", "user_id": user.pk}
    with (
        patch("apps.core.views_oauth.exchange_code_for_tokens", return_value=tokens),
        patch("apps.core.services.google_oauth.validate_oauth_state", return_value=state),
    ):
        resp = _cliente(user).get("/api/oauth/google/callback/", {"code": "c", "state": "s"})
    assert "google=connected" in resp.url


def _removida_de_novo(user):
    """A credencial nova (do callback) também é revogada."""
    cred = GoogleOAuthCredential.objects.get(user=user)
    with patch.object(token_manager.requests, "post", return_value=_resposta(400, INVALID_GRANT)):
        with pytest.raises(ValueError):
            token_manager.refresh_access_token_safe(cred, force=True)


def _desconectou_a_credencial_atual(user):
    with patch.object(token_manager.requests, "post", return_value=_resposta(200, {})):  # /revoke do Google
        assert _cliente(user).post("/api/integrations/google/disconnect/").status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "historia, esperado",
    [
        ("nunca_conectou", False),
        ("desconectou_manual", False),
        ("removida_pelo_sistema", True),
        ("removida_e_reconectou", False),
        # Só o ÚLTIMO evento decide: uma remoção antiga não conta depois de reconectar e desconectar.
        ("removida_reconectou_desconectou", False),
        ("removida_reconectou_removida_de_novo", True),
    ],
)
def test_status_reconnect_required(historia, esperado):
    user = _controle()
    if historia == "desconectou_manual":
        _desconectou_manual(user)
    elif historia == "removida_pelo_sistema":
        _removida_pelo_sistema(user)
    elif historia.startswith("removida_"):
        _removida_pelo_sistema(user)
        _reconectou(user)
        if historia == "removida_reconectou_desconectou":
            _desconectou_a_credencial_atual(user)
        elif historia == "removida_reconectou_removida_de_novo":
            _removida_de_novo(user)

    assert _status(user)["reconnect_required"] is esperado


def test_status_removida_pelo_sistema_so_acrescenta_reconnect_required(settings):
    """Contrato completo: os demais campos (inclusive publish_ready/publish_block_reason, #2049) não mudam."""
    settings.GCAL_AUTH_MODE = "oauth"
    user = _controle()
    _removida_pelo_sistema(user)

    assert _status(user) == {
        "connected": False,
        "google_email": None,
        "token_expiry": None,
        "expires_in_days": None,
        "is_expired": False,
        "default_calendar_id": None,
        "publish_ready": False,
        "publish_block_reason": "google_not_connected",
        "reconnect_required": True,
    }


# ---------------------------------------------------------------------------
# 4. Aviso ao Controle: quem precisa reconectar, no resumo de alertas do GCal
# ---------------------------------------------------------------------------

ALERTAS = "/api/gcal/dashboard/alerts/summary/"


def test_alerts_summary_lista_so_quem_o_sistema_desconectou():
    removida = _usuario("Apoio de Coordenação", first_name="Ana", last_name="Removida")
    _removida_pelo_sistema(removida)
    _desconectou_manual(_controle())
    reconectou = _controle()
    _removida_pelo_sistema(reconectou)
    _reconectou(reconectou)
    desligada = _controle(first_name="Bia", last_name="Desligada")
    _removida_pelo_sistema(desligada)
    desligada.is_active = False
    desligada.save(update_fields=["is_active"])
    _controle()  # nunca conectou

    resp = _cliente(_controle()).get(ALERTAS)

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["google_reconnect"] == {"count": 1, "users": [{"id": removida.pk, "nome": "Ana Removida"}]}


@pytest.mark.parametrize("grupo", ["Coordenador", "Apoio de Coordenação", "Formador"])
def test_alerts_summary_sem_use_gcal_continua_403(grupo):
    """Guarda: a lista de nomes não abre para quem não tinha acesso ao resumo (só `use_gcal`)."""
    assert _cliente(_usuario(grupo)).get(ALERTAS).status_code == status.HTTP_403_FORBIDDEN
