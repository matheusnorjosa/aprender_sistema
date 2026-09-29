"""
Define `Gerencia.nome_exibicao` (nome do setor na tela) das 13 gerências ativas de prod.

PR A — setor = gerência na tela (PLANOS_LIBERACAO_2026-09-29 §2, "Dado de produção").
Mapa do dono medido em prod em 2026-09-29 (só leitura). As gerências 5, 10, 13, 14, 15,
18, 20 e 24 estão inativas e ficam fora.

Proteção contra ambiente errado: se algum id não existir, ou se o `nome` (código
interno) não for o esperado, aborta tudo sem gravar nada.

Uso:
    python manage.py definir_nome_exibicao_gerencias           # dry-run (padrão)
    python manage.py definir_nome_exibicao_gerencias --apply   # grava
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import AuditLog, Gerencia
from apps.core.services.audit import registrar_auditoria

if TYPE_CHECKING:
    from argparse import ArgumentParser

# (id, nome esperado, nome_exibicao)
NOMES_EXIBICAO: list[tuple[int, str, str]] = [
    (1, "SUPERINTENDENCIA", "Superintendência"),
    (2, "GERENCIA 2", "Vidas"),
    (3, "GERENCIA 3", "Fluir"),
    (4, "GERENCIA 4", "Superativar"),
    (6, "GERENCIA 6", "Sou da Paz"),
    (8, "INDIVIDUAL - A COR DA GENTE", "A Cor da Gente"),
    (9, "INDIVIDUAL - ED FINANCEIRA", "Educação Financeira"),
    (11, "INDIVIDUAL - MY COMPANION", "My Companion"),
    (12, "INDIVIDUAL - TRÂNSITO LEGAL", "Trânsito Legal"),
    (16, "GERENCIA IDEB 10", "Gestão Escolar"),
    (17, "GERENCIA BRINCANDO", "Brincando e Aprendendo"),
    (19, "GERENCIA DAT", "DAT"),
    (22, "LER, OUVIR E CONTAR", "Ler, Ouvir e Contar"),
]


class Command(BaseCommand):
    help = "Define o nome de tela (nome_exibicao) das gerências ativas. Dry-run por padrão; --apply grava."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--apply", action="store_true", help="Grava as alterações (sem ele, só mostra).")

    def handle(self, *args: Any, **options: Any) -> None:
        apply: bool = options["apply"]
        ids = [gid for gid, _, _ in NOMES_EXIBICAO]

        with transaction.atomic():
            gerencias = Gerencia.objects.select_for_update().in_bulk(ids)
            erros = [f"id {gid}: não existe" for gid in ids if gid not in gerencias]
            erros += [
                f"id {gid}: nome é {gerencias[gid].nome!r}, esperado {nome!r}"
                for gid, nome, _ in NOMES_EXIBICAO
                if gid in gerencias and gerencias[gid].nome != nome
            ]
            if erros:
                raise CommandError("Ambiente não confere; nada foi gravado. " + "; ".join(erros))

            self.stdout.write("APPLY" if apply else "DRY-RUN (nada é gravado; use --apply)")
            alteradas = iguais = 0
            for gid, nome, novo in NOMES_EXIBICAO:
                g = gerencias[gid]
                antes = g.nome_exibicao
                if antes == novo:
                    iguais += 1
                    self.stdout.write(f"  = {gid} {nome}: {novo!r}")
                    continue
                alteradas += 1
                self.stdout.write(f"  ~ {gid} {nome}: {antes!r} -> {novo!r}")
                if apply:
                    g.nome_exibicao = novo
                    g.save(update_fields=["nome_exibicao"])
                    registrar_auditoria(
                        actor=None,  # comando CLI de admin; sem request user
                        action=AuditLog.Action.UPDATE,
                        model_name="Gerencia",
                        details={
                            "gerencia_id": gid,
                            "campo": "nome_exibicao",
                            "antes": antes,
                            "depois": novo,
                            "origem": "definir_nome_exibicao_gerencias",
                        },
                    )

        if apply:
            self.stdout.write(self.style.SUCCESS(f"{alteradas} alteradas, {iguais} iguais."))
        else:
            self.stdout.write(f"{alteradas} a alterar, {iguais} iguais.")
