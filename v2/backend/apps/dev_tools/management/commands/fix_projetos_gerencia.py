"""
Management command para corrigir vinculação de projetos às gerências.

Correções aplicadas:
1. Avançando Juntos Matemática/Português → GERENCIA 2 (Vidas)
2. ACerta → GERENCIA 4 (ACerta)
3. Cataventos → SUPERINTENDENCIA (Super)
4. Brincando e Vidas → Marcar como teste (não usados)

Data: 2025-12-01
Issue: Hierarquia organizacional
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.core.models import Gerencia, Projeto


class Command(BaseCommand):
    """Corrige vinculação de projetos às gerências corretas."""

    help = "Corrige vinculação de projetos às gerências (idempotente)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula as mudanças sem aplicar (padrão: False)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 Modo DRY-RUN: Nenhuma mudança será aplicada"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Modo APPLY: Mudanças serão aplicadas"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 CORREÇÃO DE PROJETOS → GERÊNCIAS")
        self.stdout.write("=" * 60 + "\n")

        # Carregar gerências
        try:
            gerencia_2 = Gerencia.objects.get(nome="GERENCIA 2")
            gerencia_4 = Gerencia.objects.get(nome="GERENCIA 4")
            superintendencia = Gerencia.objects.get(nome="SUPERINTENDENCIA")
        except Gerencia.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"❌ Gerência não encontrada: {e}"))
            return

        # 1. Mover Avançando Juntos para GERENCIA 2
        self.stdout.write("\n1️⃣  Avançando Juntos → GERENCIA 2 (Vidas)")
        avancando_juntos = Projeto.objects.filter(nome__icontains="AVANÇANDO JUNTOS")

        for projeto in avancando_juntos:
            gerencia_atual = projeto.gerencia.nome if projeto.gerencia else "SEM GERÊNCIA"
            self.stdout.write(f"   📝 {projeto.nome}")
            self.stdout.write(f"      De: {gerencia_atual} → Para: GERENCIA 2")

            if not dry_run:
                projeto.gerencia = gerencia_2  # pyright: ignore[reportAttributeAccessIssue]
                projeto.save()
                self.stdout.write(self.style.SUCCESS("      ✅ Atualizado"))
            else:
                self.stdout.write(self.style.WARNING("      🔍 Simulado"))

        # 2. Vincular ACerta à GERENCIA 4
        self.stdout.write("\n2️⃣  ACerta → GERENCIA 4 (ACerta)")
        try:
            acerta = Projeto.objects.get(nome="ACerta")
            gerencia_atual = acerta.gerencia.nome if acerta.gerencia else "SEM GERÊNCIA"
            self.stdout.write(f"   📝 {acerta.nome}")
            self.stdout.write(f"      De: {gerencia_atual} → Para: GERENCIA 4")
            self.stdout.write(f"      Solicitações: {acerta.solicitacoes.count()}")  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

            if not dry_run:
                acerta.gerencia = gerencia_4  # pyright: ignore[reportAttributeAccessIssue]
                acerta.save()
                self.stdout.write(self.style.SUCCESS("      ✅ Atualizado"))
            else:
                self.stdout.write(self.style.WARNING("      🔍 Simulado"))
        except Projeto.DoesNotExist:
            self.stdout.write(self.style.WARNING("   ⚠️  Projeto ACerta não encontrado"))

        # 3. Vincular Cataventos à SUPERINTENDENCIA
        self.stdout.write("\n3️⃣  Cataventos → SUPERINTENDENCIA (Super)")
        try:
            cataventos = Projeto.objects.get(nome="Cataventos")
            gerencia_atual = cataventos.gerencia.nome if cataventos.gerencia else "SEM GERÊNCIA"
            self.stdout.write(f"   📝 {cataventos.nome}")
            self.stdout.write(f"      De: {gerencia_atual} → Para: SUPERINTENDENCIA")
            self.stdout.write(f"      Solicitações: {cataventos.solicitacoes.count()}")  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            self.stdout.write(f"      Fluxo: {cataventos.fluxo}")

            if not dry_run:
                cataventos.gerencia = superintendencia  # pyright: ignore[reportAttributeAccessIssue]
                cataventos.save()
                self.stdout.write(self.style.SUCCESS("      ✅ Atualizado"))
            else:
                self.stdout.write(self.style.WARNING("      🔍 Simulado"))
        except Projeto.DoesNotExist:
            self.stdout.write(self.style.WARNING("   ⚠️  Projeto Cataventos não encontrado"))

        # 4. Marcar Brincando e Vidas como teste (não usados)
        self.stdout.write("\n4️⃣  Brincando e Vidas → Marcar como teste (não usados)")
        for nome in ["Brincando", "Vidas"]:
            try:
                projeto = Projeto.objects.get(nome=nome)
                self.stdout.write(f"   📝 {projeto.nome}")
                self.stdout.write(f"      Solicitações: {projeto.solicitacoes.count()}")  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
                self.stdout.write(f"      is_test: {projeto.is_test} → True")

                if not dry_run:
                    projeto.is_test = True
                    projeto.save()
                    self.stdout.write(self.style.SUCCESS("      ✅ Marcado como teste"))
                else:
                    self.stdout.write(self.style.WARNING("      🔍 Simulado"))
            except Projeto.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Projeto {nome} não encontrado"))

        # Resumo final
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY-RUN CONCLUÍDO: Nenhuma mudança foi aplicada"))
            self.stdout.write("   Execute sem --dry-run para aplicar as correções")
        else:
            self.stdout.write(self.style.SUCCESS("✅ CORREÇÕES APLICADAS COM SUCESSO!"))

            # Listar situação final
            self.stdout.write("\n📊 Situação Final:")
            for g in Gerencia.objects.all().order_by("nome"):
                count = g.projetos.count()  # type: ignore[reportUnknownMemberType,reportUnknownVariableType,reportAttributeAccessIssue]
                self.stdout.write(f"   {g.nome:25} → {count:2} projetos")

        self.stdout.write("=" * 60)
