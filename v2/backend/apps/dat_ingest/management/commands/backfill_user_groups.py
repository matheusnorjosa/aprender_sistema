"""
Backfill: Atribui grupos aos usuários baseado em suas participações históricas.

CONTEXTO:
Os usuários foram importados das planilhas mas os grupos não foram atribuídos.
Este comando analisa as participações existentes e atribui os grupos corretos.

REGRAS:
1. Usuários com participações como COORDENADOR → Grupo "Coordenador"
2. Usuários com participações como FORMADOR → Grupo "Formador"
3. Usuários sem participações → não atribui grupo (decisão manual)
4. Usuários que já têm grupo → preserva grupo existente (não sobrescreve)

USO:
    python manage.py backfill_user_groups --dry-run  # Simula
    python manage.py backfill_user_groups --apply     # Aplica
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.db.models import Count, Q

from apps.core.models import Usuario


class Command(BaseCommand):
    help = "Atribui grupos aos usuários baseado em participações históricas"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem writes no banco",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica mudanças no banco",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options.get("dry_run", False)
        apply = options.get("apply", False)

        # Default para dry-run se nenhum especificado
        if not dry_run and not apply:
            dry_run = True

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("BACKFILL USER GROUPS")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Modo: {'DRY-RUN' if dry_run else 'APLICAR'}\n")

        # Buscar grupos
        try:
            grupo_formador = Group.objects.get(name="Formador")
            grupo_coordenador = Group.objects.get(name="Coordenador")
        except Group.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"❌ Grupo não encontrado: {e}"))
            return

        # Buscar usuários com participações mas sem grupo
        usuarios_sem_grupo = Usuario.objects.annotate(num_participacoes=Count("event_participations")).filter(
            num_participacoes__gt=0, groups__isnull=True
        )

        self.stdout.write(f"📊 Usuários com participações mas sem grupo: {usuarios_sem_grupo.count()}\n")

        stats = {
            "atribuido_formador": 0,
            "atribuido_coordenador": 0,
            "sem_participacoes": 0,
            "ja_tem_grupo": 0,
            "erros": 0,
        }

        for usuario in usuarios_sem_grupo:
            # Contar participações por role (para exibição)
            num_coordenador = usuario.event_participations.filter(role="COORDENADOR").count()
            num_formador = usuario.event_participations.filter(role="FORMADOR").count()
            total_participacoes = usuario.event_participations.count()

            # REGRA CORRETA: Baseado no USERNAME, não nas participações
            # Motivo: As participações foram importadas incorretamente (Maria Nadir é exemplo)
            # Usuários com username "coordenacao*" estão na coluna N da planilha (Coordenador)
            if usuario.username.lower().startswith("coordenacao"):
                grupo = grupo_coordenador
                role_label = "Coordenador (username)"
                stats["atribuido_coordenador"] += 1
            elif total_participacoes > 0:
                # Usuários com participações (mas não coordenacao*) → Formador
                grupo = grupo_formador
                role_label = "Formador (participações)"
                stats["atribuido_formador"] += 1
            else:
                # Sem participações e sem padrão coordenacao
                self.stdout.write(self.style.WARNING(f"  ⚠️  {usuario.username:30s} | Sem participações (skip)"))
                stats["sem_participacoes"] += 1
                continue

            # Aplicar mudança
            if apply:
                try:
                    with transaction.atomic():
                        usuario.groups.add(grupo)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✅ {usuario.username:30s} | F:{num_formador:3d} C:{num_coordenador:2d} → Grupo: {role_label}"
                            )
                        )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro ao atribuir grupo para {usuario.username}: {e}"))
                    stats["erros"] += 1
            else:
                # Dry-run
                self.stdout.write(
                    f"  🔍 [DRY-RUN] {usuario.username:30s} | F:{num_formador:3d} C:{num_coordenador:2d} → Grupo: {role_label}"
                )

        # Verificar usuários que já têm grupo
        usuarios_com_grupo = Usuario.objects.annotate(num_grupos=Count("groups")).filter(num_grupos__gt=0)
        stats["ja_tem_grupo"] = usuarios_com_grupo.count()

        # Sumário
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("📊 SUMÁRIO:")
        self.stdout.write(f"   Atribuído 'Formador': {stats['atribuido_formador']}")
        self.stdout.write(f"   Atribuído 'Coordenador': {stats['atribuido_coordenador']}")
        self.stdout.write(f"   Sem participações (skip): {stats['sem_participacoes']}")
        self.stdout.write(f"   Já tinham grupo: {stats['ja_tem_grupo']}")
        self.stdout.write(f"   Erros: {stats['erros']}")
        self.stdout.write("-" * 80)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  DRY-RUN: Use --apply para aplicar as mudanças"))

        self.stdout.write("\n✅ Backfill concluído!\n")
