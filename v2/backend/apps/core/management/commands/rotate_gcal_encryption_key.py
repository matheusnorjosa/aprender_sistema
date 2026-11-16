"""
Management Command: recifrar os tokens do Google com a chave principal (FER-59).

Troca de chave sem parada:
    1. Gerar a chave nova (fora do servidor):
       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    2. Na stack: GCAL_ENCRYPTION_KEY_FALLBACKS=<nova> (principal segue a antiga); atualizar a stack.
    3. Na stack: GCAL_ENCRYPTION_KEY=<nova> e GCAL_ENCRYPTION_KEY_FALLBACKS=<antiga>; atualizar a stack.
    4. python manage.py rotate_gcal_encryption_key
    5. Tirar GCAL_ENCRYPTION_KEY_FALLBACKS e atualizar a stack.

As chaves vêm só do ambiente: o comando não as recebe por argumento (não ficam no histórico nem na
lista de processos) e nunca as imprime.

Refs:
    - token_manager.rotate_encryption_key()
    - v2/docs/GUIDE_GCAL.md, seção 8
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from cryptography.fernet import InvalidToken

from apps.core.services.google_oauth import rotate_encryption_key
from apps.core.services.oauth.token_manager import _get_fallback_keys, _get_fernet_key


class Command(BaseCommand):
    help = "Recifra os tokens do Google com GCAL_ENCRYPTION_KEY (chaves antigas em GCAL_ENCRYPTION_KEY_FALLBACKS)"

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            resultado = rotate_encryption_key()
        except InvalidToken:
            raise CommandError(
                "Nada foi gravado: alguma credencial não abre com nenhuma chave configurada. "
                + "Confira se a chave antiga está em GCAL_ENCRYPTION_KEY_FALLBACKS."
            ) from None
        except ValueError as exc:
            raise CommandError(f"Nada foi gravado: {exc}") from None

        self.stdout.write(self.style.SUCCESS(f"{resultado.recifradas} credenciais recifradas com a chave principal."))
        fallbacks = _get_fallback_keys()
        if not fallbacks:
            self.stdout.write(
                self.style.WARNING(
                    "Atenção: nenhuma chave em GCAL_ENCRYPTION_KEY_FALLBACKS. A chave não mudou; "
                    + "os tokens só foram recifrados com a mesma principal."
                )
            )
        elif _get_fernet_key().decode("utf-8") in fallbacks:
            self.stdout.write(
                self.style.WARNING(
                    "Atenção: a chave principal também está em GCAL_ENCRYPTION_KEY_FALLBACKS. "
                    + "Confira se GCAL_ENCRYPTION_KEY recebeu mesmo a chave nova."
                )
            )
        elif resultado.so_com_fallback == 0:
            # Também com 0 credenciais: aí não há como conferir que a principal é a nova.
            self.stdout.write(
                self.style.WARNING(
                    "Atenção: nenhuma credencial estava cifrada com uma chave de GCAL_ENCRYPTION_KEY_FALLBACKS "
                    + f"({resultado.recifradas} no banco). Ou GCAL_ENCRYPTION_KEY ainda não tem a chave nova neste "
                    + "container (passo 3 não aplicado), ou tudo já tinha sido recifrado. "
                    + "Não tire FALLBACKS antes de conferir o passo 3."
                )
            )
        else:
            self.stdout.write(
                "Próximo passo: todas as credenciais abrem só com a principal; "
                + "tirar GCAL_ENCRYPTION_KEY_FALLBACKS e atualizar a stack."
            )
