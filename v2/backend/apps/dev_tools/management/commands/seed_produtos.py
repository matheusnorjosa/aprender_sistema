"""
Seed inicial de Produtos baseado em produtos.xlsx.

Usage:
    python manage.py seed_produtos
"""

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.models import Produto, Projeto


# Mapeamento simplificado: código → (nome, projeto_nome)
# Baseado em produtos.xlsx e mapeamento de compras
PRODUTOS = [
    # Novo Lendo
    ("NL-C1", "Novo Lendo - Coleção 1", "NOVO LENDO"),
    ("NL-C2", "Novo Lendo - Coleção 2", "NOVO LENDO"),
    ("NL-C3", "Novo Lendo - Coleção 3", "NOVO LENDO"),
    ("NL-KB", "Novo Lendo - Kit Berçário", "NOVO LENDO"),
    ("NL-KM", "Novo Lendo - Kit Maternal", "NOVO LENDO"),
    # Gestão Escolar
    ("GE-KB", "Gestão Escolar - Kit Base", "GESTÃO ESCOLAR (IDEB10)"),
    ("GE-KC", "Gestão Escolar - Kit Completo", "GESTÃO ESCOLAR (IDEB10)"),
    # Acerta Matemática
    ("AM-C1", "Acerta Matemática - Coleção 1", "ACERTA MATEMÁTICA"),
    ("AM-C2", "Acerta Matemática - Coleção 2", "ACERTA MATEMÁTICA"),
    # Acerta Português
    ("AP-C1", "Acerta Português - Coleção 1", "ACERTA PORTUGUÊS"),
    ("AP-C2", "Acerta Português - Coleção 2", "ACERTA PORTUGUÊS"),
    # Vida e Ciências
    ("VC-C1", "Vida e Ciências - Coleção 1", "VIDA E CIÊNCIAS"),
    # Vida e Linguagem
    ("VL-C1", "Vida e Linguagem - Coleção 1", "VIDA E LINGUAGEM"),
    # Vida e Matemática
    ("VM-C1", "Vida e Matemática - Coleção 1", "VIDA E MATEMÁTICA"),
    # Fluir das Emoções
    ("FE-C1", "Fluir das Emoções - Coleção 1", "FLUIR DAS EMOÇÕES"),
    ("FE-C2", "Fluir das Emoções - Coleção 2", "FLUIR DAS EMOÇÕES - 1"),
    ("FE-C3", "Fluir das Emoções - Coleção 3", "FLUIR DAS EMOÇÕES - 2"),
    # Projeto Amma
    ("PA-C1", "Projeto Amma - Coleção 1", "PROJETO AMMA"),
    # Cirandar
    ("CI-C1", "Cirandar - Coleção 1", "CIRANDAR"),
    # Lendo e Escrevendo
    ("LE-C1", "Lendo e Escrevendo - Coleção 1", "LENDO E ESCREVENDO"),
    # Brincando e Aprendendo
    ("BA-C1", "Brincando e Aprendendo - Coleção 1", "BRINCANDO E APRENDENDO"),
    # Sou da Paz
    ("SP-C1", "Sou da Paz - Coleção 1", "SOU DA PAZ"),
]


class Command(BaseCommand):
    help = "Seed inicial de produtos (principais produtos)"

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        self.stdout.write("Seeding produtos...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for codigo, nome, projeto_nome in PRODUTOS:
            try:
                # Resolver projeto
                try:
                    projeto = Projeto.objects.get(nome=projeto_nome)
                except Projeto.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Projeto não encontrado: {projeto_nome} (produto: {codigo})"
                        )
                    )
                    skipped_count += 1
                    continue

                # Get or create produto
                produto, created = Produto.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        "nome": nome,
                        "projeto": projeto,
                        "ativo": True,
                    },
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Created: {codigo} - {nome} ({projeto_nome})"
                        )
                    )
                else:
                    # Update se mudou
                    updated = False
                    if produto.nome != nome:
                        produto.nome = nome
                        updated = True
                    if produto.projeto != projeto:  # type: ignore[misc]
                        produto.projeto = projeto  # type: ignore[assignment]
                        updated = True

                    if updated:
                        produto.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⟳ Updated: {codigo} - {nome}"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"  - Skipped (already exists): {codigo}"
                        )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ Error processing {codigo}: {e}"
                    )
                )
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seed complete: {created_count} created, {updated_count} updated, "
                f"{skipped_count} skipped, {len(PRODUTOS)} total"
            )
        )
