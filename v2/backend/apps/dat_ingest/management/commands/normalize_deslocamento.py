"""
Normaliza planilha DESLOCAMENTO para formato compatível com ETL.

A planilha original tem formato:
| Origem | Tipo | Destino | Data | Pessoa 1 | Pessoa 2 | ... |

Este comando transforma para:
| name | origem | destino | start | end | obs |

Onde:
- Pares (Deslocamento → Retorno) são combinados para formar start_date/end_date
- Uma linha por pessoa é gerada
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Normaliza planilha DESLOCAMENTO para formato ETL"

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
            default="DESLOCAMENTO",
            help="Nome da aba (default: DESLOCAMENTO)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Arquivo CSV de saída (default: out_etl/deslocamento_normalizado.csv)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.file_path = options["file"]
        self.sheet_name = options["sheet"]

        # Output path
        if options["output"]:
            self.output_path = Path(options["output"])
        else:
            out_dir = Path(settings.BASE_DIR) / "out_etl"
            out_dir.mkdir(exist_ok=True)
            self.output_path = out_dir / "deslocamento_normalizado.csv"

        self.stdout.write("🚀 Normalize DESLOCAMENTO")
        self.stdout.write(f"   Input: {self.file_path}")
        self.stdout.write(f"   Sheet: {self.sheet_name}")
        self.stdout.write(f"   Output: {self.output_path}")

        # Carregar dados
        self.stdout.write("\n📂 Carregando arquivo...")
        rows = self.load_file()
        self.stdout.write(f"   {len(rows)} linhas carregadas")

        # Processar e gerar CSV normalizado
        self.stdout.write("\n⚙️  Processando...")
        normalized = self.normalize_deslocamentos(rows)
        self.stdout.write(f"   {len(normalized)} registros normalizados")

        # Escrever CSV
        self.write_csv(normalized)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Arquivo gerado: {self.output_path}"))

    def load_file(self) -> list[dict[str, Any]]:
        """Carrega XLSX."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas não instalado")

        file_path = Path(self.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        df = pd.read_excel(file_path, sheet_name=self.sheet_name)
        df = df.dropna(how="all")

        rows = []
        for _, row in df.iterrows():
            rows.append(row.to_dict())

        return rows

    def parse_date(self, value: Any) -> date | None:
        """Parse data flexível."""
        if not value or str(value) == "nan" or str(value) == "NaT":
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, (int, float)):
            try:
                return (datetime(1899, 12, 30) + timedelta(days=int(value))).date()
            except Exception:
                return None

        value_str = str(value).strip()
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"]:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                pass

        return None

    def normalize_deslocamentos(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Normaliza deslocamentos.

        Estratégia:
        1. Agrupar por pessoas (Pessoa 1, Pessoa 2, etc.)
        2. Para cada pessoa, tentar encontrar par Deslocamento → Retorno
        3. Se não houver retorno, usar mesma data (viagem de um dia)
        """
        normalized = []

        # Identificar colunas de pessoas
        pessoa_cols = []
        if rows:
            for col in rows[0].keys():
                col_lower = str(col).lower()
                if "pessoa" in col_lower or "formador" in col_lower:
                    pessoa_cols.append(col)

        self.stdout.write(f"   Colunas de pessoas: {pessoa_cols}")

        # Processar cada linha
        deslocamentos_por_pessoa: dict[str, list[dict[str, Any]]] = {}

        for row in rows:
            # Extrair dados base
            origem = str(row.get("Origem", "")).strip()
            tipo = str(row.get("Tipo", "")).strip().lower()
            destino = str(row.get("Destino", "")).strip()
            data = self.parse_date(row.get("Data"))

            if not data:
                continue

            # Extrair pessoas
            pessoas = []
            for col in pessoa_cols:
                val = row.get(col)
                if val and str(val) != "nan":
                    pessoas.append(str(val).strip())

            # Registrar deslocamento para cada pessoa
            for pessoa in pessoas:
                if pessoa not in deslocamentos_por_pessoa:
                    deslocamentos_por_pessoa[pessoa] = []

                deslocamentos_por_pessoa[pessoa].append(
                    {
                        "origem": origem,
                        "tipo": tipo,
                        "destino": destino,
                        "data": data,
                    }
                )

        # Processar cada pessoa
        for pessoa, viagens in deslocamentos_por_pessoa.items():
            # Ordenar por data
            viagens_sorted = sorted(viagens, key=lambda x: x["data"])

            # Tentar parear ida/volta
            processed_indices: set[int] = set()

            for i, viagem in enumerate(viagens_sorted):
                if i in processed_indices:
                    continue

                if "deslocamento" in viagem["tipo"]:
                    # Buscar retorno correspondente
                    retorno = None
                    for j in range(i + 1, len(viagens_sorted)):
                        if j in processed_indices:
                            continue
                        candidate = viagens_sorted[j]
                        if "retorno" in candidate["tipo"]:
                            # Verificar se destino do retorno é origem do deslocamento
                            if candidate["origem"] == viagem["destino"] or candidate["destino"] == viagem["origem"]:
                                retorno = candidate
                                processed_indices.add(j)
                                break

                    start_date = viagem["data"]
                    if retorno:
                        end_date = retorno["data"]
                    else:
                        # Sem retorno: usar mesma data
                        end_date = start_date

                    normalized.append(
                        {
                            "name": pessoa,
                            "origem": viagem["origem"],
                            "destino": viagem["destino"],
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat(),
                            "obs": f"Tipo: {viagem['tipo']}",
                        }
                    )

                    processed_indices.add(i)

                elif "retorno" in viagem["tipo"] and i not in processed_indices:
                    # Retorno sem ida: registrar como viagem de um dia
                    normalized.append(
                        {
                            "name": pessoa,
                            "origem": viagem["origem"],
                            "destino": viagem["destino"],
                            "start": viagem["data"].isoformat(),
                            "end": viagem["data"].isoformat(),
                            "obs": "Retorno sem ida pareada",
                        }
                    )
                    processed_indices.add(i)

        return normalized

    def write_csv(self, records: list[dict[str, Any]]) -> None:
        """Escreve CSV normalizado."""
        if not records:
            self.stdout.write(self.style.WARNING("   Nenhum registro para escrever"))
            return

        fieldnames = ["name", "origem", "destino", "start", "end", "obs"]

        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
