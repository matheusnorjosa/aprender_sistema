"""
Seed inicial de Gerências baseado em mapeamento de produtos.

Usage:
    python manage.py seed_gerencias
"""

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.models import Gerencia


GERENCIAS = [
    {
        "nome": "SUPERINTENDENCIA",
        "nome_setor": "Super",
        "descricao": "Projetos SUPER que requerem aprovação manual",
    },
    {
        "nome": "GERENCIA 2",
        "nome_setor": "Vidas",
        "descricao": "VIDA E CIÊNCIAS, LINGUAGEM, MATEMÁTICA",
    },
    {
        "nome": "GERENCIA 3",
        "nome_setor": "Fluir",
        "descricao": "FLUIR DAS EMOÇÕES e coleções",
    },
    {
        "nome": "GERENCIA 4",
        "nome_setor": "ACerta",
        "descricao": "ACERTA MATEMÁTICA, PORTUGUÊS, ECS, SUPERATIVAR, LEIO ESCREVO",
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
        "nome": "GERENCIA INDIVIDUAL",
        "nome_setor": "Individual",
        "descricao": "Projetos com gerência individual (A COR DA GENTE, ED FINANCEIRA, GESTÃO ESCOLAR, etc.)",
    },
]


class Command(BaseCommand):
    help = "Seed inicial de gerências (7 registros)"

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        self.stdout.write("Seeding gerências...")

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
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Created: {gerencia.nome} ({gerencia.nome_setor})"
                    )
                )
            else:
                # Atualizar campos se mudaram
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
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⟳ Updated: {gerencia.nome} ({gerencia.nome_setor})"
                        )
                    )
                else:
                    self.stdout.write(
                        f"  - Skipped (already exists): {gerencia.nome}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seed complete: {created_count} created, {updated_count} updated, {len(GERENCIAS)} total"
            )
        )
