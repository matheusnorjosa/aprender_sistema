"""
Seed de Gerências baseado no mapeamento organizacional confirmado.

Gerência = Setor (mesma entidade, nomenclaturas diferentes).
- "GERENCIA 2" = nome interno/burocrático
- "Vidas" = nome comercial/operacional (nome_setor)

Usage:
    python manage.py seed_gerencias
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.models import Gerencia

GERENCIAS = [
    {
        "nome": "SUPERINTENDENCIA",
        "nome_setor": "Super",
        "descricao": "Projetos SUPER que requerem aprovação manual (CIRANDAR, LENDO E ESCREVENDO, NOVO LENDO, TEMA, UNI DUNI TÊ, etc.)",
    },
    {
        "nome": "GERENCIA 2",
        "nome_setor": "Vidas",
        "descricao": "VIDA E CIÊNCIAS, VIDA E LINGUAGEM, VIDA E MATEMÁTICA, AVANÇANDO JUNTOS MAT/PORT",
    },
    {
        "nome": "GERENCIA 3",
        "nome_setor": "Fluir",
        "descricao": "FLUIR DAS EMOÇÕES",
    },
    {
        "nome": "GERENCIA 4",
        "nome_setor": "ACerta",
        "descricao": "ACERTA PORTUGUÊS, ACERTA MATEMÁTICA, ECS, SUPERATIVAR, LEIO ESCREVO E CALCULO",
    },
    {
        "nome": "GERENCIA 5",
        "nome_setor": "Brincando",
        "descricao": "BRINCANDO E APRENDENDO",
    },
    {
        "nome": "GERENCIA 6",
        "nome_setor": "Sou da Paz",
        "descricao": "SOU DA PAZ",
    },
    {
        "nome": "INDIVIDUAL - A COR DA GENTE",
        "nome_setor": "A Cor da Gente",
        "descricao": "A COR DA GENTE",
    },
    {
        "nome": "INDIVIDUAL - ED FINANCEIRA",
        "nome_setor": "Ed Financeira",
        "descricao": "ED FINANCEIRA",
    },
    {
        "nome": "INDIVIDUAL - GESTÃO ESCOLAR",
        "nome_setor": "Gestão Escolar",
        "descricao": "GESTÃO ESCOLAR",
    },
    {
        "nome": "INDIVIDUAL - MY COMPANION",
        "nome_setor": "My Companion",
        "descricao": "MY COMPANION",
    },
    {
        "nome": "INDIVIDUAL - TRÂNSITO LEGAL",
        "nome_setor": "Trânsito Legal",
        "descricao": "TRÂNSITO LEGAL",
    },
]

# Old unified record to remove when splitting
DEPRECATED_GERENCIAS = ["GERENCIA INDIVIDUAL", "INDIVIDUAL - UNI DUNI TÊ"]


class Command(BaseCommand):
    help = "Seed de gerências organizacionais (11 registros, idempotente)"

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        self.stdout.write("Seeding gerências...")

        # Remove deprecated unified records (safe only if no EquipeGerencia links)
        for nome in DEPRECATED_GERENCIAS:
            deleted, _ = Gerencia.objects.filter(nome=nome).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f"  ✗ Removed deprecated: {nome}"))

        created_count = 0
        updated_count = 0

        for gerencia_data in GERENCIAS:
            gerencia, created = Gerencia.objects.get_or_create(
                nome=gerencia_data["nome"],
                defaults={
                    "nome_setor": gerencia_data["nome_setor"],
                    "descricao": gerencia_data["descricao"],
                    "ativo": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {gerencia.nome} ({gerencia.nome_setor})"))
            else:
                updated = False
                if gerencia.nome_setor != gerencia_data["nome_setor"]:
                    gerencia.nome_setor = gerencia_data["nome_setor"]
                    updated = True
                if gerencia.descricao != gerencia_data["descricao"]:
                    gerencia.descricao = gerencia_data["descricao"]
                    updated = True

                if updated:
                    gerencia.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"  ⟳ Updated: {gerencia.nome} ({gerencia.nome_setor})"))
                else:
                    self.stdout.write(f"  - Skipped: {gerencia.nome} (already exists)")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seed complete: {created_count} created, " f"{updated_count} updated, {len(GERENCIAS)} total"
            )
        )
