"""
M03-02 (#1648) — login enforça CSRF (barra login-CSRF / session fixation).

A view de login é `@api_view` (csrf_exempt implícito) e, sendo anônima, o
`enforce_csrf` do SessionAuthentication do DRF nunca dispara — um POST
cross-origin conseguia estabelecer sessão. O fix enforça o CSRF manualmente.

Nota de teste: o `APIClient` padrão (enforce_csrf_checks=False) PULA o check via
`_dont_enforce_csrf_checks`, então os testes de login existentes continuam
válidos. Para exercitar o CSRF real usamos `APIClient(enforce_csrf_checks=True)`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/auth/login/"
PASSWORD = "SenhaForte!123"
# Origin same-origin: satisfaz a checagem de Origin do CSRF em HTTPS, isolando a
# validação do TOKEN (sem isso, o 403 viria da checagem de Referer, não do token).
ORIGIN = "https://testserver"


def _user(username: str, cpf: str):
    return UsuarioFactory(username=username, password=PASSWORD, cpf=cpf, is_active=True)


class TestLoginCsrfEnforced:
    def test_login_sem_csrf_token_retorna_403(self):
        """RED: hoje o login (csrf_exempt) sucede sem CSRF mesmo em cliente estrito."""
        _user("csrf_a", "79000000001")
        client = APIClient(enforce_csrf_checks=True)
        resp = client.post(
            LOGIN_URL,
            {"username": "csrf_a", "password": PASSWORD},
            format="json",
            secure=True,
            HTTP_ORIGIN=ORIGIN,
        )
        assert resp.status_code == 403, f"esperado 403, obteve {resp.status_code}"

    def test_login_com_csrf_token_valido_funciona(self):
        """Com token CSRF válido (fluxo do frontend), o login procede."""
        _user("csrf_b", "79000000002")
        client = APIClient(enforce_csrf_checks=True)
        # Frontend: busca o token em /api/csrf/ (seta o cookie) e o envia no header.
        csrf_resp = client.get("/api/csrf/", secure=True, HTTP_ORIGIN=ORIGIN)
        token = csrf_resp.data["csrfToken"]
        resp = client.post(
            LOGIN_URL,
            {"username": "csrf_b", "password": PASSWORD},
            format="json",
            secure=True,
            HTTP_ORIGIN=ORIGIN,
            HTTP_X_CSRFTOKEN=token,
        )
        assert resp.status_code == 200, resp.data


class TestExistingClientsUnaffected:
    def test_apiclient_padrao_loga_sem_token(self):
        """Não-regressão: APIClient padrão pula o CSRF (_dont_enforce_csrf_checks)."""
        _user("csrf_c", "79000000003")
        client = APIClient()  # enforce_csrf_checks=False (padrão)
        resp = client.post(LOGIN_URL, {"username": "csrf_c", "password": PASSWORD}, format="json", secure=True)
        assert resp.status_code == 200, resp.data
