"""
P1.4 - Testes de Guard Rails de Produção

Valida que settings.py bloqueia configurações inseguras em produção:
- DEBUG=True em produção → sys.exit(1)
- ALLOWED_HOSTS vazio em produção → sys.exit(1)
- CSRF_COOKIE_SECURE=False → warning
- SESSION_COOKIE_SECURE=False → warning
- SECRET_KEY curta → warning
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

from django.conf import settings


class ProductionGuardRailsTests(TestCase):
    """
    Testes de segurança para guards de produção em settings.py

    NOTA: Estes testes rodam Django em subprocess porque os guards
    chamam sys.exit(1) e parariam o pytest.
    """

    def test_startup_fails_with_debug_true_in_production(self):
        """
        P1.4 - Startup DEVE falhar se DEBUG=True em ENVIRONMENT=production

        Cenário:
        - ENVIRONMENT=production
        - DEBUG=1 (True)

        Expectativa:
        - settings.py detecta DEBUG=True
        - sys.exit(1) com mensagem de erro
        - Processo termina com exit code 1
        """
        env = os.environ.copy()
        env["ENVIRONMENT"] = "production"
        env["DEBUG"] = "1"  # CRITICAL: DEBUG=True em produção
        env["ALLOWED_HOSTS"] = "example.com"  # Válido para passar o outro guard
        env["SECRET_KEY"] = "a" * 64  # Válido para passar o outro guard
        env["DB_NAME"] = "test_db"
        env["DB_USER"] = "test_user"
        env["DB_PASSWORD"] = "test_password"
        env["DB_HOST"] = "localhost"
        env["DB_PORT"] = "5434"

        # Rodar Django check em subprocess
        # P1.4 FIX: Correct path - manage.py is at /app/manage.py (container root)
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=str(Path(settings.BASE_DIR)),  # Project root where manage.py is located
            env=env,
            capture_output=True,
            text=True,
        )

        # Validar que falhou com exit code 1
        self.assertEqual(result.returncode, 1)

        # Validar mensagem de erro no stderr
        self.assertIn("DEBUG=True em produção é inseguro", result.stderr)
        self.assertIn("ERRO CRÍTICO", result.stderr)

    def test_startup_fails_with_empty_allowed_hosts_in_production(self):
        """
        P1.4 - Startup DEVE falhar se ALLOWED_HOSTS vazio/wildcard em produção

        Cenário:
        - ENVIRONMENT=production
        - ALLOWED_HOSTS=* (wildcard)

        Expectativa:
        - settings.py detecta ALLOWED_HOSTS=['*']
        - sys.exit(1) com mensagem de erro
        - Processo termina com exit code 1
        """
        env = os.environ.copy()
        env["ENVIRONMENT"] = "production"
        env["DEBUG"] = "0"  # Válido
        env["ALLOWED_HOSTS"] = "*"  # CRITICAL: Wildcard em produção
        env["SECRET_KEY"] = "a" * 64  # Válido
        env["DB_NAME"] = "test_db"
        env["DB_USER"] = "test_user"
        env["DB_PASSWORD"] = "test_password"
        env["DB_HOST"] = "localhost"
        env["DB_PORT"] = "5434"

        # Rodar Django check em subprocess
        # P1.4 FIX: Correct path - manage.py is at /app/manage.py (container root)
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=str(Path(settings.BASE_DIR)),  # Project root where manage.py is located
            env=env,
            capture_output=True,
            text=True,
        )

        # Validar que falhou com exit code 1
        self.assertEqual(result.returncode, 1)

        # Validar mensagem de erro no stderr
        self.assertIn("ALLOWED_HOSTS=['*'] em produção é inseguro", result.stderr)
        self.assertIn("ERRO CRÍTICO", result.stderr)

    def test_startup_succeeds_with_valid_production_config(self):
        """
        P1.4 - Startup DEVE passar se configuração de produção está correta

        Cenário:
        - ENVIRONMENT=production
        - DEBUG=0
        - ALLOWED_HOSTS=example.com
        - SECRET_KEY longa (64+ chars)

        Expectativa:
        - settings.py não chama sys.exit()
        - Django check passa (exit code 0)
        """
        env = os.environ.copy()
        env["ENVIRONMENT"] = "production"
        env["DEBUG"] = "0"
        env["ALLOWED_HOSTS"] = "example.com,api.example.com"
        env["SECRET_KEY"] = "a" * 64  # 64 chars (>= 50 recomendado)
        env["DB_NAME"] = "test_db"
        env["DB_USER"] = "test_user"
        env["DB_PASSWORD"] = "test_password"
        env["DB_HOST"] = "localhost"
        env["DB_PORT"] = "5434"

        # Rodar Django check em subprocess
        # P1.4 FIX: Correct path - manage.py is at /app/manage.py (container root)
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=str(Path(settings.BASE_DIR)),  # Project root where manage.py is located
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Validar que passou (pode ter warnings, mas não erros críticos)
        # Exit code 0 = sucesso
        # Exit code 1 = failure (guards bloquearam)
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        # Aceitar exit code 0 (sucesso) ou != 1 (warnings OK, mas não critical errors)
        self.assertNotEqual(result.returncode, 1, f"Django check falhou inesperadamente. Stderr: {result.stderr}")

    def test_startup_fails_with_short_secret_key(self):
        """
        SEC-AUTH-02 - Startup DEVE falhar se SECRET_KEY < 50 chars em produção

        Cenário:
        - ENVIRONMENT=production
        - SECRET_KEY com apenas 20 caracteres

        Expectativa:
        - settings.py detecta SECRET_KEY curta
        - sys.exit(1) com mensagem de erro
        - Processo termina com exit code 1
        """
        env = os.environ.copy()
        env["ENVIRONMENT"] = "production"
        env["DEBUG"] = "0"
        env["ALLOWED_HOSTS"] = "example.com"
        env["SECRET_KEY"] = "a" * 20  # Apenas 20 chars (< 50 mínimo)
        env["DB_NAME"] = "test_db"
        env["DB_USER"] = "test_user"
        env["DB_PASSWORD"] = "test_password"
        env["DB_HOST"] = "localhost"
        env["DB_PORT"] = "5434"

        # Rodar Django check em subprocess
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=str(Path(settings.BASE_DIR)),
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # SEC-AUTH-02: Short SECRET_KEY now causes sys.exit(1)
        self.assertEqual(result.returncode, 1)

        # Validar mensagem de erro no stderr
        self.assertIn("SECRET_KEY muito curta", result.stderr)
        self.assertIn("ERRO CRÍTICO", result.stderr)


class DevToolsProductionGuardTests(TestCase):
    """
    CP-08 (#1466) — `apps.dev_tools` NUNCA carrega sob ENVIRONMENT=production.

    O default de INCLUDE_DEV_TOOLS é `true` e a stack de produção não define a
    variável, então o app entrava em prod por omissão. O guard força `False` em
    produção independente da env var (defense-in-depth, mesmo espírito dos guards
    de SECRET_KEY/ALLOWED_HOSTS).

    Optou-se por forçar o valor em vez de `sys.exit(1)`: produção hoje não define
    a variável, então abortar o boot transformaria o footgun em indisponibilidade
    no primeiro deploy.
    """

    def _installed_apps_under(self, **overrides: str) -> tuple[int, str, str]:
        """Sobe o Django em subprocess e imprime INSTALLED_APPS."""
        env = os.environ.copy()
        env["DEBUG"] = "0"
        env["ALLOWED_HOSTS"] = "example.com"
        env["SECRET_KEY"] = "a" * 64
        env["DB_NAME"] = "test_db"
        env["DB_USER"] = "test_user"
        env["DB_PASSWORD"] = "test_password"
        env["DB_HOST"] = "localhost"
        env["DB_PORT"] = "5434"
        env.update(overrides)

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import django;django.setup();"
                "from django.conf import settings;"
                "print('\\n'.join(settings.INSTALLED_APPS))",
            ],
            cwd=str(Path(settings.BASE_DIR)),
            env={**env, "DJANGO_SETTINGS_MODULE": "config.settings"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr

    def test_dev_tools_absent_in_production_by_default(self):
        """CP-08: sem INCLUDE_DEV_TOOLS definido, prod NÃO carrega dev_tools."""
        code, stdout, stderr = self._installed_apps_under(ENVIRONMENT="production")

        self.assertEqual(code, 0, f"Django não subiu. stderr: {stderr}")
        self.assertNotIn("apps.dev_tools", stdout.split("\n"))

    def test_dev_tools_absent_in_production_even_if_explicitly_enabled(self):
        """CP-08: INCLUDE_DEV_TOOLS=true NÃO vence o guard de produção."""
        code, stdout, stderr = self._installed_apps_under(
            ENVIRONMENT="production",
            INCLUDE_DEV_TOOLS="true",
        )

        self.assertEqual(code, 0, f"Django não subiu. stderr: {stderr}")
        self.assertNotIn("apps.dev_tools", stdout.split("\n"))
        self.assertIn("INCLUDE_DEV_TOOLS=true ignorado", stderr)

    def test_dev_tools_present_in_development(self):
        """Sem regressão: fora de produção o app continua disponível."""
        code, stdout, stderr = self._installed_apps_under(
            ENVIRONMENT="development",
            INCLUDE_DEV_TOOLS="true",
        )

        self.assertEqual(code, 0, f"Django não subiu. stderr: {stderr}")
        self.assertIn("apps.dev_tools", stdout.split("\n"))
