"""
ETL para corrigir mapeamento Projeto → Gerência baseado em produtos.xlsx.

Correções identificadas:
1. Remove projetos órfãos duplicatas (sem solicitações vinculadas)
2. Vincula projetos órfãos à gerência correta
3. Corrige projetos com gerência incorreta

Usage:
    python manage.py etl_fix_projetos_gerencia --dry-run
    python manage.py etl_fix_projetos_gerencia --apply

Idempotence:
    - Verifica estado atual antes de alterar
    - Não remove projetos com solicitações vinculadas
    - Pode ser executado múltiplas vezes sem efeitos colaterais
"""
# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Gerencia, Projeto, Solicitacao


# Correções baseadas em produtos.xlsx
CORRECOES = {
    # Projetos que devem ir para Individual (ID=7)
    "vincular_individual": [
        13,  # GESTÃO ESCOLAR (órfão)
        24,  # AVANÇANDO JUNTOS MATEMÁTICA (atualmente Vidas)
        25,  # AVANÇANDO JUNTOS PORTUGUÊS (atualmente Vidas)
        15,  # UNI DUNI TÊ (atualmente Super)
    ],
    # Projetos órfãos duplicatas para remover (sem solicitações)
    "remover_duplicatas": [
        41,  # Brincando (duplicata de BRINCANDO E APRENDENDO ID=10)
        42,  # Vidas (órfão sem uso)
    ],
}


class Command(BaseCommand):
    """Corrige mapeamento Projeto → Gerência baseado em produtos.xlsx."""

    help = "Corrige mapeamento Projeto → Gerência baseado em produtos.xlsx"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula, não altera o banco",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica as alterações no banco",
        )

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        dry_run = options.get("dry_run", False)
        apply = options.get("apply", False)

        if not dry_run and not apply:
            self.stderr.write(
                self.style.ERROR("Especifique --dry-run ou --apply")
            )
            return

        self.stdout.write("=" * 70)
        self.stdout.write("ETL: CORRIGIR PROJETOS → GERÊNCIA")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Modo: {'DRY-RUN (simulação)' if dry_run else 'APPLY (produção)'}")
        self.stdout.write("")

        # Buscar gerência Individual
        try:
            individual = Gerencia.objects.get(nome_setor="Individual")
        except Gerencia.DoesNotExist:
            self.stderr.write(
                self.style.ERROR("Gerência 'Individual' não encontrada!")
            )
            return

        self.stdout.write(f"Gerência Individual: ID={individual.id}")
        self.stdout.write("")

        stats = {
            "vinculados": 0,
            "removidos": 0,
            "skipped_com_solicitacoes": 0,
            "ja_corretos": 0,
            "erros": 0,
        }

        # 1. Vincular projetos à gerência Individual
        self.stdout.write("-" * 50)
        self.stdout.write("VINCULANDO PROJETOS À GERÊNCIA INDIVIDUAL:")
        self.stdout.write("-" * 50)

        for projeto_id in CORRECOES["vincular_individual"]:
            try:
                projeto = Projeto.objects.get(id=projeto_id)
            except Projeto.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] Projeto ID={projeto_id} não existe")
                )
                continue

            if projeto.gerencia_id == individual.id:
                self.stdout.write(f"  [OK] {projeto.nome} já está em Individual")
                stats["ja_corretos"] += 1
                continue

            atual = projeto.gerencia.nome_setor if projeto.gerencia else "NENHUMA"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [+] {projeto.nome}: {atual} → Individual"
                )
            )

            if apply:
                projeto.gerencia = individual
                projeto.save(update_fields=["gerencia"])

            stats["vinculados"] += 1

        # 2. Remover projetos duplicatas
        self.stdout.write("")
        self.stdout.write("-" * 50)
        self.stdout.write("REMOVENDO PROJETOS DUPLICATAS:")
        self.stdout.write("-" * 50)

        for projeto_id in CORRECOES["remover_duplicatas"]:
            try:
                projeto = Projeto.objects.get(id=projeto_id)
            except Projeto.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] Projeto ID={projeto_id} não existe")
                )
                continue

            # Verificar se tem solicitações vinculadas
            sol_count = Solicitacao.objects.filter(projeto_id=projeto_id).count()
            if sol_count > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f"  [BLOQUEADO] {projeto.nome}: tem {sol_count} solicitações vinculadas"
                    )
                )
                stats["skipped_com_solicitacoes"] += 1
                continue

            self.stdout.write(
                self.style.SUCCESS(f"  [-] {projeto.nome} (ID={projeto_id})")
            )

            if apply:
                projeto.delete()

            stats["removidos"] += 1

        # Resumo
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("RESUMO")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Projetos vinculados a Individual: {stats['vinculados']}")
        self.stdout.write(f"Projetos removidos (duplicatas): {stats['removidos']}")
        self.stdout.write(f"Já corretos (skip): {stats['ja_corretos']}")
        self.stdout.write(f"Bloqueados (têm solicitações): {stats['skipped_com_solicitacoes']}")
        self.stdout.write(f"Erros: {stats['erros']}")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("DRY-RUN: Nenhuma alteração foi feita no banco.")
            )
            self.stdout.write("Execute com --apply para aplicar as alterações.")
