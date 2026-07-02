"""Seed do catalogo canonico de Projetos (go-live).

Lista curada pelo dono do dado (a partir da planilha canonica de produtos, agrupada por
projeto). fluxo: SUPER = projetos da Superintendencia (exigem aprovacao PA-01); os demais
NAO_SUPER (auto-aprovado).

create-only + idempotente (get_or_create por nome; NUNCA sobrescreve o fluxo de um projeto
que ja existe). Fica em `apps.core` (nao em dev_tools) para sobreviver ao CP-08
(INCLUDE_DEV_TOOLS=false em prod). Sem PII.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.models import Projeto

_FLUXOS = {"SUPER", "NAO_SUPER"}

# 33 projetos canonicos (11 SUPER). Nomes definitivos revisados pelo dono do dado.
PROJETOS_CANONICOS: list[tuple[str, str]] = [
    ("A Cor da Gente", "NAO_SUPER"),
    ("ACerta Matemática", "NAO_SUPER"),
    ("ACerta Português", "NAO_SUPER"),
    ("Avançando Juntos Matemática", "NAO_SUPER"),
    ("Avançando Juntos Português", "NAO_SUPER"),
    ("Brincando e Aprendendo", "NAO_SUPER"),
    ("Cirandar", "SUPER"),
    ("ECS", "NAO_SUPER"),
    ("Educação Financeira", "NAO_SUPER"),
    ("Fluir das Emoções", "NAO_SUPER"),
    ("Fluir das Emoções 1", "NAO_SUPER"),
    ("Fluir das Emoções 2", "NAO_SUPER"),
    ("Fluir das Emoções 3", "NAO_SUPER"),
    ("Gestão Escolar", "NAO_SUPER"),
    ("Leio, Escrevo e Calculo", "NAO_SUPER"),
    ("Lendo e Escrevendo", "SUPER"),
    ("Ler, Ouvir e Contar", "SUPER"),
    ("My Companion", "NAO_SUPER"),
    ("NL e AMMA Português e Matemática", "SUPER"),
    ("Novo Lendo", "SUPER"),
    ("Projeto Amma", "SUPER"),
    ("Projeto Catavento 2", "SUPER"),
    ("Projeto Catavento 3", "SUPER"),
    ("Projeto Miudezas e Descobertas", "SUPER"),
    ("Sou da Paz", "NAO_SUPER"),
    ("Superativar Linguagens", "NAO_SUPER"),
    ("Superativar Matemática", "NAO_SUPER"),
    ("TEMA", "SUPER"),
    ("Trânsito Legal", "NAO_SUPER"),
    ("Uni Duni Tê", "SUPER"),
    ("Vida e Ciências", "NAO_SUPER"),
    ("Vida e Linguagem", "NAO_SUPER"),
    ("Vida e Matemática", "NAO_SUPER"),
]


def seed_projetos_canonicos(projetos: list[tuple[str, str]]) -> dict[str, int]:
    """Cria projetos (create-only por nome). Retorna counts; NUNCA sobrescreve fluxo existente."""
    stats = {"created": 0, "existing": 0, "rejected": 0}
    for nome_raw, fluxo_raw in projetos:
        nome = (nome_raw or "").strip()
        fluxo = (fluxo_raw or "").strip().upper()
        if not nome or fluxo not in _FLUXOS:
            stats["rejected"] += 1
            continue
        _, created = Projeto.objects.get_or_create(nome=nome, defaults={"fluxo": fluxo})
        stats["created" if created else "existing"] += 1
    return stats


class Command(BaseCommand):
    help = "Seed do catalogo canonico de Projetos (create-only, idempotente)"

    def handle(self, *args: Any, **options: Any) -> None:
        stats = seed_projetos_canonicos(PROJETOS_CANONICOS)
        self.stdout.write(
            self.style.SUCCESS(
                f"Projetos: {stats['created']} criados, {stats['existing']} existentes, "
                f"{stats['rejected']} rejeitados"
            )
        )
        self.stdout.write(f"Total no banco: {Projeto.objects.count()}")
