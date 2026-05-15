#!/usr/bin/env python3
"""
Script para validar configuração OAuth do Google Calendar.

Uso:
    python validate_oauth_config.py

Verifica:
- Presença de variáveis obrigatórias
- Formato correto das variáveis
- Encryption key válida
- Client ID/Secret format
"""

# Standalone CLI script (not part of Django app). Optional dependencies
# (``dotenv``, ``cryptography``) are imported lazily inside functions and may
# not be installed in the analysis environment — suppress related Pyright
# noise to keep the IDE Problems panel clean.
# pyright: reportMissingImports=false, reportMissingTypeArgument=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false, reportReturnType=false

import os
import sys
from pathlib import Path


def check_env_variable(name, required=True, format_check=None):
    """Verifica se variável de ambiente existe e está no formato correto."""
    value = os.getenv(name)

    if not value:
        if required:
            print(f"❌ {name}: AUSENTE (obrigatória)")
            return False
        else:
            print(f"⚠️  {name}: ausente (opcional)")
            return True

    if format_check:
        if not format_check(value):
            print(f"❌ {name}: FORMATO INVÁLIDO")
            return False

    # Mostrar apenas os primeiros/últimos caracteres para segurança
    if len(value) > 40:
        display_value = f"{value[:10]}...{value[-10:]}"
    else:
        display_value = f"{value[:10]}..."

    print(f"✅ {name}: {display_value}")
    return True


def validate_fernet_key(key):
    """Valida se a chave é uma Fernet key válida."""
    try:
        from cryptography.fernet import Fernet
        Fernet(key.encode() if isinstance(key, str) else key)
        return True
    except Exception:
        return False


def validate_client_id(client_id):
    """Valida formato do OAuth Client ID.

    Formato esperado: ``<id>.apps.googleusercontent.com``.

    Hardening (CodeQL py/incomplete-url-substring-sanitization):
    substring check (``"x" in value``) é bypassável (ex: ``evil.com/.apps.googleusercontent.com``).
    Usar ``endswith`` + checagem de prefixo + ausência de delimitadores de URL.
    """
    if not isinstance(client_id, str) or not client_id:
        return False
    # Não pode conter delimitadores de URL/whitespace
    if any(ch in client_id for ch in ("/", " ", "\t", "\n", "?", "#", ":", "@")):
        return False
    suffix = ".apps.googleusercontent.com"
    if not client_id.endswith(suffix):
        return False
    prefix = client_id[: -len(suffix)]
    # Prefixo precisa existir (não pode ser apenas o sufixo) e não começar com '.'
    return bool(prefix) and not prefix.startswith(".")


def validate_redirect_uri(uri):
    """Valida formato do Redirect URI.

    Hardening: parse com ``urlparse`` e exigir scheme ``http``/``https`` E
    netloc não-vazio (substring/startswith é bypassável por URLs malformadas).
    """
    if not isinstance(uri, str) or not uri:
        return False
    try:
        from urllib.parse import urlparse

        parsed = urlparse(uri)
    except (ValueError, TypeError):
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def main():
    print("=" * 70)
    print("🔐 Validação de Configuração OAuth - Google Calendar")
    print("=" * 70)
    print()

    # Carregar .env se existir
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"📄 Carregando variáveis de: {env_file}")
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print()
    else:
        print(f"⚠️  Arquivo .env não encontrado em: {env_file}")
        print("   Verificando variáveis de ambiente do sistema...")
        print()

    all_valid = True

    # Variáveis OAuth obrigatórias
    print("📋 Variáveis OAuth Obrigatórias")
    print("-" * 70)

    all_valid &= check_env_variable(
        "GCAL_OAUTH_CLIENT_ID",
        required=True,
        format_check=validate_client_id
    )

    all_valid &= check_env_variable(
        "GCAL_OAUTH_CLIENT_SECRET",
        required=True
    )

    all_valid &= check_env_variable(
        "GCAL_OAUTH_REDIRECT_URI",
        required=True,
        format_check=validate_redirect_uri
    )

    all_valid &= check_env_variable(
        "GCAL_ENCRYPTION_KEY",
        required=True,
        format_check=validate_fernet_key
    )

    print()

    # Variáveis OAuth opcionais
    print("📋 Variáveis OAuth Opcionais")
    print("-" * 70)

    check_env_variable(
        "GCAL_OAUTH_SCOPES",
        required=False
    )

    check_env_variable(
        "GCAL_AUTH_MODE",
        required=False
    )

    print()

    # Verificação de modo de autenticação
    auth_mode = os.getenv("GCAL_AUTH_MODE", "service_account")
    print("🔐 Modo de Autenticação")
    print("-" * 70)

    if auth_mode == "oauth":
        print("✅ GCAL_AUTH_MODE=oauth (correto para batch operations)")
    elif auth_mode == "service_account":
        print("⚠️  GCAL_AUTH_MODE=service_account (OAuth não será usado)")
        print("   Para usar OAuth, defina GCAL_AUTH_MODE=oauth no .env")
    else:
        print(f"❌ GCAL_AUTH_MODE='{auth_mode}' (valor inválido)")
        print("   Valores válidos: 'oauth' ou 'service_account'")
        all_valid = False

    print()

    # Verificação de Client ID no Google Cloud Console
    print("☁️  Checklist Google Cloud Console")
    print("-" * 70)
    print("1. [ ] Google Calendar API habilitada")
    print("2. [ ] OAuth 2.0 Client criado (Web application)")
    print("3. [ ] Redirect URI configurado:")
    redirect_uri = os.getenv("GCAL_OAUTH_REDIRECT_URI", "não configurado")
    print(f"       {redirect_uri}")
    print("4. [ ] Scopes configurados:")
    scopes = os.getenv(
        "GCAL_OAUTH_SCOPES",
        "https://www.googleapis.com/auth/calendar"
    )
    for scope in scopes.split():
        print(f"       - {scope}")

    print()

    # Resultado final
    print("=" * 70)
    if all_valid:
        print("✅ CONFIGURAÇÃO VÁLIDA!")
        print()
        print("Próximos passos:")
        print("1. Reiniciar containers: docker compose restart web worker beat")
        print("2. Acessar: http://localhost:5173/pre-agenda")
        print("3. Clicar 'Conectar conta Google'")
        print("4. Completar consent flow")
        print("5. Verificar status: GET /api/integrations/google/status/")
        return 0
    else:
        print("❌ CONFIGURAÇÃO INVÁLIDA")
        print()
        print("Ações necessárias:")
        print("1. Corrigir variáveis faltantes ou inválidas")
        print("2. Consultar: OAUTH_SETUP_GUIDE.md")
        print("3. Verificar .env em: v2/infra/.env")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Validação interrompida pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
