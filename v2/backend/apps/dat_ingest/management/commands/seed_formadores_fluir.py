"""
Seed dos 9 formadores únicos do projeto Fluir das Emoções.

Usage:
    python manage.py seed_formadores_fluir

Idempotence:
    - Usa get_or_create() por username normalizado
    - Não cria duplicatas se já existirem

Output:
    - Relatório de formadores criados/atualizados/skipped
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.core.models import Usuario
from apps.dat_ingest.services.parse_fluir import get_formadores_fluir


class Command(BaseCommand):
    """Seed formadores Fluir no banco de dados."""

    help = "Seed 9 formadores do projeto Fluir das Emoções"

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        """Seed formadores Fluir com idempotência."""
        self.stdout.write("=" * 60)
        self.stdout.write("SEED FORMADORES FLUIR")
        self.stdout.write("=" * 60)

        # Garantir que grupo "Formador" existe
        grupo_formador, _ = Group.objects.get_or_create(name="Formador")

        formadores_nomes = get_formadores_fluir()
        stats = {"created": 0, "updated": 0, "skipped": 0}

        for idx, nome_completo in enumerate(formadores_nomes, 1):
            # Normalizar username (remover acentos, espaços → underscore, lowercase)
            username = self._normalize_username(nome_completo)

            # get_or_create por username
            usuario, created = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    "cpf": f"999{idx:08d}",  # CPF fictício: 99900000001, 99900000002, etc.
                    "email": f"{username}@aprender.local",
                    "first_name": self._get_first_name(nome_completo),
                    "last_name": self._get_last_name(nome_completo),
                    "cargo": "Formador",
                    "is_active": True,
                },
            )

            if created:
                stats["created"] += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ Criado: {nome_completo} ({username})"))
            else:
                # Atualizar campos se necessário
                updated = False
                if usuario.cargo != "Formador":
                    usuario.cargo = "Formador"
                    updated = True
                if updated:
                    usuario.save()
                    stats["updated"] += 1
                    self.stdout.write(self.style.WARNING(f"  🔄 Atualizado: {nome_completo} ({username})"))
                else:
                    stats["skipped"] += 1
                    self.stdout.write(self.style.NOTICE(f"  ⏭️  Já existe: {nome_completo} ({username})"))

            # Adicionar ao grupo Formador se não estiver
            if not usuario.groups.filter(name="Formador").exists():
                usuario.groups.add(grupo_formador)
                self.stdout.write(self.style.NOTICE("      ➕ Adicionado ao grupo Formador"))

        # Resumo
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RESUMO:")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Criados: {stats['created']}")
        self.stdout.write(f"  Atualizados: {stats['updated']}")
        self.stdout.write(f"  Já existiam: {stats['skipped']}")
        self.stdout.write(f"  Total processado: {len(formadores_nomes)}")
        self.stdout.write("=" * 60)

    def _normalize_username(self, nome_completo: str) -> str:
        """
        Normaliza nome completo para username.

        Examples:
            "Adeliana Mówima Falcao Machado" → "adeliana_mowima_falcao_machado"
            "Jéssica Nunes Apolonio" → "jessica_nunes_apolonio"
        """
        import unicodedata

        # Remover acentos
        nome_sem_acento = "".join(
            c for c in unicodedata.normalize("NFD", nome_completo) if unicodedata.category(c) != "Mn"
        )

        # Lowercase + substituir espaços por underscore
        username = nome_sem_acento.lower().replace(" ", "_")

        return username

    def _get_first_name(self, nome_completo: str) -> str:
        """Extrai primeiro nome."""
        return nome_completo.split()[0]

    def _get_last_name(self, nome_completo: str) -> str:
        """Extrai sobrenome (tudo após primeiro nome)."""
        parts = nome_completo.split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""
