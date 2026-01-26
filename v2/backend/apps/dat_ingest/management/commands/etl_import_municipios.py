"""
ETL de Municípios: Import idempotente de Municipio a partir das planilhas.

Extrai municípios únicos de:
- Planilha de Controle (aba COMPRAS): Município + UF
- Acompanhamento de Agenda: Município

Idempotência: get_or_create por (nome, uf)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import Municipio


class Command(BaseCommand):
    help = "ETL de Municípios: import idempotente a partir das planilhas"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do arquivo XLSX (Planilha de Controle)",
        )
        parser.add_argument(
            "--sheet",
            type=str,
            default="",
            help="Nome da aba (default: busca COMPRAS automaticamente)",
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

        self.stdout.write(f"🚀 ETL Municípios (dry_run={self.dry_run})")
        self.stdout.write(f"   File: {self.file_path}")

        # Stats
        self.stats = {
            "created": 0,
            "already_exists": 0,
            "skipped": 0,
        }

        # Carregar arquivo
        self.stdout.write("\n📂 Carregando arquivo...")
        municipios = self.extract_municipios()
        self.stdout.write(f"   {len(municipios)} municípios únicos encontrados")

        # Processar
        self.stdout.write("\n⚙️  Processando municípios...")
        with transaction.atomic():
            for nome, uf in sorted(municipios):
                self.process_municipio(nome, uf)

            if self.dry_run:
                self.stdout.write("   [DRY-RUN] Rollback transaction")
                transaction.set_rollback(True)

        # Relatório
        self.generate_report(municipios)

        self.stdout.write(self.style.SUCCESS("\n✅ ETL concluído!"))

    def extract_municipios(self) -> set[tuple[str, str]]:
        """Extrai municípios únicos do arquivo."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas não instalado")

        file_path = Path(self.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        xl = pd.ExcelFile(file_path)
        municipios: set[tuple[str, str]] = set()

        # Encontrar aba COMPRAS ou usar a especificada
        target_sheet = self.sheet_name
        if not target_sheet:
            for sheet in xl.sheet_names:
                if "COMPRAS" in sheet.upper():
                    target_sheet = sheet
                    break

        if not target_sheet:
            self.stdout.write(self.style.WARNING("   Aba COMPRAS não encontrada, usando primeira aba"))
            target_sheet = xl.sheet_names[0]

        self.stdout.write(f"   Lendo aba: {target_sheet}")

        df = pd.read_excel(xl, sheet_name=target_sheet)

        # Extrair Município + UF
        for _, row in df.iterrows():
            nome = str(row.get("Município") or row.get("Municipio") or "").strip()
            uf = str(row.get("UF") or "").strip().upper()

            if nome and nome != "nan":
                # Normalizar nome (uppercase, sem espaços extras)
                nome_norm = " ".join(nome.upper().split())

                # UF padrão se não informada
                if not uf or uf == "NAN":
                    uf = "CE"  # Default para Ceará (maioria dos municípios)

                uf = uf[:2]  # Garantir 2 caracteres

                municipios.add((nome_norm, uf))

        return municipios

    def process_municipio(self, nome: str, uf: str) -> None:
        """Processa um município."""
        if not nome:
            self.stats["skipped"] += 1
            return

        # Verificar se já existe
        exists = Municipio.objects.filter(nome__iexact=nome, uf=uf).exists()

        if exists:
            self.stats["already_exists"] += 1
            return

        if not self.dry_run:
            Municipio.objects.create(
                nome=nome,
                uf=uf,
                ativo=True,
            )
            self.stdout.write(f"   ✅ Criado: {nome} ({uf})")

        self.stats["created"] += 1

    def generate_report(self, municipios: set[tuple[str, str]]) -> None:
        """Gera relatório."""
        out_dir = Path(settings.BASE_DIR) / "out_etl"
        out_dir.mkdir(exist_ok=True)

        report_path = out_dir / "etl_municipios_report.json"

        report = {
            "stats": self.stats,
            "municipios": sorted([{"nome": n, "uf": u} for n, u in municipios], key=lambda x: x["nome"]),
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"\n📄 Relatório salvo em: {report_path}")
        self.stdout.write("\n📊 Stats:")
        self.stdout.write(f"   Criados: {self.stats['created']}")
        self.stdout.write(f"   Já existentes: {self.stats['already_exists']}")
        self.stdout.write(f"   Skipped: {self.stats['skipped']}")
