"""
Management Command: Rotacionar GCAL_ENCRYPTION_KEY

Rotaciona chave de criptografia dos tokens OAuth do Google Calendar
sem causar downtime.

Usage:
    python manage.py rotate_gcal_encryption_key --old-key=<OLD_KEY> --new-key=<NEW_KEY>

Example:
    # Gerar nova chave
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # Rotacionar (OLD_KEY = valor atual de GCAL_ENCRYPTION_KEY)
    python manage.py rotate_gcal_encryption_key \\
        --old-key="<VALOR_ANTIGO>" \\
        --new-key="<NOVO_VALOR_GERADO>"

    # Atualizar .env com nova chave e restart aplicação

Refs:
    - OAuth Phase 6: Management Command de rotação
    - google_oauth.py: rotate_encryption_key()
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false
from __future__ import annotations

import sys
from typing import Any

from cryptography.fernet import InvalidToken
from django.core.management.base import BaseCommand, CommandParser

from apps.core.services.google_oauth import rotate_encryption_key


class Command(BaseCommand):
    help = "Rotaciona GCAL_ENCRYPTION_KEY sem downtime"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--old-key',
            type=str,
            required=True,
            help='Chave Fernet antiga (base64-encoded, valor atual de GCAL_ENCRYPTION_KEY)'
        )
        parser.add_argument(
            '--new-key',
            type=str,
            required=True,
            help='Chave Fernet nova (base64-encoded, gerada via Fernet.generate_key())'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        old_key = options['old_key']
        new_key = options['new_key']

        self.stdout.write("🔄 Iniciando rotação de chave de criptografia...")

        try:
            count = rotate_encryption_key(old_key, new_key)

            self.stdout.write(
                self.style.SUCCESS(f"✅ {count} credenciais atualizadas com sucesso!")
            )
            self.stdout.write("")
            self.stdout.write("📝 Próximos passos:")
            self.stdout.write("  1. Atualizar GCAL_ENCRYPTION_KEY no .env com a nova chave")
            self.stdout.write(f"     GCAL_ENCRYPTION_KEY=\"{new_key}\"")
            self.stdout.write("  2. Restart da aplicação (docker compose restart web worker beat)")
            self.stdout.write("")

        except InvalidToken:
            self.stdout.write(
                self.style.ERROR("❌ Erro: Chave antiga incorreta!")
            )
            self.stdout.write("")
            self.stdout.write("Verifique se --old-key corresponde ao valor atual de GCAL_ENCRYPTION_KEY.")
            sys.exit(1)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Erro ao rotacionar chave: {e}")
            )
            sys.exit(1)
