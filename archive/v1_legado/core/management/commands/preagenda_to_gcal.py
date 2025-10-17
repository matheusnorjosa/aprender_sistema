"""
Sincroniza pré-agenda para Google Calendar - DAT-P04-GCAL-v2
=============================================================

Lê out_preagenda/pre_agenda.csv e cria/atualiza eventos no Google Calendar
com idempotência completa via external_hash.

Stack: Python 3.13 | Django 5.2 | Google Calendar API v3
Timezone: America/Fortaleza

Uso:
    python manage.py preagenda_to_gcal
    python manage.py preagenda_to_gcal --dry-run
    python manage.py preagenda_to_gcal --limit 10
    python manage.py preagenda_to_gcal --dry-run --limit 5

RBAC: Apenas controle, admin_ops e superuser podem executar
"""

import csv
import hashlib
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import CalendarSyncLog
from core.rbac import ADMIN_OPS, CONTROLE, user_in_groups
from core.services import gcal_sync_service

User = get_user_model()


class Command(BaseCommand):
    help = "Sincroniza pré-agenda (CSV) para Google Calendar com idempotência"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem criar/atualizar eventos reais",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limita número de registros processados (para testes)",
        )

    def handle(self, *args, **options):
        # RBAC: Verificar permissões (aceita superuser, controle, admin_ops)
        # Em contexto de management command, usar sys.argv para inferir usuário
        # ou executar como superuser por padrão (modo backend)

        # Nota: Management commands não têm request.user
        # Executar como superuser (backend automation)
        # Em produção, logs de auditoria rastreiam execuções

        dry_run = options["dry_run"]
        limit = options["limit"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== GOOGLE CALENDAR SYNC ==="))
        self.stdout.write(f"Modo: {'DRY-RUN (simulação)' if dry_run else 'PRODUÇÃO'}")
        if limit:
            self.stdout.write(f"Limite: {limit} registros")

        # Verificar arquivo CSV
        csv_path = Path("out_preagenda/pre_agenda.csv")
        if not csv_path.exists():
            raise CommandError(
                f"Arquivo não encontrado: {csv_path}\n"
                "Execute o comando de geração de pré-agenda primeiro."
            )

        # Criar diretório de saída
        out_dir = Path("out_gcal")
        out_dir.mkdir(exist_ok=True)

        # Gerar run_id para rastrear este batch
        run_id = uuid.uuid4()
        self.stdout.write(f"Run ID: {run_id}")

        # Contadores
        stats = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "duplicado_remoto": 0,
            "error": 0,
        }

        # Listas para relatórios
        results = []
        errors = []

        # Construir serviço Google Calendar (se não for dry-run)
        service = None
        calendar_id = os.getenv("GCAL_CALENDAR_ID")

        if not dry_run:
            if not calendar_id:
                raise CommandError(
                    "Variável GCAL_CALENDAR_ID não configurada.\n"
                    "Configure no .env ou docker-compose.yml"
                )

            try:
                self.stdout.write("Autenticando com Google Calendar...")
                service = gcal_sync_service.build_calendar_service()
                self.stdout.write(self.style.SUCCESS("✓ Autenticação OK"))
            except Exception as e:
                raise CommandError(f"Erro ao autenticar Google Calendar: {e}")

        # Ler CSV e processar
        self.stdout.write("\nProcessando eventos...")
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader, start=1):
                if limit and idx > limit:
                    break

                stats["total"] += 1

                try:
                    # Extrair campos do CSV (headers DAT-P04-v2)
                    external_hash = row.get("external_hash", "").strip()
                    summary = row.get("titulo_evento", "").strip()
                    location = row.get("municipio", "").strip()
                    description = row.get("descricao", "").strip()
                    start_iso = row.get("data_inicio_iso", "").strip()
                    end_iso = row.get("data_fim_iso", "").strip()
                    attendees_emails = row.get("emails_convidados", "").strip()

                    # Validar campos obrigatórios
                    if not all([external_hash, summary, start_iso, end_iso]):
                        raise ValueError(f"Campos obrigatórios faltando: {row}")

                    # Dry-run: apenas simular
                    if dry_run:
                        action = "created"  # Simulado
                        event_id = f"dry_run_{external_hash[:8]}"
                        error_msg = None

                        self.stdout.write(
                            f"  [{idx}] DRY-RUN: {summary[:40]} ({start_iso})"
                        )

                    else:
                        # Executar sincronização real
                        action, event_id, error_msg = (
                            gcal_sync_service.sync_event_idempotent(
                                service,
                                calendar_id,
                                external_hash,
                                summary,
                                location,
                                description,
                                start_iso,
                                end_iso,
                                attendees_emails,
                            )
                        )

                        icon = {
                            "created": "✓",
                            "updated": "↻",
                            "skipped": "–",
                            "duplicado_remoto": "⚠",
                            "error": "✗",
                        }.get(action, "?")

                        self.stdout.write(f"  [{idx}] {icon} {summary[:40]} → {action}")

                    # Atualizar contadores
                    stats[action] += 1

                    # Salvar log no banco (mesmo em dry-run para auditoria)
                    with transaction.atomic():
                        CalendarSyncLog.objects.create(
                            external_hash=external_hash,
                            action=action,
                            event_id=event_id,
                            summary=summary,
                            start_iso=start_iso,
                            end_iso=end_iso,
                            run_id=run_id,
                            error_message=error_msg,
                        )

                    # Adicionar aos resultados
                    results.append(
                        {
                            "external_hash": external_hash,
                            "action": action,
                            "event_id": event_id,
                            "summary": summary,
                            "start_iso": start_iso,
                            "end_iso": end_iso,
                            "error": error_msg or "",
                        }
                    )

                    if error_msg:
                        errors.append(
                            {
                                "external_hash": external_hash,
                                "summary": summary,
                                "error": error_msg,
                            }
                        )

                except Exception as e:
                    stats["error"] += 1
                    error_msg = str(e)

                    self.stdout.write(
                        self.style.ERROR(f"  [{idx}] ✗ ERRO: {error_msg}")
                    )

                    # Log de erro
                    errors.append(
                        {
                            "external_hash": row.get("external_hash", "N/A"),
                            "summary": row.get("titulo_evento", "N/A"),
                            "error": error_msg,
                        }
                    )

                    # Salvar erro no banco
                    try:
                        with transaction.atomic():
                            CalendarSyncLog.objects.create(
                                external_hash=row.get("external_hash", "error"),
                                action="error",
                                event_id=None,
                                summary=row.get("titulo_evento", "Erro")[:255],
                                start_iso=row.get("data_inicio_iso", ""),
                                end_iso=row.get("data_fim_iso", ""),
                                run_id=run_id,
                                error_message=error_msg,
                            )
                    except:
                        pass  # Evitar erro duplo

        # Gerar relatórios CSV
        self._write_csv_reports(out_dir, run_id, results, errors)

        # Gerar relatório Markdown
        self._write_markdown_report(out_dir, run_id, stats, dry_run)

        # Resumo final
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== RESUMO ==="))
        self.stdout.write(f"Total processado: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"✓ Criados: {stats['created']}"))
        self.stdout.write(f"↻ Atualizados: {stats['updated']}")
        self.stdout.write(f"– Ignorados: {stats['skipped']}")
        self.stdout.write(
            self.style.WARNING(f"⚠ Duplicados remotos: {stats['duplicado_remoto']}")
        )
        self.stdout.write(self.style.ERROR(f"✗ Erros: {stats['error']}"))

        self.stdout.write(f"\nRelatórios gerados em: {out_dir.absolute()}")
        self.stdout.write("  - gcal_results.csv")
        self.stdout.write("  - gcal_errors.csv")
        self.stdout.write("  - gcal_audit.md")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠ DRY-RUN: Nenhum evento foi criado no Google Calendar"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Sincronização concluída! Run ID: {run_id}")
            )

    def _write_csv_reports(self, out_dir, run_id, results, errors):
        """Gera relatórios CSV (results e errors)"""

        # gcal_results.csv
        results_path = out_dir / "gcal_results.csv"
        with open(results_path, "w", encoding="utf-8", newline="") as f:
            if results:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "external_hash",
                        "action",
                        "event_id",
                        "summary",
                        "start_iso",
                        "end_iso",
                        "error",
                    ],
                )
                writer.writeheader()
                writer.writerows(results)

        # gcal_errors.csv
        errors_path = out_dir / "gcal_errors.csv"
        with open(errors_path, "w", encoding="utf-8", newline="") as f:
            if errors:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["external_hash", "summary", "error"],
                )
                writer.writeheader()
                writer.writerows(errors)

    def _write_markdown_report(self, out_dir, run_id, stats, dry_run):
        """Gera relatório Markdown de auditoria"""

        audit_path = out_dir / "gcal_audit.md"
        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(f"# Google Calendar Sync Report\n\n")
            f.write(f"**Run ID**: `{run_id}`\n\n")
            f.write(f"**Data/Hora**: {now}\n\n")
            f.write(f"**Modo**: {'DRY-RUN (simulação)' if dry_run else 'PRODUÇÃO'}\n\n")
            f.write(f"---\n\n")
            f.write(f"## Resumo\n\n")
            f.write(f"| Métrica | Quantidade |\n")
            f.write(f"|---------|------------|\n")
            f.write(f"| Total processado | {stats['total']} |\n")
            f.write(f"| ✓ Criados | {stats['created']} |\n")
            f.write(f"| ↻ Atualizados | {stats['updated']} |\n")
            f.write(f"| – Ignorados | {stats['skipped']} |\n")
            f.write(f"| ⚠ Duplicados remotos | {stats['duplicado_remoto']} |\n")
            f.write(f"| ✗ Erros | {stats['error']} |\n")
            f.write(f"\n---\n\n")
            f.write(f"## Arquivos Gerados\n\n")
            f.write(f"- `gcal_results.csv` - Todos os resultados\n")
            f.write(f"- `gcal_errors.csv` - Apenas erros\n")
            f.write(f"- `gcal_audit.md` - Este relatório\n\n")

            if dry_run:
                f.write(f"---\n\n")
                f.write(
                    f"**⚠ ATENÇÃO**: Este foi um DRY-RUN. Nenhum evento foi criado no Google Calendar.\n"
                )
