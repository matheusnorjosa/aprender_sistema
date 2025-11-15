"""
Vincula projetos existentes às gerências baseado em mapeamento.

Usage:
    python manage.py link_projetos_gerencias --dry-run  # Preview
    python manage.py link_projetos_gerencias --apply    # Apply
"""

from django.core.management.base import BaseCommand

from apps.core.models import Gerencia, Projeto


# Mapeamento gerência → projetos
MAPEAMENTO = {
    "SUPERINTENDENCIA": [
        "CIRANDAR",
        "LENDO E ESCREVENDO",
        "LER, OUVIR E CONTAR",
        "NOVO LENDO",
        "PROJETO AMMA",
        "PROJETO CATAVENTO 2",
        "PROJETO CATAVENTO 3",
        "PROJETO MIUDEZAS E DESCOBERTAS",
        "TEMA",
        "UNI DUNI TÊ",
    ],
    "GERENCIA 2": [
        "VIDA E CIÊNCIAS",
        "VIDA E LINGUAGEM",
        "VIDA E MATEMÁTICA",
    ],
    "GERENCIA 3": [
        "FLUIR DAS EMOÇÕES",
        "FLUIR DAS EMOÇÕES - 1",
        "FLUIR DAS EMOÇÕES - 2",
        "FLUIR DAS EMOÇÕES - 3",
    ],
    "GERENCIA 4": [
        "ACERTA MATEMÁTICA",
        "ACERTA PORTUGUÊS",
        "ECS",
        "LEIO, ESCREVO E CALCULO",
        "SUPERATIVAR - LINGUAGENS",
        "SUPERATIVAR - MATEMÁTICA",
    ],
    "GERENCIA 5": [
        "BRINCANDO E APRENDENDO",
    ],
    "GERENCIA 6": [
        "SOU DA PAZ",
    ],
    "GERENCIA INDIVIDUAL": [
        "A COR DA GENTE",
        "AVANÇANDO JUNTOS MATEMÁTICA",
        "AVANÇANDO JUNTOS PORTUGUÊS",
        "ED FINANCEIRA",
        "GESTÃO ESCOLAR (IDEB10)",
        "TRÂNSITO LEGAL",
    ],
}


class Command(BaseCommand):
    help = "Vincula projetos existentes às gerências"

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--dry-run", action="store_true", help="Preview only")
        parser.add_argument("--apply", action="store_true", help="Apply changes")

    def handle(self, *args: tuple, **options: dict) -> None:  # type: ignore[type-arg]
        dry_run = options.get("dry_run", False)
        apply_mode = options.get("apply", False)

        if not dry_run and not apply_mode:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Error: Use --dry-run (preview) or --apply (commit)"
                )
            )
            return

        mode = "DRY-RUN" if dry_run else "APPLY"
        self.stdout.write(f"Linking projetos to gerências ({mode})...\n")

        stats = {"linked": 0, "skipped": 0, "not_found": 0}

        for gerencia_nome, projeto_nomes in MAPEAMENTO.items():
            try:
                gerencia = Gerencia.objects.get(nome=gerencia_nome)
            except Gerencia.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ Gerencia not found: {gerencia_nome} (run seed_gerencias first)"
                    )
                )
                continue

            self.stdout.write(f"\n{gerencia.nome} ({gerencia.nome_setor}):")

            for projeto_nome in projeto_nomes:
                try:
                    projeto = Projeto.objects.get(nome=projeto_nome)

                    if projeto.gerencia == gerencia:
                        self.stdout.write(f"  - Skip: {projeto_nome} (already linked)")
                        stats["skipped"] += 1
                    else:
                        if apply_mode:
                            projeto.gerencia = gerencia
                            projeto.save(update_fields=["gerencia"])
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✓ Linked: {projeto_nome} → {gerencia.nome_setor}"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  ⟳ Would link: {projeto_nome} → {gerencia.nome_setor}"
                                )
                            )
                        stats["linked"] += 1

                except Projeto.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ Projeto not found: {projeto_nome}")
                    )
                    stats["not_found"] += 1

        # Summary
        self.stdout.write(
            f"\n{'=' * 60}\n"
            f"Mode: {mode}\n"
            f"Linked: {stats['linked']}\n"
            f"Skipped: {stats['skipped']}\n"
            f"Not found: {stats['not_found']}\n"
            f"{'=' * 60}"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Dry-run mode: No changes made. Use --apply to commit."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ {stats['linked']} projetos linked!")
            )
