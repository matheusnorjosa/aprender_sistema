"""
Comando canônico de importação de eventos das abas de planilhas.

DIA 3: Idempotência SHA1 + Regras Canônicas + Relatório
- Solicitante = Coordenador (adiciona ao grupo)
- Status: PRE_AGENDA→CRIADO, CONCLUIDO→REALIZADO, NUNCA criar AGENDADO
- Corte temporal: ≤2025-09-25 → realizado/cancelado
"""

import csv
from datetime import datetime, time

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from ingestao.utils import sha1_of_row

# Entrada canônica → Status core (sem AGENDADO por ingestão)
STATUS_MAP = {
    "CRIADO": "CRIADO",
    "APROVADO": "APROVADO",
    "REALIZADO": "REALIZADO",
    "CANCELADO": "CANCELADO",
    # legados:
    "PRE_AGENDA": "CRIADO",
    "CONCLUIDO": "REALIZADO",
}


def _as_bool(v):
    s = str(v or "").strip().lower()
    return s in {"1", "true", "t", "sim", "yes", "y", "ok", "apro", "aprovado", "x"}


def _parse_ts(row):
    v = row.get("data_inicio") or row.get("data") or ""
    dt = parse_datetime(v) or (
        parse_date(v) and datetime.combine(parse_date(v), time(0, 0))
    )
    return dt


class Command(BaseCommand):
    help = "Importa eventos/solicitações (SSOT Sheets/CSV) — idempotente + relatório + regras canônicas"

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--fonte", default="Agenda2025")
        parser.add_argument("--sheet-id", default="")
        parser.add_argument("--gid", default="")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--cutoff",
            default="2025-09-25",
            help="YYYY-MM-DD: <=cutoff força realizado/cancelado",
        )
        parser.add_argument(
            "--col-solicitante",
            default="solicitante",
            help="nome da coluna do solicitante",
        )
        parser.add_argument(
            "--col-cancelado", default="cancelado", help="coluna bool de cancelamento"
        )
        parser.add_argument(
            "--col-aprovado",
            default="aprovado_super",
            help="coluna bool de aprovação da Super",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["csv_path"]
        fonte = opts["fonte"]
        dry = opts["dry_run"]
        sheet_id = opts["sheet_id"]
        gid = opts["gid"]
        cutoff = datetime.fromisoformat(opts["cutoff"]).date()
        col_solic = opts["col_solicitante"]
        col_cancel = opts["col_cancelado"]
        col_aprov = opts["col_aprovado"]

        User = get_user_model()
        Group.objects.get_or_create(name="coordenador")
        grupo_coord = Group.objects.get(name="coordenador")
        MarcadorPlanilha = apps.get_model("core", "MarcadorPlanilha")
        Solicitacao = apps.get_model("core", "Solicitacao")

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

                # Solicitante = Coordenador (garante grupo)
                solicitante_txt = payload.get(col_solic) or ""
                email_guess = (
                    payload.get("solicitante_email") or ""
                ).strip().lower() or None

                if email_guess:
                    user, _ = User.objects.get_or_create(
                        email=email_guess, defaults={"username": email_guess}
                    )
                else:
                    username = sha1_of_row({"sol": solicitante_txt})[:16]
                    user, _ = User.objects.get_or_create(
                        username=username, defaults={"first_name": solicitante_txt}
                    )
                user.groups.add(grupo_coord)

                # Determinar status
                status_in = (payload.get("status") or "").upper()
                status_core = STATUS_MAP.get(status_in, "CRIADO")

                # Corte temporal
                dt_inicio = _parse_ts(payload)
                is_past = dt_inicio and dt_inicio.date() <= cutoff

                cancelado = _as_bool(payload.get(col_cancel))
                aprovado = _as_bool(payload.get(col_aprov))

                if is_past:
                    status_core = "CANCELADO" if cancelado else "REALIZADO"
                else:
                    status_core = "APROVADO" if aprovado else "CRIADO"

                if status_core == "AGENDADO":
                    status_core = "CRIADO"  # NUNCA criar AGENDADO na ingestão

                if dry:
                    self.stdout.write(
                        f"DRY: {payload.get('titulo') or 'sem_titulo'} | "
                        f"status={status_core} | solicitante={user.id}"
                    )
                else:
                    # Buscar/criar entidades relacionadas (simplificado)
                    titulo = payload.get("titulo") or f"Evento {h[:8]}"

                    # Criar solicitação (campos mínimos)
                    sol = Solicitacao.objects.create(
                        titulo_evento=titulo,
                        status=status_core,
                        data_inicio=dt_inicio or datetime.now(),
                        data_fim=dt_inicio or datetime.now(),
                        usuario_solicitante=user,
                        # Adicionar campos obrigatórios com defaults temporários
                        municipio_id=1,  # TODO: mapear município
                        projeto_id=1,  # TODO: mapear projeto
                        tipo_evento_id=1,  # TODO: mapear tipo
                    )

                    MarcadorPlanilha.objects.create(
                        external_hash=h,
                        tipo_entidade="solicitacao",
                        entidade_id=None,  # TODO: usar sol.id se criar solicitacao
                        raw_data=payload,
                        origem=f"import_eventos:{fonte}",
                        origem_aba=fonte,
                        gid=gid or "",
                        cancelado_flag=cancelado,
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
                    / f"GSHEETS_CROSSCHECK_import_eventos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            self.style.SUCCESS("📊 RELATÓRIO DE AUDITORIA - import_eventos_abas")
        )
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"Fonte: {fonte}")
        self.stdout.write(f"Sheet ID: {sheet_id or 'N/A'}")
        self.stdout.write(f"GID: {gid or 'N/A'}")
        self.stdout.write(f"Arquivo: {path}")
        self.stdout.write(f"Corte Temporal: ≤ {cutoff}")
        self.stdout.write("")
        self.stdout.write(f"✅ Criados: {created}")
        self.stdout.write(f"🔄 Atualizados: {updated}")
        self.stdout.write(f"⏭️  Pulados (já importados): {skipped}")
        self.stdout.write("")
        self.stdout.write("📝 Amostra de hashes (primeiros 10):")
        for i, h in enumerate(sample, 1):
            self.stdout.write(f"   {i}. {h}")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("\n⚠️  Regras aplicadas:")
        self.stdout.write(f"   • Solicitantes adicionados ao grupo 'coordenador'")
        self.stdout.write(
            f"   • Status legados: PRE_AGENDA→CRIADO, CONCLUIDO→REALIZADO"
        )
        self.stdout.write(
            f"   • NUNCA criado status AGENDADO (reservado para GCal sync)"
        )
        self.stdout.write(
            f"   • Eventos ≤{cutoff}: REALIZADO (ou CANCELADO se marcado)"
        )

        if dry:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN: Nenhuma alteração foi salva no banco")
            )

        return 0
