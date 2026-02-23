"""
ETL de Bloqueios: Import idempotente de AvailabilityBlock.

Lê planilha de Disponibilidade (aba Bloqueios) e cria AvailabilityBlock.

Regras de negócio:
- Usuário resolvido por nome
- Tipo: T=Total, P=Parcial
- Datas parseadas: ISO, dd/mm/yyyy, Excel serial
- Idempotência: SHA1(usuario_id|inicio|fim|tipo)
- Relatório em out_etl/etl_bloqueios_report.json
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import AvailabilityBlock
from apps.dat_ingest.services.resolvers import resolve_user_by_name


class Command(BaseCommand):
    help = "ETL de Bloqueios: import idempotente de AvailabilityBlock"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do arquivo XLSX (Disponibilidade)",
        )
        parser.add_argument(
            "--sheet",
            type=str,
            default="Bloqueios",
            help="Nome da aba (default: Bloqueios)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem writes no banco",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.dry_run = options["dry_run"]
        self.file_path = options["file"]
        self.sheet_name = options["sheet"]
        self.tz = ZoneInfo("America/Fortaleza")

        self.stdout.write(f"🚀 ETL Bloqueios (dry_run={self.dry_run})")
        self.stdout.write(f"   File: {self.file_path}")
        self.stdout.write(f"   Sheet: {self.sheet_name}")

        # Stats e pendências
        self.stats = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": {"usuario": 0, "dates": 0, "other": 0},
        }
        self.pendencias: dict[str, list[Any]] = {
            "usuarios": [],
            "dates": [],
            "outros": [],
        }

        # Carregar arquivo
        self.stdout.write("\n📂 Carregando arquivo...")
        rows = self.load_file()
        self.stdout.write(f"   {len(rows)} linhas carregadas")

        # Processar linhas
        self.stdout.write("\n⚙️  Processando bloqueios...")
        with transaction.atomic():
            for idx, row in enumerate(rows, start=1):
                try:
                    self.process_row(row, idx)
                except Exception as e:
                    self.stdout.write(f"   ❌ Erro linha {idx}: {e}")
                    self.stats["skipped"]["other"] += 1
                    self.pendencias["outros"].append(
                        {
                            "linha": idx,
                            "erro": str(e),
                            "row": str(row),
                        }
                    )

            if self.dry_run:
                self.stdout.write("   [DRY-RUN] Rollback transaction")
                transaction.set_rollback(True)

        # Relatório
        self.generate_report()

        self.stdout.write(self.style.SUCCESS("\n✅ ETL concluído!"))

    def load_file(self) -> list[dict[str, Any]]:
        """Carrega XLSX com headers flexíveis."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas não instalado. Execute: pip install pandas")

        file_path = Path(self.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        df = pd.read_excel(file_path, sheet_name=self.sheet_name)
        df = df.dropna(how="all")

        rows = []
        for _, row in df.iterrows():
            normalized = self._normalize_row(row)
            rows.append(normalized)

        return rows

    def _normalize_row(self, row: Any) -> dict[str, Any]:
        """Normaliza headers do XLSX para padrão interno."""
        normalized = {}

        # Criar mapa lower → valor
        row_dict = row.to_dict()
        lower_map = {str(k).strip().lower(): v for k, v in row_dict.items()}

        # Usuário
        for key in ["usuário", "usuario", "user", "formador", "nome"]:
            if key in lower_map:
                val = lower_map[key]
                normalized["usuario"] = str(val).strip() if val and str(val) != "nan" else ""
                break
        else:
            normalized["usuario"] = ""

        # Início
        for key in ["inicio", "início", "start", "data_inicio"]:
            if key in lower_map:
                normalized["inicio"] = lower_map[key]
                break
        else:
            normalized["inicio"] = None

        # Fim
        for key in ["fim", "end", "data_fim"]:
            if key in lower_map:
                normalized["fim"] = lower_map[key]
                break
        else:
            normalized["fim"] = None

        # Tipo
        for key in ["tipo", "type"]:
            if key in lower_map:
                val = lower_map[key]
                normalized["tipo"] = str(val).strip() if val and str(val) != "nan" else "Total"
                break
        else:
            normalized["tipo"] = "Total"

        # Motivo
        for key in ["motivo", "obs", "observacao", "observação"]:
            if key in lower_map:
                val = lower_map[key]
                normalized["motivo"] = str(val).strip() if val and str(val) != "nan" else ""
                break
        else:
            normalized["motivo"] = ""

        return normalized

    def parse_datetime_flexible(self, value: Any) -> datetime | None:
        """Parse datetime flexível."""
        if not value or str(value) == "nan":
            return None

        # Se já é datetime
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=self.tz)
            return value

        # Se é date
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time(), tzinfo=self.tz)

        # Se é número (Excel serial)
        if isinstance(value, (int, float)):
            try:
                base_date = datetime(1899, 12, 30, tzinfo=self.tz)
                return base_date + timedelta(days=float(value))
            except Exception:
                return None

        # Se é string
        value_str = str(value).strip()
        if not value_str:
            return None

        # Tentar ISO
        try:
            dt = datetime.fromisoformat(value_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=self.tz)
            return dt
        except ValueError:
            pass

        # Tentar dd/mm/yyyy
        for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(value_str, fmt)
                return dt.replace(tzinfo=self.tz)
            except ValueError:
                pass

        return None

    def process_row(self, row: dict[str, Any], linha_num: int) -> None:
        """Processa uma linha do arquivo."""
        # Resolver usuário
        nome = row.get("usuario", "").strip()

        if not nome:
            self.stdout.write(f"   ⚠️  Linha {linha_num}: Nome de usuário vazio")
            self.stats["skipped"]["usuario"] += 1
            return

        usuario = resolve_user_by_name(nome)

        if not usuario:
            self.stdout.write(f"   ⚠️  Linha {linha_num}: Usuário não resolvido ({nome})")
            self.stats["skipped"]["usuario"] += 1
            self.pendencias["usuarios"].append(
                {
                    "linha": linha_num,
                    "nome": nome,
                }
            )
            return

        # Parse datas
        inicio = self.parse_datetime_flexible(row.get("inicio"))
        fim = self.parse_datetime_flexible(row.get("fim"))

        if not inicio or not fim:
            self.stdout.write(
                f"   ⚠️  Linha {linha_num}: Datas inválidas (inicio={row.get('inicio')}, fim={row.get('fim')})"
            )
            self.stats["skipped"]["dates"] += 1
            self.pendencias["dates"].append(
                {
                    "linha": linha_num,
                    "inicio": str(row.get("inicio")),
                    "fim": str(row.get("fim")),
                }
            )
            return

        # Ajustar fim para fim do dia se for meia-noite
        if fim.hour == 0 and fim.minute == 0:
            fim = fim.replace(hour=23, minute=59, second=59)

        if fim <= inicio:
            self.stdout.write(f"   ⚠️  Linha {linha_num}: fim <= inicio")
            self.stats["skipped"]["dates"] += 1
            return

        # Tipo
        tipo_raw = row.get("tipo", "Total").lower()
        if "parcial" in tipo_raw:
            tipo = "P"
        else:
            tipo = "T"

        # Motivo
        motivo = row.get("motivo", "").strip()

        # Gerar external_hash (para idempotência manual)
        external_hash = self.compute_hash(usuario.id, inicio, fim, tipo)

        # Verificar existência
        existing = AvailabilityBlock.objects.filter(
            usuario=usuario,
            inicio=inicio,
            fim=fim,
            tipo=tipo,
        ).first()

        if not self.dry_run:
            if existing:
                self.stats["unchanged"] += 1
            else:
                AvailabilityBlock.objects.create(
                    usuario=usuario,
                    inicio=inicio,
                    fim=fim,
                    tipo=tipo,
                    motivo=motivo,
                    status="aprovado",  # Auto-aprovado
                )
                self.stats["created"] += 1
                self.stdout.write(f"   ✅ Linha {linha_num}: Bloqueio criado ({nome})")
        else:
            self.stats["created"] += 1
            self.stdout.write(f"   [DRY-RUN] Linha {linha_num}: {nome} ({tipo}) {inicio.date()} - {fim.date()}")

    def compute_hash(self, usuario_id: int, inicio: datetime, fim: datetime, tipo: str) -> str:
        """Gera hash SHA1 para referência."""
        parts = [
            str(usuario_id),
            inicio.isoformat(),
            fim.isoformat(),
            tipo,
        ]
        content = "|".join(parts)
        return hashlib.sha1(content.encode("utf-8"), usedforsecurity=False).hexdigest()

    def generate_report(self) -> None:
        """Gera relatório JSON."""
        out_dir = Path(settings.BASE_DIR) / "out_etl"
        out_dir.mkdir(exist_ok=True)

        report_path = out_dir / "etl_bloqueios_report.json"

        report = {
            "stats": self.stats,
            "pendencias": self.pendencias,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"\n📄 Relatório salvo em: {report_path}")
        self.stdout.write("\n📊 Stats:")
        self.stdout.write(f"   Created: {self.stats['created']}")
        self.stdout.write(f"   Unchanged: {self.stats['unchanged']}")
        self.stdout.write(f"   Skipped: {self.stats['skipped']}")
