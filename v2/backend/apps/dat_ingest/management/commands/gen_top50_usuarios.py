"""
Gera CSV com top-50 usuários a partir do relatório de pendências (PR20 Task 4).

CONTEXTO:
Após filtrar indicadores (Task 2), ainda restam ~70 pessoas reais sem cadastro.
Este comando analisa frequência de ocorrência e sugere os top-50 para cadastro
em lote, resolvendo ~40% das pendências.

FONTE:
relatorio_pessoas_pendentes_match.csv (gerado pela auditoria)

HEURÍSTICA:
- papel_sugerido: se apareceu ≥1x como COORDENADOR → "Coordenador", senão "Formador"
- Frequência: contar ocorrências únicas (pessoa + papel)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.dat_ingest.services.indicator_filter import should_create_participation


class Command(BaseCommand):
    help = "Gera CSV com top-50 usuários para cadastro em lote (PR20)"

    def add_arguments(self, parser: CommandParser) -> None:
        outbox = Path(settings.BASE_DIR) / ".agents" / "outbox"
        parser.add_argument(
            "--input",
            type=str,
            default=str(outbox / "relatorio_pessoas_pendentes_match.csv"),
            help="Caminho do relatório de pendências",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=str(outbox / "top50_usuarios_sugeridos.csv"),
            help="Caminho do CSV de saída",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Número máximo de usuários (padrão: 50)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        input_path = Path(options["input"])
        output_path = Path(options["out"])
        limit = options["limit"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("GERAÇÃO TOP-50 USUÁRIOS (PR20 Task 4)")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Input:  {input_path}")
        self.stdout.write(f"Output: {output_path}")
        self.stdout.write(f"Limit:  {limit}\n")

        # Ler CSV de pendências
        if not input_path.exists():
            self.stdout.write(self.style.ERROR(f"❌ Arquivo não encontrado: {input_path}"))
            return

        pessoas = []
        with open(input_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pessoa = row.get("pessoa", "").strip()
                papel = row.get("papel", "").strip()
                aba = row.get("aba", "").strip()
                sector = row.get("sector", "").strip()

                # Filtrar indicadores (Task 2)
                if not should_create_participation(pessoa):
                    continue

                # Papel pode ser múltiplo separado por vírgula
                papeis = [p.strip() for p in papel.split(",")]

                for p in papeis:
                    pessoas.append({
                        "pessoa": pessoa,
                        "papel": p,
                        "aba": aba,
                        "sector": sector,
                    })

        self.stdout.write(f"📊 Total de ocorrências (após filtrar indicadores): {len(pessoas)}")

        # Agrupar por pessoa: contar frequência e papéis
        pessoa_stats = defaultdict(lambda: {"count": 0, "papeis": set(), "abas": set(), "sectors": set()})

        for p in pessoas:
            nome = p["pessoa"]
            pessoa_stats[nome]["count"] += 1
            pessoa_stats[nome]["papeis"].add(p["papel"])
            pessoa_stats[nome]["abas"].add(p["aba"])
            pessoa_stats[nome]["sectors"].add(p["sector"])

        # Calcular papel_sugerido (heurística)
        usuarios_ranked = []
        for nome, stats in pessoa_stats.items():
            # Se apareceu como COORDENADOR, sugerir "Coordenador"; senão "Formador"
            if "COORDENADOR" in stats["papeis"]:
                papel_sugerido = "Coordenador"
            elif "FORMADOR_1" in stats["papeis"] or any("FORMADOR" in p for p in stats["papeis"]):
                papel_sugerido = "Formador"
            else:
                papel_sugerido = "Formador"  # Default

            # Setor mais frequente
            sector_freq = ", ".join(sorted(stats["sectors"]))

            usuarios_ranked.append({
                "nome_display": nome,
                "email": "",  # Não temos email no relatório de pendências
                "papel_sugerido": papel_sugerido,
                "gerente_sugerido": "",  # Não conseguimos inferir facilmente
                "origem_mais_frequente": ", ".join(sorted(stats["abas"])),
                "frequencia": stats["count"],
                "papeis_observados": ", ".join(sorted(stats["papeis"])),
                "setores": sector_freq,
            })

        # Ordenar por frequência descendente
        usuarios_ranked.sort(key=lambda x: x["frequencia"], reverse=True)

        # Limitar ao top-N
        top_usuarios = usuarios_ranked[:limit]

        self.stdout.write(f"\n📋 Top-{limit} usuários selecionados (frequência desc):")
        for i, u in enumerate(top_usuarios[:10], 1):
            self.stdout.write(
                f"  {i:2d}. {u['nome_display']:30s} | Freq: {u['frequencia']:3d} | Papel: {u['papel_sugerido']}"
            )
        if len(top_usuarios) > 10:
            self.stdout.write(f"  ... (+{len(top_usuarios)-10} usuários)")

        # Escrever CSV de saída
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            fieldnames = [
                "nome_display",
                "email",
                "papel_sugerido",
                "gerente_sugerido",
                "origem_mais_frequente",
                "frequencia",
                "papeis_observados",
                "setores",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(top_usuarios)

        self.stdout.write(f"\n✅ CSV gerado: {output_path}")
        self.stdout.write(f"   Usuários: {len(top_usuarios)}")
        self.stdout.write(
            f"\n⚠️  ATENÇÃO: Campo 'email' vazio - preencher manualmente antes de importar!"
        )
        self.stdout.write("=" * 80 + "\n")
