"""
ETL de Acompanhamento: Upsert idempotente de Solicitação + Participation.

Lê CSVs normalizados (eventos e participantes) e cria/atualiza:
- Solicitação por external_hash único
- Participation por (solicitacao, usuario, role) único

Regras de negócio:
- Setor mapeado por aba + projeto
- Status: data < hoje → aprovado; Super+SIM → aprovado; Else → pendente
- Super com múltiplos municípios → 1 Solicitação/município
- Outros sem formadores → Coordenador também FORMADOR
- Convidados (coluna T) ignorados neste ETL
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.core.models import Participation, Solicitacao
from apps.dat_ingest.services.acompanhamento_normalize import (
    hash_event_v2,
    normalize_sector,
    parse_date_iso,
    parse_time_iso,
    split_municipios_super,
)
from apps.dat_ingest.services.indicator_filter import should_create_participation
from apps.dat_ingest.services.resolvers import (
    resolve_municipio,
    resolve_projeto,
    resolve_tipo_evento,
    resolve_user_by_email,
    resolve_user_by_name,
)


class Command(BaseCommand):
    help = "ETL de Acompanhamento: upsert idempotente de Solicitação + Participation"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--events-csv",
            type=str,
            default="/app/data/csv-import/etl_eventos_normalizados.csv",
            help="Caminho do CSV de eventos",
        )
        parser.add_argument(
            "--participants-csv",
            type=str,
            default="/app/data/csv-import/etl_participantes_normalizados.csv",
            help="Caminho do CSV de participantes",
        )
        parser.add_argument(
            "--today",
            type=str,
            help="Data de referência (YYYY-MM-DD) para testes",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem writes no banco (mutually exclusive with --apply)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica writes no banco (com quality gates, mutually exclusive with --dry-run)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.dry_run = options.get("dry_run", False)
        self.apply = options.get("apply", False)
        self.events_csv = options["events_csv"]
        self.participants_csv = options["participants_csv"]

        # Mutual exclusivity: default to dry-run if neither specified
        if not self.dry_run and not self.apply:
            self.dry_run = True
        elif self.dry_run and self.apply:
            raise CommandError("--dry-run and --apply are mutually exclusive")

        # Timezone e data de referência
        self.tz = timezone.get_current_timezone()  # America/Fortaleza
        if options["today"]:
            self.today = parse_date_iso(options["today"])
        else:
            self.today = timezone.localdate()

        self.stdout.write(f"🚀 ETL Acompanhamento (dry_run={self.dry_run}, apply={self.apply})")
        self.stdout.write(f"   TZ: {self.tz}")
        self.stdout.write(f"   Today: {self.today}")
        self.stdout.write(f"   Events CSV: {self.events_csv}")
        self.stdout.write(f"   Participants CSV: {self.participants_csv}")

        # Stats e pendências
        self.stats = {
            "solicitacoes": {"created": 0, "updated": 0, "unchanged": 0},
            "participations": {"created": 0, "updated": 0},
            "skipped": {"autor": 0, "fk": 0, "intervalo_invalido": 0, "indicators": 0},
        }
        self.pendencias = {
            "usuarios": [],
            "municipios": [],
            "projetos": [],
            "tipos": [],
            "outros": [],
        }

        # Carregar CSVs
        self.stdout.write("\n📂 Carregando CSVs...")
        eventos = self.load_eventos_csv()
        participantes_map = self.load_participantes_csv()

        self.stdout.write(f"   {len(eventos)} eventos carregados")
        self.stdout.write(f"   {len(participantes_map)} grupos de participantes")

        # PR21: Quality Gates - calcular métricas antes de processar
        self.stdout.write("\n📊 Calculando métricas de qualidade...")
        metrics = self.calculate_metrics(eventos, participantes_map)

        # PR21: Detect violations (dry-run: apenas reporta; apply: aborta)
        violations = self.detect_violations(metrics)

        if violations:
            self.generate_violations_report(violations, metrics)
            if self.apply:
                # Apply: abortar se houver violações
                error_msg = f"❌ Quality gates violated ({len(violations)} gate(s)). Apply aborted.\n"
                error_msg += "\n".join(f"  - {v['gate']}: {v['message']}" for v in violations)
                raise CommandError(error_msg)
            else:
                # Dry-run: apenas warning
                self.stdout.write(self.style.WARNING(
                    f"   ⚠️  {len(violations)} violation(s) detectadas (dry-run: sem abortar)"
                ))
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ All quality gates passed"))

        # Sempre gerar relatório de métricas (dry-run ou apply)
        self.generate_metrics_report(metrics)

        # Processar eventos
        self.stdout.write("\n⚙️  Processando eventos...")
        with transaction.atomic():
            for evento in eventos:
                self.process_evento(evento, participantes_map)

            if self.dry_run:
                self.stdout.write("   [DRY-RUN] Rollback transaction")
                transaction.set_rollback(True)

        # Relatório
        self.generate_report()

        self.stdout.write(self.style.SUCCESS("\n✅ ETL concluído!"))

    def load_eventos_csv(self) -> list[dict[str, Any]]:
        """Carrega CSV de eventos em memória."""
        eventos = []
        with open(self.events_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                eventos.append(row)
        return eventos

    def load_participantes_csv(self) -> dict[str, list[dict[str, Any]]]:
        """
        Carrega CSV de participantes e agrupa por event_hash.

        Returns:
            {event_hash: [{"role": "COORDENADOR", "email": ..., "display_name": ...}]}
        """
        participantes_map = {}
        with open(self.participants_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                event_hash = row.get("event_hash", "").strip()
                if not event_hash:
                    continue

                if event_hash not in participantes_map:
                    participantes_map[event_hash] = []

                participantes_map[event_hash].append(row)

        return participantes_map

    def compute_external_hash(self, evento: dict[str, Any], coord_email: str, coord_name: str, participantes: list[dict[str, Any]] | None = None) -> str:
        """
        Gera external_hash SHA1 a partir de campos-chave do evento.

        PR21: Usa hash_event_v2 (17 campos) se USE_EXTERNAL_HASH_V2=True,
        caso contrário usa hash v1 (8 campos) para back-compat.

        Se event_hash vier do CSV, usa direto.
        """
        if evento.get("event_hash"):
            return evento["event_hash"].strip()

        # PR21: Use hash v2 se flag ativada
        if settings.USE_EXTERNAL_HASH_V2:
            # Extrair formadores dos participantes
            formadores = []
            if participantes:
                for p in participantes:
                    if p.get("role") == "FORMADOR":
                        email_or_name = p.get("email") or p.get("display_name", "")
                        formadores.append(email_or_name)

            # Preencher até 5 formadores
            while len(formadores) < 5:
                formadores.append("")

            # Construir row para hash_event_v2
            row = {
                "source_sheet": evento.get("source_sheet", ""),
                "municipio": evento.get("municipio", ""),
                "encontro": evento.get("encontro", ""),
                "tipo": evento.get("tipo", ""),
                "data": evento.get("data", ""),
                "hora_inicio": evento.get("hora_inicio", ""),
                "hora_fim": evento.get("hora_fim", ""),
                "projeto": evento.get("projeto", ""),
                "segmento": evento.get("segmento", ""),
                "coord_acompanha": evento.get("coord_acompanha", ""),
                "coordenador": coord_email if coord_email else coord_name,
                "formador1": formadores[0],
                "formador2": formadores[1],
                "formador3": formadores[2],
                "formador4": formadores[3],
                "formador5": formadores[4],
                "aprovacao": evento.get("aprovacao", ""),
            }

            return hash_event_v2(row)

        # Fallback: hash v1 (8 campos) para back-compat
        sector = normalize_sector(
            evento.get("source_sheet", ""), evento.get("projeto", "")
        )
        municipio = evento.get("municipio", "").strip()
        tipo = evento.get("tipo", "").strip()
        data = evento.get("data", "").strip()
        hora_inicio = evento.get("hora_inicio", "").strip()
        hora_fim = evento.get("hora_fim", "").strip()
        encontro = evento.get("encontro", "").strip()

        # Identificador de coordenador (email prioritário, fallback nome)
        coord_id = coord_email if coord_email else coord_name

        parts = [sector, municipio, tipo, data, hora_inicio, hora_fim, coord_id, encontro]
        content = "|".join(parts)

        return hashlib.sha1(content.encode("utf-8")).hexdigest()

    def determine_status(self, evento: dict[str, Any]) -> str:
        """
        Determina status da solicitação conforme regras:
        - data < hoje → aprovado
        - source_sheet == "Super" and aprovacao == "SIM" → aprovado
        - source_sheet == "Super" and aprovacao != "SIM" → pendente
        - Else → pendente
        """
        data_evento = parse_date_iso(evento.get("data", ""))
        if not data_evento:
            return "pendente"

        if data_evento < self.today:  # type: ignore[operator]
            return "aprovado"

        source_sheet = evento.get("source_sheet", "").strip()
        aprovacao = evento.get("aprovacao", "").strip().upper()

        if source_sheet == "Super":
            return "aprovado" if aprovacao == "SIM" else "pendente"

        return "pendente"

    def process_evento(self, evento: dict[str, Any], participantes_map: dict[str, list[dict[str, Any]]]) -> None:
        """
        Processa um evento do CSV:
        1. Resolve autor (primeiro COORDENADOR)
        2. Determina municípios (split se Super)
        3. Para cada município, cria/atualiza Solicitação
        4. Cria/atualiza Participations
        """
        event_hash_csv = evento.get("event_hash", "").strip()
        participantes = participantes_map.get(event_hash_csv, [])

        # Encontrar coordenador (autor)
        coord = self.find_coordenador(participantes)
        if not coord:
            self.stdout.write(f"   ⚠️  Sem coordenador: {event_hash_csv}")
            self.stats["skipped"]["autor"] += 1
            self.pendencias["outros"].append({
                "event_hash": event_hash_csv,
                "motivo": "autor_ausente",
            })
            return

        autor = resolve_user_by_email(coord.get("email", ""))
        if not autor:
            autor = resolve_user_by_name(coord.get("display_name", ""))

        if not autor:
            self.stdout.write(
                f"   ⚠️  Autor não resolvido: {coord.get('email')} / {coord.get('display_name')}"
            )
            self.stats["skipped"]["autor"] += 1
            self.pendencias["usuarios"].append({
                "email": coord.get("email"),
                "display_name": coord.get("display_name"),
                "motivo": "coordenador_nao_encontrado",
            })
            return

        # Determinar municípios
        source_sheet = evento.get("source_sheet", "").strip()
        municipio_value = evento.get("municipio", "").strip()

        if source_sheet == "Super":
            municipios_nomes = split_municipios_super(municipio_value)
        else:
            municipios_nomes = [municipio_value] if municipio_value else []

        if not municipios_nomes:
            self.stdout.write(f"   ⚠️  Sem município: {event_hash_csv}")
            self.stats["skipped"]["fk"] += 1
            self.pendencias["outros"].append({
                "event_hash": event_hash_csv,
                "motivo": "municipio_ausente",
            })
            return

        # Processar cada município (gera 1 Solicitação por município)
        for municipio_nome in municipios_nomes:
            self.process_solicitacao_for_municipio(
                evento, autor, municipio_nome, participantes
            )

    def find_coordenador(self, participantes: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Retorna o primeiro COORDENADOR da lista de participantes."""
        for p in participantes:
            if p.get("role", "").strip().upper() == "COORDENADOR":
                return p
        return None

    def process_solicitacao_for_municipio(
        self, evento: dict[str, Any], autor: Any, municipio_nome: str, participantes: list[dict[str, Any]]
    ) -> None:
        """
        Cria/atualiza Solicitação para um município específico.
        """
        # Resolver FK: município, projeto, tipo_evento
        municipio = resolve_municipio(municipio_nome)
        if not municipio:
            self.stdout.write(f"   ⚠️  Município não resolvido: {municipio_nome}")
            self.stats["skipped"]["fk"] += 1
            self.pendencias["municipios"].append(municipio_nome)
            return

        sector = normalize_sector(
            evento.get("source_sheet", ""), evento.get("projeto", "")
        )
        projeto = resolve_projeto(sector)
        if not projeto:
            self.stdout.write(f"   ⚠️  Projeto não resolvido: {sector}")
            self.stats["skipped"]["fk"] += 1
            self.pendencias["projetos"].append(sector)
            return

        tipo = evento.get("tipo", "").strip()
        tipo_evento = resolve_tipo_evento(tipo)
        if not tipo_evento:
            self.stdout.write(f"   ⚠️  Tipo evento não resolvido: {tipo}")
            self.stats["skipped"]["fk"] += 1
            self.pendencias["tipos"].append(tipo)
            return

        # Parse data/hora
        data_evento = parse_date_iso(evento.get("data", ""))
        hora_inicio = parse_time_iso(evento.get("hora_inicio", ""))
        hora_fim = parse_time_iso(evento.get("hora_fim", ""))

        if not (data_evento and hora_inicio and hora_fim):
            self.stdout.write(f"   ⚠️  Data/hora inválida: {evento.get('event_hash')}")
            self.stats["skipped"]["intervalo_invalido"] += 1
            self.pendencias["outros"].append({
                "event_hash": evento.get("event_hash"),
                "motivo": "data_hora_invalida",
            })
            return

        # Combinar data + hora timezone-aware
        inicio = timezone.make_aware(
            datetime.combine(data_evento, hora_inicio), self.tz
        )
        fim = timezone.make_aware(datetime.combine(data_evento, hora_fim), self.tz)

        if fim <= inicio:
            self.stdout.write(f"   ⚠️  Intervalo inválido (fim <= inicio): {evento.get('event_hash')}")
            self.stats["skipped"]["intervalo_invalido"] += 1
            self.pendencias["outros"].append({
                "event_hash": evento.get("event_hash"),
                "motivo": "fim_menor_igual_inicio",
            })
            return

        # Determinar status
        status = self.determine_status(evento)

        # external_hash (ajustar para incluir município se Super)
        coord_email = ""
        coord_name = ""
        coord = self.find_coordenador(participantes)
        if coord:
            coord_email = coord.get("email", "")
            coord_name = coord.get("display_name", "")

        # PR21: Pass participantes to compute_external_hash for hash v2
        base_hash = self.compute_external_hash(evento, coord_email, coord_name, participantes)

        # Se Super com múltiplos municípios, adicionar município ao hash
        source_sheet = evento.get("source_sheet", "").strip()
        if source_sheet == "Super":
            external_hash = f"{base_hash}_{municipio_nome}"
        else:
            external_hash = base_hash

        # Observações (opcional: incluir encontro, segmento, cancelado, adiado)
        observacoes_parts = []
        if evento.get("encontro"):
            observacoes_parts.append(f"Encontro: {evento['encontro']}")
        if evento.get("segmento"):
            observacoes_parts.append(f"Segmento: {evento['segmento']}")
        if evento.get("cancelado"):
            observacoes_parts.append(f"Cancelado: {evento['cancelado']}")
        if evento.get("adiado"):
            observacoes_parts.append(f"Adiado: {evento['adiado']}")

        observacoes = " | ".join(observacoes_parts)

        # Upsert Solicitação
        if not self.dry_run:
            solicitacao, created = Solicitacao.objects.update_or_create(
                external_hash=external_hash,
                defaults={
                    "usuario": autor,
                    "coordenador": autor,  # Set coordenador to same user as autor (from spreadsheet column N)
                    "municipio": municipio,
                    "projeto": projeto,
                    "tipo_evento": tipo_evento,
                    "inicio": inicio,
                    "fim": fim,
                    "status": status,
                    "observacoes": observacoes,
                },
            )

            if created:
                self.stats["solicitacoes"]["created"] += 1
                self.stdout.write(f"   ✅ Solicitação criada: {external_hash[:8]}...")
            else:
                # Verifica se houve mudança
                changed = False
                if solicitacao.status != status:
                    changed = True
                if solicitacao.inicio != inicio or solicitacao.fim != fim:
                    changed = True

                if changed:
                    self.stats["solicitacoes"]["updated"] += 1
                    self.stdout.write(f"   🔄 Solicitação atualizada: {external_hash[:8]}...")
                else:
                    self.stats["solicitacoes"]["unchanged"] += 1

            # Criar Participations
            self.process_participations(solicitacao, participantes, evento)
        else:
            # Dry-run: apenas contadores
            self.stats["solicitacoes"]["created"] += 1
            self.stdout.write(f"   [DRY-RUN] Solicitação: {external_hash[:8]}...")

    def process_participations(self, solicitacao: Any, participantes: list[dict[str, Any]], evento: dict[str, Any]) -> None:
        """
        Cria/atualiza Participations para uma solicitação.

        Regras:
        - "Outros" sem formadores → duplicar coordenador como FORMADOR
        - Usuários não resolvidos → pendências (não criar CONVIDADO)
        """
        source_sheet = evento.get("source_sheet", "").strip()

        # Agrupar participantes por role
        participantes_by_role = {"COORDENADOR": [], "FORMADOR": [], "COORD_ACOMPANHA": []}

        for p in participantes:
            role = p.get("role", "").strip().upper()
            if role in participantes_by_role:
                participantes_by_role[role].append(p)

        # Regra: "Outros" sem formadores → coordenador também FORMADOR
        if source_sheet == "Outros" and not participantes_by_role["FORMADOR"]:
            if participantes_by_role["COORDENADOR"]:
                coord = participantes_by_role["COORDENADOR"][0]
                participantes_by_role["FORMADOR"].append(coord.copy())

        # Criar Participations
        for role, grupo in participantes_by_role.items():
            for p in grupo:
                email = p.get("email", "").strip()
                display_name = p.get("display_name", "").strip()

                # FILTRO PR20: Skip indicadores (não-pessoas)
                # Skip se ambos (email E display_name) vazios OU se display_name é indicador
                if not email and not display_name:
                    self.stdout.write(f"      🚫 Participante vazio ({role}): sem email/nome")
                    self.stats["skipped"]["indicators"] = (
                        self.stats["skipped"].get("indicators", 0) + 1
                    )
                    continue

                # Se display_name existe, verificar se é indicador
                if display_name and not should_create_participation(display_name):
                    self.stdout.write(
                        f"      🚫 Indicador filtrado ({role}): {display_name}"
                    )
                    self.stats["skipped"]["indicators"] = (
                        self.stats["skipped"].get("indicators", 0) + 1
                    )
                    continue

                # Resolver usuário
                user = resolve_user_by_email(email)
                if not user:
                    user = resolve_user_by_name(display_name)

                if not user:
                    self.stdout.write(
                        f"      ⚠️  Participante não resolvido ({role}): {email} / {display_name}"
                    )
                    self.pendencias["usuarios"].append({
                        "email": email,
                        "display_name": display_name,
                        "role": role,
                        "motivo": "nao_encontrado",
                    })
                    continue

                # Criar Participation
                participation, created = Participation.objects.get_or_create(
                    solicitacao=solicitacao,
                    usuario=user,
                    role=role,
                )

                if created:
                    self.stats["participations"]["created"] += 1
                else:
                    self.stats["participations"]["updated"] += 1

    def calculate_metrics(self, eventos: list[dict[str, Any]], participantes_map: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """
        Calcula métricas de qualidade de dados para quality gates (PR21).

        Returns:
            Dict com métricas: total_events, duplicates_count, duplicates_pct,
                               unknown_users_count, invalid_intervals_count, invalid_dates_count
        """
        total_events = len(eventos)
        hashes_seen = {}
        duplicates_count = 0
        unknown_users = set()
        invalid_intervals = 0
        invalid_dates = 0

        for evento in eventos:
            # Calcular hash (ALL campos relevantes para detectar duplicata EXATA)
            event_id = evento.get("event_hash", "")
            if not event_id:
                # Duplicata = linha com TODOS os campos idênticos
                # Incluir: source_sheet, municipio, encontro, tipo, data, horas, projeto, segmento, coord, formadores
                simple_hash = (
                    f"{evento.get('source_sheet')}|"
                    f"{evento.get('municipio')}|"
                    f"{evento.get('encontro')}|"
                    f"{evento.get('tipo')}|"
                    f"{evento.get('data')}|"
                    f"{evento.get('hora_inicio')}|"
                    f"{evento.get('hora_fim')}|"
                    f"{evento.get('projeto')}|"
                    f"{evento.get('segmento')}|"
                    f"{evento.get('coord_acompanha')}|"
                    f"{evento.get('coordenador')}"
                )
                event_id = simple_hash

            if event_id in hashes_seen:
                duplicates_count += 1
            else:
                hashes_seen[event_id] = True

            # Unknown users: check coordenador (from evento) + participantes (from participantes_map)
            # 1. Check coordenador from evento
            coord_email = evento.get("coordenador", "").strip()
            if coord_email:
                user = resolve_user_by_email(coord_email)
                if not user:
                    # Try by name if email failed
                    user = resolve_user_by_name(coord_email)
                if not user:
                    unknown_users.add(coord_email)

            # 2. Check participantes from participantes_map
            event_hash = evento.get("event_hash", "")
            if event_hash in participantes_map:
                for p in participantes_map[event_hash]:
                    email = p.get("email", "")
                    display_name = p.get("display_name", "")

                    # Skip indicators
                    if not should_create_participation(display_name):
                        continue

                    # Try to resolve user
                    user = None
                    if email:
                        user = resolve_user_by_email(email)
                    if not user and display_name:
                        user = resolve_user_by_name(display_name)

                    if not user:
                        unknown_users.add(email or display_name)

            # Invalid intervals (fim <= início)
            data_str = evento.get("data", "")
            hora_inicio_str = evento.get("hora_inicio", "")
            hora_fim_str = evento.get("hora_fim", "")

            data = parse_date_iso(data_str)
            hora_inicio = parse_time_iso(hora_inicio_str)
            hora_fim = parse_time_iso(hora_fim_str)

            if not data or not hora_inicio or not hora_fim:
                invalid_dates += 1
            elif hora_fim <= hora_inicio:
                invalid_intervals += 1

        duplicates_pct = (duplicates_count / total_events * 100) if total_events > 0 else 0.0

        metrics = {
            "total_events": total_events,
            "duplicates_count": duplicates_count,
            "duplicates_pct": round(duplicates_pct, 2),
            "unknown_users_count": len(unknown_users),
            "invalid_intervals_count": invalid_intervals,
            "invalid_dates_count": invalid_dates,
        }

        self.stdout.write(f"   Total eventos: {metrics['total_events']}")
        self.stdout.write(f"   Duplicatas: {metrics['duplicates_count']} ({metrics['duplicates_pct']}%)")
        self.stdout.write(f"   Usuários desconhecidos: {metrics['unknown_users_count']}")
        self.stdout.write(f"   Intervalos inválidos: {metrics['invalid_intervals_count']}")
        self.stdout.write(f"   Datas inválidas: {metrics['invalid_dates_count']}")

        return metrics

    def detect_violations(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Detecta violações de quality gates (PR21).

        Returns:
            Lista de violações [{gate, message}] ou [] se nenhuma.
        """
        violations = []

        # Gate 1: Duplicates percentage
        if metrics["duplicates_pct"] > settings.ETL_MAX_DUPLICATES_PCT:
            msg = (
                f"Duplicates threshold violated: {metrics['duplicates_pct']}% > "
                f"{settings.ETL_MAX_DUPLICATES_PCT}%"
            )
            violations.append({"gate": "ETL_MAX_DUPLICATES_PCT", "message": msg})

        # Gate 2: Unknown users
        if metrics["unknown_users_count"] > settings.ETL_MAX_UNKNOWN_USERS:
            msg = (
                f"Unknown users threshold violated: {metrics['unknown_users_count']} > "
                f"{settings.ETL_MAX_UNKNOWN_USERS}"
            )
            violations.append({"gate": "ETL_MAX_UNKNOWN_USERS", "message": msg})

        # Gate 3: Invalid intervals
        if settings.ETL_REQUIRE_ZERO_INVALID_INTERVALS and metrics["invalid_intervals_count"] > 0:
            msg = (
                f"Invalid intervals detected: {metrics['invalid_intervals_count']} "
                f"(ETL_REQUIRE_ZERO_INVALID_INTERVALS=True)"
            )
            violations.append({"gate": "ETL_REQUIRE_ZERO_INVALID_INTERVALS", "message": msg})

        # Gate 4: Invalid dates
        if settings.ETL_REQUIRE_ZERO_INVALID_DATES and metrics["invalid_dates_count"] > 0:
            msg = (
                f"Invalid dates detected: {metrics['invalid_dates_count']} "
                f"(ETL_REQUIRE_ZERO_INVALID_DATES=True)"
            )
            violations.append({"gate": "ETL_REQUIRE_ZERO_INVALID_DATES", "message": msg})

        return violations

    def generate_metrics_report(self, metrics: dict[str, Any]) -> None:
        """
        Gera relatório JSON de métricas em v2/.agents/outbox/etl_metrics.json (PR21).
        """
        outbox = Path(settings.BASE_DIR) / ".agents" / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)

        report_path = outbox / "etl_metrics.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"   📄 Métricas salvas em: {report_path}")

    def generate_violations_report(self, violations: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
        """
        Gera relatório CSV de violações em v2/.agents/outbox/etl_violations.csv (PR21).
        """
        outbox = Path(settings.BASE_DIR) / ".agents" / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)

        report_path = outbox / "etl_violations.csv"

        with open(report_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["gate", "message", "metric_value", "threshold"])
            writer.writeheader()

            for v in violations:
                gate = v["gate"]
                message = v["message"]

                # Extract metric value and threshold from message
                if gate == "ETL_MAX_DUPLICATES_PCT":
                    metric_value = metrics["duplicates_pct"]
                    threshold = settings.ETL_MAX_DUPLICATES_PCT
                elif gate == "ETL_MAX_UNKNOWN_USERS":
                    metric_value = metrics["unknown_users_count"]
                    threshold = settings.ETL_MAX_UNKNOWN_USERS
                elif gate == "ETL_REQUIRE_ZERO_INVALID_INTERVALS":
                    metric_value = metrics["invalid_intervals_count"]
                    threshold = 0
                elif gate == "ETL_REQUIRE_ZERO_INVALID_DATES":
                    metric_value = metrics["invalid_dates_count"]
                    threshold = 0
                else:
                    metric_value = "N/A"
                    threshold = "N/A"

                writer.writerow({
                    "gate": gate,
                    "message": message,
                    "metric_value": metric_value,
                    "threshold": threshold,
                })

        self.stdout.write(f"   📄 Violações salvas em: {report_path}")

    def generate_report(self) -> None:
        """Gera relatório JSON de pendências."""
        out_dir = Path(settings.BASE_DIR) / "out_etl"
        out_dir.mkdir(exist_ok=True)

        report_path = out_dir / "etl_acompanhamento_pendencias.json"

        report = {
            "stats": self.stats,
            "pendencias": self.pendencias,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"\n📄 Relatório salvo em: {report_path}")
        self.stdout.write(f"\n📊 Stats:")
        self.stdout.write(f"   Solicitações: {self.stats['solicitacoes']}")
        self.stdout.write(f"   Participations: {self.stats['participations']}")
        self.stdout.write(f"   Skipped: {self.stats['skipped']}")
