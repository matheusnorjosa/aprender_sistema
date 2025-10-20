"""
Comando canônico de importação de disponibilidades.

DIA 3: Idempotência SHA1 + Relatório
"""

import csv

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from ingestao.utils import sha1_of_row


class Command(BaseCommand):
    help = "Importa disponibilidades (staging heurístico) — idempotente + relatório"

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--fonte", default="Disp2025")
        parser.add_argument("--sheet-id", default="")
        parser.add_argument("--gid", default="")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["csv_path"]
        fonte = opts["fonte"]
        dry = opts["dry_run"]
        sheet_id = opts["sheet_id"]
        gid = opts["gid"]

        MarcadorPlanilha = apps.get_model("core", "MarcadorPlanilha")

        created = skipped = 0
        sample = []
        rows_local = []  # Para cross-check

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_local.append(row)  # Guardar para cross-check
                payload = {k.strip(): (v or "").strip() for k, v in row.items()}
                h = sha1_of_row(payload)

                if MarcadorPlanilha.objects.filter(external_hash=h).exists():
                    skipped += 1
                    continue

                if dry:
                    self.stdout.write(
                        f"DRY: {payload.get('tipo')} | {payload.get('usuario')}"
                    )
                else:
                    # Registrar marcador (dados ficam em staging para processamento posterior)
                    MarcadorPlanilha.objects.create(
                        external_hash=h,
                        tipo_entidade="disponibilidade",
                        entidade_id=None,
                        raw_data=payload,
                        origem=f"import_disp:{fonte}",
                        origem_aba=fonte,
                        gid=gid or "",
                        cancelado_flag=False,
                    )
                    created += 1

                if len(sample) < 10:
                    sample.append(h[:8] + "...")

        # Cross-check com Google Sheets (se configurado)
        if sheet_id and gid:
            try:
                import json
                import pathlib

                from django.utils import timezone

                from ingestao.crosscheck import crosscheck_sheet

                report = crosscheck_sheet(sheet_id, gid, rows_local)
                from django.conf import settings

                out = (
                    pathlib.Path(settings.DOCS_ROOT)
                    / f"GSHEETS_CROSSCHECK_import_disp_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                out.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                self.stdout.write(self.style.SUCCESS(f"[CROSS-CHECK] Salvo em: {out}"))
                self.stdout.write(f"  Local: {report['local_rows']} linhas")
                self.stdout.write(f"  Sheets: {report['sheet_rows']} linhas")
                self.stdout.write(
                    f"  Cobertura: {report['coverage_local_in_sheet_pct']}% (local em sheets)"
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"[CROSS-CHECK] Falhou: {e}; seguindo apenas com CSV local."
                    )
                )

        # Relatório final de auditoria
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(
            self.style.SUCCESS("📊 RELATÓRIO DE AUDITORIA - import_disponibilidades")
        )
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"Fonte: {fonte}")
        self.stdout.write(f"Sheet ID: {sheet_id or 'N/A'}")
        self.stdout.write(f"GID: {gid or 'N/A'}")
        self.stdout.write(f"Arquivo: {path}")
        self.stdout.write("")
        self.stdout.write(f"✅ Criados (marcadores): {created}")
        self.stdout.write(f"⏭️  Pulados (já importados): {skipped}")
        self.stdout.write("")
        self.stdout.write("📝 Amostra de hashes (primeiros 10):")
        for i, h in enumerate(sample, 1):
            self.stdout.write(f"   {i}. {h}")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("\nℹ️  Dados marcados para processamento posterior em staging")

        if dry:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN: Nenhuma alteração foi salva no banco")
            )

        return 0
