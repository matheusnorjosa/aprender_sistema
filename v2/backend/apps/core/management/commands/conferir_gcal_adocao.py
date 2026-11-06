"""
Command: confere no Google, só lendo, os Event IDs que a adoção da virada (`gcal_adocao`) gravaria.

Uso (logo antes da adoção; o arquivo vale 24 h):
    python manage.py conferir_gcal_adocao --path <dir do export> --saida /tmp/conferido.json --operador <id>
    python manage.py import_export_contract --path <dir do export> --mode virada --apply \\
        --allow-entity gcal_adocao --gcal-verificado /tmp/conferido.json

Decisão do dono D63 (20/10/2026): a adoção só grava o id depois de conferir no Google que o evento existe,
está confirmado e tem a mesma data (em America/Fortaleza) que o evento do sistema. Os candidatos são os do
`gcal_adocao` (`ExportContractImporter.candidatos_gcal_adocao`, mesma regra). Para cada um, só GET na agenda
da organização (`GCAL_OAUTH_CALENDAR_ID`; vazio ou 'primary' é erro). Erro de leitura (403, 5xx, timeout)
não aprova, e `dateTime` sem fuso também (o fuso do servidor não decide o dia). O arquivo `--saida` traz só
os aprovados: {solicitacao_id: {event_id, verificado_em, inicio_google}}; o antigo é apagado antes de tudo e o
novo é gravado de uma vez (temporário + os.replace), então a conferência que falha não deixa arquivo. A saída
só traz contagens por motivo e s<id>: nada de título, nome, e-mail ou CPF.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from apps.core.models import Usuario
from apps.core.services.export_contract_importer import ExportContractImporter, data_inicio_google
from apps.core.services.gcal_client_factory import get_oauth_client_for_user

logger = logging.getLogger(__name__)

_FORTALEZA = ZoneInfo("America/Fortaleza")
MOTIVOS = (
    "aprovado",
    "ausente_no_google",
    "cancelado_no_google",
    "nao_confirmado",
    "outra_data",
    "erro_de_leitura",
)


def _inicio_bruto(evento: dict[str, Any]) -> str:
    """O início que o Google devolveu: `start.dateTime` ou, no evento de dia inteiro, `start.date`."""
    start = evento.get("start") or {}
    bruto = start.get("dateTime") or start.get("date")
    if not bruto:
        raise ValueError("evento sem start")
    return str(bruto)


def _gravar(caminho: str, dados: dict[str, Any]) -> None:
    """Grava o JSON de uma vez: temporário no mesmo diretório e `os.replace`."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(caminho)), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, caminho)
    except BaseException:
        os.unlink(tmp)
        raise


class Command(BaseCommand):
    help = (
        "Confere no Google (só GET) os Event IDs que a adoção da virada gravaria e grava o arquivo que o "
        "--gcal-verificado do import_export_contract exige. Nunca escreve no Google. Montar o cliente pode "
        "renovar o token do operador (grava a credencial e um AuditLog GOOGLE_REFRESH_TOKEN) e, no "
        "invalid_grant, desconectar a conta Google dele (apaga a credencial e grava GOOGLE_DISCONNECT), como "
        "no uso normal."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--path", required=True, help="Diretório do export-contract (o mesmo da adoção).")
        parser.add_argument("--saida", required=True, help="Arquivo JSON a gravar com os ids aprovados.")
        parser.add_argument("--operador", type=int, required=True, help="Id do usuário cuja conta Google lê.")

    def handle(self, *args: Any, **options: Any) -> None:
        # Antes de qualquer checagem: a conferência que falha não pode deixar o arquivo de outra rodada.
        if os.path.exists(options["saida"]):
            os.remove(options["saida"])
        agenda = str(getattr(settings, "GCAL_OAUTH_CALENDAR_ID", "") or "")
        if not agenda or agenda == "primary":
            raise CommandError("GCAL_OAUTH_CALENDAR_ID vazio ou 'primary': a conferência só lê a agenda da organização")
        path: str = options["path"]
        if not os.path.exists(os.path.join(path, "solicitacao.csv")):
            raise CommandError("--path sem solicitacao.csv")
        operador_id: int = options["operador"]
        operador = Usuario.objects.filter(pk=operador_id).first()
        if operador is None:
            raise CommandError(f"Operador u{operador_id} não existe")
        try:
            client, _ = get_oauth_client_for_user(operador)
        except ValueError as e:
            raise CommandError(f"Sem cliente Google para u{operador_id}: {type(e).__name__}") from e
        if not client.calendar_accessible(agenda):
            raise CommandError(f"A conta Google de u{operador_id} não enxerga a agenda da organização")

        candidatos = ExportContractImporter(path=path, mode="virada").candidatos_gcal_adocao()
        ids: dict[str, list[str]] = {k: [] for k in MOTIVOS}
        aprovados: dict[str, dict[str, str]] = {}
        for sid, eid, inicio in candidatos:
            try:
                evento = client.get(agenda, eid)
                if evento is None:
                    motivo = "ausente_no_google"
                elif evento.get("status") == "cancelled":
                    motivo = "cancelado_no_google"
                elif evento.get("status") != "confirmed":
                    motivo = "nao_confirmado"
                else:
                    bruto = _inicio_bruto(evento)
                    dia = data_inicio_google(bruto)
                    motivo = "aprovado" if dia == timezone.localtime(inicio, _FORTALEZA).date() else "outra_data"
                    if motivo == "aprovado":
                        aprovados[str(sid)] = {
                            "event_id": eid,
                            "verificado_em": timezone.now().isoformat(),
                            "inicio_google": bruto,
                        }
            except Exception as e:  # falha fechada: qualquer erro de leitura não aprova  # noqa: BLE001
                logger.warning("conferir_gcal_adocao: s%s não lido (%s)", sid, type(e).__name__)
                motivo = "erro_de_leitura"
            ids[motivo].append(f"s{sid}")

        _gravar(options["saida"], aprovados)

        out = self.stdout
        out.write(f"conferidos={len(candidatos)} aprovados={len(aprovados)} saida={options['saida']}")
        for motivo in MOTIVOS:
            lista = ids[motivo]
            out.write(f"  {motivo}: {len(lista)}" + (f" [{' '.join(lista)}]" if lista else ""))
        if ids["erro_de_leitura"]:
            out.write(self.style.WARNING(f"  {len(ids['erro_de_leitura'])} não lidos: rode de novo antes da adoção"))
