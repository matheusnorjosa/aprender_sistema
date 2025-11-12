"""
Seed dos 6 projetos faltantes identificados na auditoria (PR20 Task 3).

CONTEXTO:
A auditoria identificou 6 projetos na aba "Outros" que não existem no
FILTRO_PROD. do Controle. Este comando cria/garante esses projetos de
forma idempotente.

PROJETOS:
1. ED FINANCEIRA (Educação Financeira)
2. LER OUVIR E CONTAR
3. GESTÃO ESCOLAR (alias: IDEB, IDEB10)
4. SOU DA PAZ
5. A COR DA GENTE
6. LEIO ESCREVO E CALCULO
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false

ALIASES:
- "IDEB" → "GESTÃO ESCOLAR"
- "IDEB10" → "GESTÃO ESCOLAR"
- "IDEB/IDEB10" → "GESTÃO ESCOLAR"

Implementado em: resolvers.normalize_projeto()
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import Projeto


class Command(BaseCommand):
    help = "Seed dos 6 projetos faltantes (PR20) - idempotente"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem writes no banco",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("SEED PROJETOS EXTRAS (PR20 Task 3)")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Modo: {'DRY-RUN' if dry_run else 'APLICAR'}\n")

        # Definir os 6 projetos faltantes
        # Todos com fluxo=NAO_SUPER, ativo=True
        projetos = [
            {
                "nome": "ED FINANCEIRA",
                "codigo": "ED_FIN",
                "fluxo": "NAO_SUPER",
                "ativo": True,
            },
            {
                "nome": "LER OUVIR E CONTAR",
                "codigo": "LER_OUVIR",
                "fluxo": "NAO_SUPER",
                "ativo": True,
            },
            {
                "nome": "GESTÃO ESCOLAR",
                "codigo": "GESTAO_ESC",
                "fluxo": "NAO_SUPER",
                "ativo": True,
            },
            {
                "nome": "SOU DA PAZ",
                "codigo": "SOU_PAZ",
                "fluxo": "NAO_SUPER",
                "ativo": True,
            },
            {
                "nome": "A COR DA GENTE",
                "codigo": "COR_GENTE",
                "fluxo": "NAO_SUPER",
                "ativo": True,
            },
            {
                "nome": "LEIO ESCREVO E CALCULO",
                "codigo": "LEIO_ESC_CALC",
                "fluxo": "NAO_SUPER",
                "ativo": True,
            },
        ]

        stats = {
            "created": 0,
            "already_exists": 0,
            "errors": 0,
        }

        if not dry_run:
            with transaction.atomic():
                for proj_data in projetos:
                    nome = proj_data["nome"]
                    try:
                        # Tentar buscar por nome exato (case-insensitive via iexact)
                        projeto, created = Projeto.objects.get_or_create(
                            nome__iexact=nome,
                            defaults={
                                "nome": nome,
                                "codigo": proj_data["codigo"],
                                "fluxo": proj_data["fluxo"],
                                "ativo": proj_data["ativo"],
                            },
                        )

                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(f"  ✅ Criado: {nome} ({projeto.codigo})")
                            )
                            stats["created"] += 1
                        else:
                            self.stdout.write(f"  ℹ️  Já existe: {nome} (ID: {projeto.id})")
                            stats["already_exists"] += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ❌ Erro ao criar '{nome}': {e}")
                        )
                        stats["errors"] += 1

        else:
            # Dry-run: apenas simular
            self.stdout.write("🔍 Verificando projetos existentes...\n")
            for proj_data in projetos:
                nome = proj_data["nome"]
                exists = Projeto.objects.filter(nome__iexact=nome).exists()
                if exists:
                    self.stdout.write(f"  ℹ️  [DRY-RUN] Já existe: {nome}")
                    stats["already_exists"] += 1
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✅ [DRY-RUN] Criaria: {nome}")
                    )
                    stats["created"] += 1

        # Sumário
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("📊 SUMÁRIO:")
        self.stdout.write(f"   Criados: {stats['created']}")
        self.stdout.write(f"   Já existentes: {stats['already_exists']}")
        self.stdout.write(f"   Erros: {stats['errors']}")
        self.stdout.write("-" * 80)

        # Verificação final
        if not dry_run and stats["errors"] == 0:
            total_existentes = Projeto.objects.filter(
                nome__in=[p["nome"] for p in projetos]
            ).count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Verificação: {total_existentes}/6 projetos existem no banco"
                )
            )

            if total_existentes < 6:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Apenas {total_existentes}/6 projetos encontrados. Verifique!"
                    )
                )
        elif not dry_run and stats["errors"] > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ FALHA: {stats['errors']} erro(s) ao criar projetos"
                )
            )
            raise Exception("Seed de projetos falhou com erros")

        self.stdout.write("\n✅ Seed de projetos concluído!\n")
