"""
Command: cópia Google → Sistema (horário e cancelamento feitos na agenda da organização).

Uso:
    python manage.py gcal_copia                 # dry-run: lê e decide, não grava nada
    python manage.py gcal_copia --apply         # grava (no modo do cursor: observar ou copiar)
    python manage.py gcal_copia --operador 7    # outra conta Google faz a leitura

A agenda é sempre `GCAL_OAUTH_CALENDAR_ID` (vazio ou 'primary' é erro). A saída só traz
contagens por motivo, futuro/passado e s<id>: nada de título, nome ou e-mail.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.core.models import GCalCopiaCursor, Usuario
from apps.core.services.gcal.copia import sincronizar
from apps.core.services.gcal_client_factory import get_oauth_client_for_user


class Command(BaseCommand):
    help = (
        "Copia do Google para o sistema o horário e o cancelamento de evento aprovado e publicado. "
        "Dry-run por padrão. Montar o cliente pode renovar o token do operador (grava a credencial e "
        "um AuditLog GOOGLE_REFRESH_TOKEN; no invalid_grant a credencial é apagada), como no uso normal."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--apply", action="store_true", help="Grava (sem isto é dry-run)")
        parser.add_argument("--operador", type=int, default=None, help="Id do usuário cuja conta Google lê")
        parser.add_argument(
            "--liberar-freio",
            action="store_true",
            help=(
                "Aplica os cancelamentos que o freio de massa segurou, só se a lista for a mesma da "
                "rodada anterior (freio_ids); se mudou, nada é aplicado e a lista nova fica (só com --apply)"
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        aplicar: bool = options["apply"]
        if options["liberar_freio"] and not aplicar:
            raise CommandError("--liberar-freio só vale com --apply")
        pino = str(getattr(settings, "GCAL_OAUTH_CALENDAR_ID", "") or "")
        if not pino or pino == "primary":
            raise CommandError("GCAL_OAUTH_CALENDAR_ID vazio ou 'primary': a cópia só lê a agenda da organização")

        cursor = GCalCopiaCursor.objects.filter(calendar_id=pino).first()
        operador_id: int | None = options["operador"] or (cursor.operador_id if cursor else None)
        if operador_id is None:
            raise CommandError("Sem operador: passe --operador <id>")
        operador = Usuario.objects.filter(pk=operador_id).first()
        if operador is None:
            raise CommandError(f"Operador u{operador_id} não existe")
        if cursor is None:
            cursor = GCalCopiaCursor(calendar_id=pino, operador_id=operador_id)
            if aplicar:
                cursor.save()  # nasce desligado e em observar (padrões do model)

        try:
            client, _ = get_oauth_client_for_user(operador)
        except ValueError as e:
            raise CommandError(f"Sem cliente Google para u{operador_id}: {type(e).__name__}") from e

        r = sincronizar(
            cursor, client, escrever=aplicar, operador_id=operador_id, liberar_freio=options["liberar_freio"]
        )
        self._imprimir(r.status, cursor.modo, aplicar, r.resumo, r.erro)
        if r.status == "ERROR":
            raise CommandError(r.erro)

    def _imprimir(self, status: str, modo: str, aplicar: bool, resumo: dict[str, Any], erro: str) -> None:
        out = self.stdout
        out.write(f"status={status} modo={modo} {'apply' if aplicar else 'dry-run'}")
        if erro:
            out.write(f"erro={erro}")
        if not resumo:
            return
        out.write(
            f"lidos={resumo.get('lidos', 0)} leitura_completa={resumo.get('leitura_completa')} "
            f"futuro={resumo.get('futuro', 0)} passado={resumo.get('passado', 0)} "
            f"falhas={len(resumo.get('falhas', []))} freio={resumo.get('freio', 0)}"
        )
        freio_ids = resumo.get("freio_ids", [])
        if freio_ids:
            # A lista inteira que o --liberar-freio vai comparar: é esta que o dono confere.
            out.write(f"freio_ids: {len(freio_ids)} [{' '.join(freio_ids)}]")
        for motivo, n in sorted(resumo.get("contagens", {}).items()):
            ids = resumo.get("ids", {}).get(motivo, [])
            out.write(f"  {motivo}: {n}" + (f" [{' '.join(ids)}]" if ids else ""))
