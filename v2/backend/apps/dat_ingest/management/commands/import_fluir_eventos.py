"""
ETL para importação de eventos da planilha Fluir das Emoções.

Usage:
    python manage.py import_fluir_eventos --dry-run  # Preview
    python manage.py import_fluir_eventos --apply  # Apply

Idempotence:
    - Usa external_hash (SHA1) para evitar duplicatas
    - Mesmo hash = mesmo evento (skip)

Quality Gates:
    - Min 100 eventos válidos (threshold configurável)
    - Max 10% rejeições
    - Todos os 9 formadores Fluir devem existir no banco
    - Projeto "FLUIR DAS EMOÇÕES" deve existir

Output:
    - Relatório JSON em out_etl/import_fluir_YYYYMMDD_HHMMSS.json
    - Stats: created, updated, skipped, errors
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false, reportArgumentType=false, reportOperatorIssue=false

from typing import Any
from pathlib import Path
from datetime import datetime
import json

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import Solicitacao, Projeto, Municipio, Usuario, Participation, TipoEvento
from apps.dat_ingest.services.parse_fluir import parse_fluir_eventos, get_formadores_fluir


class Command(BaseCommand):
    """ETL para importar eventos da planilha Fluir."""

    help = "Importa eventos da planilha Fluir para Solicitacao"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--filepath",
            type=str,
            default="data/csv-import/Acompanhamento de Agenda _ Fluir (1).xlsx",
            help="Caminho da planilha Fluir",
        )
        parser.add_argument("--dry-run", action="store_true", help="Preview only (não persiste)")
        parser.add_argument("--apply", action="store_true", help="Apply changes (persiste no banco)")
        parser.add_argument(
            "--min-eventos",
            type=int,
            default=100,
            help="Threshold mínimo de eventos válidos (quality gate)",
        )

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        """Execute ETL com dry-run ou apply mode."""
        filepath_rel = options["filepath"]
        dry_run: bool = bool(options.get("dry_run", False))
        apply_mode: bool = bool(options.get("apply", False))
        min_eventos: int = int(options.get("min_eventos", 100))

        if not dry_run and not apply_mode:
            self.stderr.write(
                self.style.ERROR("❌ ERRO: Especifique --dry-run ou --apply")
            )
            return

        mode = "DRY-RUN (preview)" if dry_run else "APPLY (commit)"

        self.stdout.write("=" * 60)
        self.stdout.write(f"IMPORT FLUIR EVENTOS - {mode}")
        self.stdout.write("=" * 60)

        # 1. Parse planilha
        filepath = Path("/app") / filepath_rel
        self.stdout.write(f"\n📂 Lendo planilha: {filepath_rel}")

        try:
            eventos_raw = parse_fluir_eventos(filepath)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"❌ Planilha não encontrada: {filepath}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Erro ao parsear planilha: {e}"))
            return

        self.stdout.write(f"  ✅ {len(eventos_raw)} eventos parseados")

        # 2. Quality Gates
        self.stdout.write("\n🔍 Quality Gates:")

        # Gate 1: Min eventos
        if len(eventos_raw) < min_eventos:
            self.stderr.write(
                self.style.ERROR(
                    f"❌ GATE 1 FALHOU: Menos de {min_eventos} eventos ({len(eventos_raw)})"
                )
            )
            return
        self.stdout.write(f"  ✅ GATE 1: {len(eventos_raw)} eventos >= {min_eventos}")

        # Gate 2: Projeto existe
        try:
            projeto_fluir = Projeto.objects.get(nome="FLUIR DAS EMOÇÕES")
            self.stdout.write(f"  ✅ GATE 2: Projeto 'FLUIR DAS EMOÇÕES' existe (ID: {projeto_fluir.id})")
        except Projeto.DoesNotExist:
            self.stderr.write(
                self.style.ERROR("❌ GATE 2 FALHOU: Projeto 'FLUIR DAS EMOÇÕES' não existe")
            )
            return

        # Gate 3: Formadores existem
        formadores_esperados = get_formadores_fluir()
        formadores_faltantes = []
        for nome in formadores_esperados:
            username = self._normalize_username(nome)
            if not Usuario.objects.filter(username=username).exists():
                formadores_faltantes.append(nome)

        if formadores_faltantes:
            self.stderr.write(
                self.style.ERROR(
                    f"❌ GATE 3 FALHOU: {len(formadores_faltantes)} formadores não encontrados:"
                )
            )
            for nome in formadores_faltantes:
                self.stderr.write(f"     - {nome}")
            self.stderr.write(
                self.style.WARNING(
                    "\n💡 Rode: python manage.py seed_formadores_fluir"
                )
            )
            return
        self.stdout.write(f"  ✅ GATE 3: Todos os {len(formadores_esperados)} formadores existem")

        # 3. Processar eventos
        self.stdout.write(f"\n🔄 Processando {len(eventos_raw)} eventos...")

        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "missing_municipios": [],
        }

        for i, evento_data in enumerate(eventos_raw, 1):
            try:
                result = self._process_evento(evento_data, projeto_fluir, dry_run)
                stats[result["action"]] += 1

                if result["action"] == "error":
                    self.stdout.write(
                        self.style.ERROR(f"  [{i}/{len(eventos_raw)}] ❌ {result['message']}")
                    )
                elif result["action"] == "created":
                    self.stdout.write(
                        self.style.SUCCESS(f"  [{i}/{len(eventos_raw)}] ✅ Criado: {result['message']}")
                    )
                elif result["action"] == "skipped":
                    self.stdout.write(
                        self.style.NOTICE(f"  [{i}/{len(eventos_raw)}] ⏭️  {result['message']}")
                    )

            except Exception as e:
                stats["errors"] += 1
                self.stdout.write(
                    self.style.ERROR(f"  [{i}/{len(eventos_raw)}] ❌ Erro: {e}")
                )

        # 4. Gate 4: Max 10% rejeições
        rejeicao_rate = (stats["errors"] / len(eventos_raw)) * 100 if eventos_raw else 0
        if rejeicao_rate > 10:
            self.stderr.write(
                self.style.ERROR(
                    f"❌ GATE 4 FALHOU: Taxa de rejeição {rejeicao_rate:.1f}% > 10%"
                )
            )
            return
        self.stdout.write(f"  ✅ GATE 4: Taxa de rejeição {rejeicao_rate:.1f}% <= 10%")

        # 5. Resumo
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RESUMO:")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Modo: {mode}")
        self.stdout.write(f"  Criados: {stats['created']}")
        self.stdout.write(f"  Atualizados: {stats['updated']}")
        self.stdout.write(f"  Já existiam: {stats['skipped']}")
        self.stdout.write(f"  Erros: {stats['errors']}")
        self.stdout.write(f"  Total processado: {len(eventos_raw)}")

        if stats["missing_municipios"]:
            self.stdout.write(f"\n⚠️  Municípios não encontrados ({len(stats['missing_municipios'])}):")
            for mun in set(stats["missing_municipios"]):
                self.stdout.write(f"     - {mun}")

        # 6. Gerar relatório JSON
        if apply_mode:
            self._save_report(stats, eventos_raw)

        self.stdout.write("=" * 60)

    def _process_evento(
        self, evento_data: dict[str, Any], projeto: Projeto, dry_run: bool
    ) -> dict[str, str]:
        """
        Processa um evento individual.

        Returns:
            Dict com 'action' (created/updated/skipped/error) e 'message'
        """
        # Resolver município
        municipio_nome_uf = evento_data["municipio_nome_uf"]
        municipio = self._resolve_municipio(municipio_nome_uf)
        if not municipio:
            return {
                "action": "error",
                "message": f"Município não encontrado: {municipio_nome_uf}",
            }

        # Resolver formadores
        formadores_nomes = evento_data["formadores"]
        formadores_objs = []
        for nome in formadores_nomes:
            username = self._normalize_username(nome)
            formador = Usuario.objects.filter(username=username).first()
            if not formador:
                return {
                    "action": "error",
                    "message": f"Formador não encontrado: {nome}",
                }
            formadores_objs.append(formador)

        # Check se já existe (external_hash)
        external_hash = evento_data["external_hash"]
        existing = Solicitacao.objects.filter(external_hash=external_hash).first()

        if existing:
            return {
                "action": "skipped",
                "message": f"Já existe (hash: {external_hash[:8]}...)",
            }

        if dry_run:
            return {
                "action": "created",
                "message": f"[DRY-RUN] Criaria: {municipio_nome_uf} - {evento_data['inicio'].date()}",
            }

        # Get or create default TipoEvento
        tipo_evento, _ = TipoEvento.objects.get_or_create(
            nome="Evento Fluir",
        )

        # Criar Solicitacao
        with transaction.atomic():
            solicitacao = Solicitacao.objects.create(
                projeto=projeto,
                municipio=municipio,
                tipo_evento=tipo_evento,
                status=evento_data["status"],
                inicio=evento_data["inicio"],
                fim=evento_data["fim"],
                is_online=evento_data["is_online"],
                observacoes=f"Fonte: {evento_data['src']}\nTurma: {evento_data['turma']}\nEncontro: {evento_data['encontro']}\nTema: {evento_data['tema']}",
                external_hash=external_hash,
            )

            # Criar Participation para formadores
            for formador in formadores_objs:
                Participation.objects.create(
                    solicitacao=solicitacao,
                    usuario=formador,
                )

        return {
            "action": "created",
            "message": f"{municipio.nome} - {solicitacao.inicio.date()} - {formadores_nomes[0]}",
        }

    def _resolve_municipio(self, municipio_nome_uf: str) -> Municipio | None:
        """
        Resolve município por nome + UF.

        Examples:
            "Araguari-MG" → Municipio(nome="Araguari", uf="MG")
            "Cubatão - SP" → Municipio(nome="Cubatão", uf="SP")
        """
        # Normalizar (remover espaços em excesso, separar por "-")
        parts = municipio_nome_uf.replace(" - ", "-").split("-")
        if len(parts) != 2:
            return None

        nome, uf = parts[0].strip(), parts[1].strip().upper()

        # Buscar no banco (case-insensitive)
        municipio = Municipio.objects.filter(nome__iexact=nome, uf=uf).first()
        return municipio

    def _normalize_username(self, nome_completo: str) -> str:
        """Normaliza nome completo para username."""
        import unicodedata

        nome_sem_acento = "".join(
            c
            for c in unicodedata.normalize("NFD", nome_completo)
            if unicodedata.category(c) != "Mn"
        )
        username = nome_sem_acento.lower().replace(" ", "_")
        return username

    def _save_report(self, stats: dict[str, Any], eventos: list[dict[str, Any]]) -> None:
        """Salva relatório JSON em out_etl/."""
        out_dir = Path("/app/out_etl")
        out_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = out_dir / f"import_fluir_{timestamp}.json"

        report = {
            "timestamp": timestamp,
            "mode": "apply",
            "stats": stats,
            "total_eventos": len(eventos),
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"\n📊 Relatório salvo: {report_path}")
