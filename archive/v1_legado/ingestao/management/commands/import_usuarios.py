"""
Comando canônico de importação de usuários (origem=planilha, is_provisorio=True).
Suporta ingestão dual: Google Sheets ou CSV local.

DIA 3: Idempotência por SHA1 + Relatório de Auditoria completo
"""

import csv

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ingestao.utils import sha1_of_row


class Command(BaseCommand):
    help = "Importa usuários (SSOT Sheets/CSV) — idempotente por SHA1, com relatório"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Caminho do CSV exportado da aba canônica")
        parser.add_argument(
            "--fonte", default="Usuarios2025", help="Identificador lógico da fonte"
        )
        parser.add_argument("--sheet-id", default="", help="ID do Google Sheet")
        parser.add_argument("--gid", default="", help="GID da aba")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        path = opts["csv_path"]
        fonte = opts["fonte"]
        dry = opts["dry_run"]
        sheet_id = opts["sheet_id"]
        gid = opts["gid"]

        User = get_user_model()
        MarcadorPlanilha = apps.get_model("core", "MarcadorPlanilha")

        created = updated = skipped = 0
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
                    self.stdout.write(f"DRY: {payload.get('email')}")
                else:
                    email = (payload.get("email") or payload.get("Email") or "").strip()
                    nome_completo = (
                        payload.get("Nome Completo")
                        or payload.get("nome_completo")
                        or ""
                    ).strip()
                    nome = (payload.get("Nome") or payload.get("nome") or "").strip()
                    cpf = (payload.get("CPF") or payload.get("cpf") or "").strip()

                    # Se não tem email, gerar um baseado no CPF ou nome
                    if not email:
                        if cpf:
                            email = f"user_{cpf}@aprender.local"
                        else:
                            email = f"user_{sha1_of_row({'n': nome_completo or nome})[:8]}@aprender.local"

                    # Dividir nome completo em first_name e last_name
                    if nome_completo:
                        partes = nome_completo.split()
                        first_name = partes[0] if partes else ""
                        last_name = " ".join(partes[1:]) if len(partes) > 1 else ""
                    else:
                        first_name = nome
                        last_name = ""

                    username_fallback = email.split("@")[0][
                        :150
                    ]  # Username sem @domain

                    user, was_created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            "first_name": first_name,
                            "last_name": last_name,
                            "username": username_fallback,
                        },
                    )

                    if was_created:
                        created += 1
                    else:
                        # Atualizações leves
                        User.objects.filter(pk=user.pk).update(
                            first_name=first_name or user.first_name,
                            last_name=last_name or user.last_name,
                        )
                        updated += 1

                    # Registrar marcador para idempotência
                    MarcadorPlanilha.objects.create(
                        external_hash=h,
                        tipo_entidade="usuario",
                        entidade_id=None,  # Não temos UUID de Usuario
                        raw_data=payload,
                        origem=f"import_usuarios:{fonte}",
                        origem_aba=fonte,
                        gid=gid or "",
                        cancelado_flag=False,
                    )

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
                    / f"GSHEETS_CROSSCHECK_import_usuarios_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            self.style.SUCCESS("📊 RELATÓRIO DE AUDITORIA - import_usuarios")
        )
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"Fonte: {fonte}")
        self.stdout.write(f"Sheet ID: {sheet_id or 'N/A'}")
        self.stdout.write(f"GID: {gid or 'N/A'}")
        self.stdout.write(f"Arquivo: {path}")
        self.stdout.write("")
        self.stdout.write(f"✅ Criados: {created}")
        self.stdout.write(f"🔄 Atualizados: {updated}")
        self.stdout.write(f"⏭️  Pulados (já importados): {skipped}")
        self.stdout.write("")
        self.stdout.write("📝 Amostra de hashes (primeiros 10):")
        for i, h in enumerate(sample, 1):
            self.stdout.write(f"   {i}. {h}")
        self.stdout.write(self.style.SUCCESS("=" * 70))

        if dry:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN: Nenhuma alteração foi salva no banco")
            )

        return 0
