"""
Command: Sincroniza pré-agenda (Solicitações aprovadas) com Google Calendar

Uso:
    python manage.py preagenda_to_gcal [options]

Opções:
    --calendar-id ID         Override GCAL_CALENDAR_ID
    --client fake|google     Tipo de client (default: GCAL_CLIENT setting = 'fake')
                             'fake'  = in-memory, safe, sem side effects (validação)
                             'google' = real API (requer GoogleCalendarClient implementado)
    --since DATETIME         Data início (ISO8601), padrão: 90 dias atrás
    --until DATETIME         Data fim (ISO8601), padrão: 180 dias à frente
    --ids CSV                IDs específicos (separados por vírgula)
    --no-delete              Não deleta eventos de solicitações não-aprovadas
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false
    --dry-run                Simula sem alterar DB/Calendar
    --verbose                Imprime detalhes de cada operação
    --batch-size N           Processa em chunks de N registros (default: 200, 0=todos)

Exemplos:
    # Dry-run completo com fake client (validação de fluxo)
    python manage.py preagenda_to_gcal --dry-run --verbose

    # Validar com fake client (sem publicar no Google)
    python manage.py preagenda_to_gcal --client=fake --verbose

    # Publicar no Google Calendar real (requer GoogleCalendarClient)
    python manage.py preagenda_to_gcal --client=google

    # Janela específica
    python manage.py preagenda_to_gcal --since 2025-01-01T00:00:00 --until 2025-12-31T23:59:59

    # IDs específicos
    python manage.py preagenda_to_gcal --ids 1,2,3 --dry-run
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.core.models import Solicitacao
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.services.gcal_sync_service import upsert_one


class Command(BaseCommand):
    help = "Sincroniza solicitações aprovadas com o Google Calendar (pré-agenda)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--calendar-id",
            type=str,
            default=None,
            help="Override GCAL_CALENDAR_ID from settings",
        )
        parser.add_argument(
            "--client",
            type=str,
            choices=["fake", "google"],
            default=None,
            help="Tipo de client: 'fake' (in-memory, safe) ou 'google' (real API). Default: GCAL_CLIENT setting",
        )
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Data início (ISO8601), padrão: 90 dias atrás",
        )
        parser.add_argument(
            "--until",
            type=str,
            default=None,
            help="Data fim (ISO8601), padrão: 180 dias à frente",
        )
        parser.add_argument(
            "--ids",
            type=str,
            default=None,
            help="CSV de IDs específicos (ex: 1,2,3)",
        )
        parser.add_argument(
            "--no-delete",
            action="store_true",
            help="Não deleta eventos de solicitações não-aprovadas",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sem alterar DB/Calendar",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Imprime detalhes de cada operação",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Processa em chunks de N registros (default: 200, 0=todos)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output JSON estruturado (para automação/Celery)",
        )

    def handle(self, *args: Any, **options: Any) -> int:
        # Timestamp início
        start_time = time.time()
        started_at = timezone.now()
        run_id = str(uuid.uuid4())
        output_json = options.get("json", False)

        # Extrair calendar_id
        cal_id = options["calendar_id"] or getattr(settings, "GCAL_CALENDAR_ID", None)

        if not cal_id:
            if output_json:
                self.stdout.write(
                    json.dumps(
                        {
                            "error": True,
                            "message": "GCAL_CALENDAR_ID não configurado e --calendar-id não informado.",
                            "meta": {"run_id": run_id},
                        },
                        ensure_ascii=False,
                    )
                )
                return
            self.stderr.write(
                self.style.ERROR(
                    "GCAL_CALENDAR_ID não configurado e --calendar-id não informado."
                )
            )
            self.stderr.write("Configure GCAL_CALENDAR_ID no .env ou use --calendar-id")
            sys.exit(2)

        # Extrair filtros temporais
        now = timezone.now()

        if options["since"]:
            try:
                since_dt = datetime.fromisoformat(options["since"])
                since = timezone.make_aware(since_dt, timezone.utc)
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(
                        f"Formato inválido para --since: {options['since']}"
                    )
                )
                sys.exit(2)
        else:
            since = now - timedelta(days=90)

        if options["until"]:
            try:
                until_dt = datetime.fromisoformat(options["until"])
                until = timezone.make_aware(until_dt, timezone.utc)
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(
                        f"Formato inválido para --until: {options['until']}"
                    )
                )
                sys.exit(2)
        else:
            until = now + timedelta(days=180)

        # Configurar opções
        dry_run = options["dry_run"]
        no_delete = options["no_delete"]
        verbose = options["verbose"]
        batch_size = options["batch_size"]

        # Construir queryset
        qs = Solicitacao.objects.filter(inicio__lte=until, fim__gte=since)

        if options["ids"]:
            ids = [int(x) for x in options["ids"].split(",") if x.strip().isdigit()]
            if not ids:
                self.stderr.write(self.style.ERROR(f"IDs inválidos: {options['ids']}"))
                sys.exit(2)
            qs = qs.filter(id__in=ids)

        # ================================================================
        # CONCURRENCY SAFETY: select_for_update() no queryset
        # ================================================================
        # Aplicar lock no queryset (apenas quando não é dry-run)
        if not dry_run:
            qs = qs.select_for_update()

        qs = qs.select_related("usuario", "municipio", "tipo_evento").order_by("id")

        # Inicializar cliente (plugável: fake ou google)
        client_type = options["client"] or getattr(settings, "GCAL_CLIENT", "fake")

        if client_type == "google":
            # Cliente real Google Calendar API
            from apps.core.services.gcal_google_client import GoogleCalendarClient

            client = GoogleCalendarClient()
        else:
            # Cliente fake (in-memory, safe para testes e validação de fluxo)
            client = FakeCalendarClient()
            if not output_json:
                self.stdout.write(
                    self.style.WARNING(
                        f"[CLIENT: fake] Usando FakeCalendarClient (in-memory, sem side effects)"
                    )
                )

        # Avisos
        if dry_run and not output_json:
            self.stdout.write(
                self.style.WARNING("[DRY-RUN MODE] Nenhuma alteração será feita")
            )

        # ================================================================
        # REDIS LOCK (Single-Flight com escopo)
        # ================================================================
        # Lock key com escopo: preagenda_to_gcal:lock:{calendar_id}:{since}:{until}
        # Evita execuções concorrentes do mesmo escopo
        lock_key = (
            f"preagenda_to_gcal:lock:{cal_id}:{since.isoformat()}:{until.isoformat()}"
        )
        lock_timeout = 300  # 5 minutos TTL

        if not cache.add(lock_key, "locked", timeout=lock_timeout):
            self.stderr.write(
                self.style.ERROR("❌ Outra instância já está processando este escopo.")
            )
            self.stderr.write(f"   Lock key: {lock_key}")
            self.stderr.write(f"   Aguarde {lock_timeout}s ou use escopo diferente.")
            sys.exit(1)

        try:
            # Métricas
            created = 0
            updated = 0
            adopted = 0
            deleted = 0
            skipped = 0

            total = qs.count()
            if not output_json:
                self.stdout.write(f"Processando {total} solicitações...")
                self.stdout.write(f"Calendário: {cal_id}")
                self.stdout.write(f"Período: {since:%Y-%m-%d} a {until:%Y-%m-%d}")
                self.stdout.write("")

            # ================================================================
            # CHUNKED PROCESSING: Processa em batches para evitar lock timeout
            # ================================================================
            # Se batch_size=0, processa todos de uma vez (legacy behavior)
            # Caso contrário, usa iterator() com chunks

            if batch_size <= 0 or dry_run:
                # Processamento em lote único (ou dry-run, que não precisa de lock)
                with transaction.atomic():
                    for s in qs:
                        outcome = upsert_one(
                            client=client,
                            calendar_id=cal_id,
                            s=s,
                            dry_run=dry_run,
                            no_delete=no_delete,
                        )

                        # Atualizar métricas
                        if outcome.action == "CREATE":
                            created += 1
                        elif outcome.action == "UPDATE":
                            updated += 1
                        elif outcome.action == "ADOPT":
                            adopted += 1
                        elif outcome.action == "DELETE":
                            deleted += 1
                        else:
                            skipped += 1

                        # Verbose output (suppress in JSON mode)
                        if verbose and not output_json:
                            icon = {
                                "CREATE": "✓",
                                "UPDATE": "↻",
                                "ADOPT": "⤴",
                                "DELETE": "✗",
                                "SKIP": "-",
                            }.get(outcome.action, " ")

                            self.stdout.write(
                                f"{icon} {outcome.action:8} #{outcome.solicitation_id:4} → {outcome.summary}"
                            )
            else:
                # Processamento em chunks com renovação opcional de lock
                # Note: select_for_update() não é compatível com iterator(),
                # então removemos o lock e processamos chunk por chunk
                qs_no_lock = qs._chain()  # Clone sem select_for_update
                qs_no_lock.query.select_for_update = False
                qs_no_lock.query.select_for_update_nowait = False
                qs_no_lock.query.select_for_update_skip_locked = False
                qs_no_lock.query.select_for_update_of = ()

                processed_count = 0

                for s in qs_no_lock.iterator(chunk_size=batch_size):
                    # Processar individualmente dentro de mini-transaction
                    with transaction.atomic():
                        # Re-fetch com select_for_update para garantir lock
                        s_locked = Solicitacao.objects.select_for_update().get(pk=s.pk)

                        outcome = upsert_one(
                            client=client,
                            calendar_id=cal_id,
                            s=s_locked,
                            dry_run=dry_run,
                            no_delete=no_delete,
                        )

                        # Atualizar métricas
                        if outcome.action == "CREATE":
                            created += 1
                        elif outcome.action == "UPDATE":
                            updated += 1
                        elif outcome.action == "ADOPT":
                            adopted += 1
                        elif outcome.action == "DELETE":
                            deleted += 1
                        else:
                            skipped += 1

                        # Verbose output (suppress in JSON mode)
                        if verbose and not output_json:
                            icon = {
                                "CREATE": "✓",
                                "UPDATE": "↻",
                                "ADOPT": "⤴",
                                "DELETE": "✗",
                                "SKIP": "-",
                            }.get(outcome.action, " ")

                            self.stdout.write(
                                f"{icon} {outcome.action:8} #{outcome.solicitation_id:4} → {outcome.summary}"
                            )

                    processed_count += 1

                    # Renovar lock a cada chunk (graceful fallback se touch não disponível)
                    if processed_count % batch_size == 0:
                        try:
                            # Tentar renovar lock para evitar timeout
                            if hasattr(cache, "touch"):
                                cache.touch(lock_key, lock_timeout)
                                if verbose:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"[LOCK RENEWED] {processed_count} processados"
                                        )
                                    )
                        except (AttributeError, NotImplementedError):
                            # Backend de cache não suporta touch, continuar normalmente
                            pass

            # ================================================================
            # OUTPUT FINAL: JSON (para automação/Celery) ou HUMAN-READABLE
            # ================================================================
            finished_at = timezone.now()
            duration_ms = int((time.time() - start_time) * 1000)

            if output_json:
                # JSON output (regra de ouro: apenas JSON em stdout, logs em stderr)
                result = {
                    "meta": {
                        "calendar_id": cal_id,
                        "client": client_type,
                        "since": since.isoformat(),
                        "until": until.isoformat(),
                        "dry_run": dry_run,
                        "batch_size": batch_size,
                        "run_id": run_id,
                        "started_at": started_at.isoformat(),
                        "finished_at": finished_at.isoformat(),
                        "duration_ms": duration_ms,
                    },
                    "totals": {
                        "CREATE": created,
                        "UPDATE": updated,
                        "ADOPT": adopted,
                        "DELETE": deleted,
                        "SKIP": skipped,
                        "total": created + updated + adopted + deleted + skipped,
                    },
                }
                self.stdout.write(json.dumps(result, ensure_ascii=False, default=str))
            else:
                # Human-readable output
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("RESUMO"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(f"Total processado: {total}")
                self.stdout.write(f"  CREATE:  {created:4} (novos eventos)")
                self.stdout.write(f"  UPDATE:  {updated:4} (eventos atualizados)")
                self.stdout.write(f"  ADOPT:   {adopted:4} (eventos adotados)")
                self.stdout.write(f"  DELETE:  {deleted:4} (eventos removidos)")
                self.stdout.write(f"  SKIP:    {skipped:4} (não processados)")
                self.stdout.write("")

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            "Nenhuma alteração foi feita (modo dry-run). "
                            "Execute sem --dry-run para aplicar."
                        )
                    )

        finally:
            # ================================================================
            # LIBERAR LOCK
            # ================================================================
            cache.delete(lock_key)

        return 0
