import csv
import io
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.config import sheets_config
from ingestao.models_disponibilidade_staging import DispStaging


def csv_url(sheet_id, gid):
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    )


def fetch(sheet_id, gid):
    url = csv_url(sheet_id, gid)
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8", errors="replace")


class Command(BaseCommand):
    help = "Importa disponibilidades para staging (ANUAL, DESLOCAMENTO, Bloqueios)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        tipos = [
            ("ANUAL", "ANUAL"),
            ("DESLOCAMENTO", "DESLOCAMENTO"),
            ("Bloqueios", "BLOQUEIOS"),
        ]
        total = 0

        with transaction.atomic():
            for key, tipo in tipos:
                gid = sheets_config.ABAS_DISPONIBILIDADE.get(key, "")
                if not gid:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  [SKIP] Sem GID para {key}")
                    )
                    continue

                try:
                    data = fetch(sheets_config.DISPONIBILIDADE_2025_ID, gid)
                    rows = list(csv.DictReader(io.StringIO(data)))
                    self.stdout.write(f"📊 [{key}] {len(rows)} linhas")

                    for i, row in enumerate(rows, start=1):
                        DispStaging.objects.update_or_create(
                            tipo=tipo, linha=i, defaults={"raw": row}
                        )
                    total += len(rows)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Erro em {key}: {e}"))

            if opts.get("dry_run"):
                self.stdout.write(self.style.WARNING("\n⚠️  DRY-RUN: rollback"))
                raise SystemExit(0)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Total staging: {total} registros"))
