"""
Command para corrigir grupos de usuários baseado em padrões de email e nome
"""

import re

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Usuario


class Command(BaseCommand):
    help = "Corrige a atribuição de grupos para usuários baseado em padrões"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa sem fazer alterações no banco",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== CORREÇÃO DE GRUPOS DE USUÁRIOS ==="))

        dry_run = options["dry_run"]

        # Estatísticas
        stats = {
            "coordenadores": 0,
            "superintendencia": 0,
            "formadores": 0,
            "controle": 0,
            "diretoria": 0,
            "admin": 0,
            "sem_grupo": 0,
        }

        try:
            with transaction.atomic():
                # Buscar usuários sem grupo
                usuarios_sem_grupo = Usuario.objects.filter(groups__isnull=True)

                self.stdout.write(f"Usuários sem grupo: {usuarios_sem_grupo.count()}")

                for usuario in usuarios_sem_grupo:
                    try:
                        grupo_sugerido = self.identificar_grupo(usuario)

                        if grupo_sugerido:
                            if grupo_sugerido not in stats:
                                stats[grupo_sugerido] = 0
                            stats[grupo_sugerido] += 1

                            if not dry_run:
                                try:
                                    group = Group.objects.get(name=grupo_sugerido)
                                    usuario.groups.add(group)
                                except Group.DoesNotExist:
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f'  Grupo "{grupo_sugerido}" nao encontrado para {usuario.username}'
                                        )
                                    )
                                    stats["sem_grupo"] += 1
                                    continue

                            self.stdout.write(
                                f"  {usuario.username} -> {grupo_sugerido}"
                            )
                        else:
                            stats["sem_grupo"] += 1
                            self.stdout.write(
                                f"  {usuario.username} -> SEM GRUPO (manual)"
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Erro ao processar {usuario.username}: {str(e)}"
                            )
                        )
                        stats["sem_grupo"] += 1

                if dry_run:
                    raise transaction.TransactionManagementError("Dry run - rollback")

        except transaction.TransactionManagementError:
            if not dry_run:
                raise
            self.stdout.write(
                self.style.WARNING("DRY RUN - Nenhuma alteração foi feita")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro durante correção: {str(e)}"))

        # Exibir estatísticas
        self.stdout.write(self.style.SUCCESS("\\n=== ESTATÍSTICAS ==="))
        for grupo, count in stats.items():
            if count > 0:
                self.stdout.write(f"{grupo}: {count} usuários")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\\nMODO DRY RUN - Execute sem --dry-run para aplicar"
                )
            )

    def identificar_grupo(self, usuario):
        """
        Identifica grupo baseado em padrões de email e nome
        """
        email = usuario.email.lower() if usuario.email else ""
        username = usuario.username.lower() if usuario.username else ""
        first_name = usuario.first_name.lower() if usuario.first_name else ""
        last_name = usuario.last_name.lower() if usuario.last_name else ""

        # Padrões para COORDENADORES
        if any(
            [
                "coordenacao" in email,
                "coord" in email and "@aprendereditora" in email,
                "coordenador" in first_name or "coordenador" in last_name,
                "coordenadora" in first_name or "coordenadora" in last_name,
                re.match(
                    r"coordenacao\d+@", email
                ),  # coordenacao1@, coordenacao2@, etc.
            ]
        ):
            return "coordenador"

        # Padrões para SUPERINTENDÊNCIA
        if any(
            [
                "superintend" in email,
                "super" in email and "@aprendereditora" in email,
                "direcao" in email,
                "gerencia" in email,
                "superintend" in first_name or "superintend" in last_name,
                username
                in ["mateus", "matheusadm", "admin"],  # Usuários administrativos
            ]
        ):
            return "superintendencia"

        # Padrões para FORMADORES
        if any(
            [
                "formador" in email,
                "educador" in email,
                "professor" in email,
                "instrutor" in email,
                "formador" in first_name or "formador" in last_name,
                "educador" in first_name or "educador" in last_name,
                "professor" in first_name or "professor" in last_name,
                "prof" in first_name,
            ]
        ):
            return "formador"

        # Padrões para CONTROLE
        if any(
            [
                "controle" in email,
                "control" in email,
                "analista" in email,
                "operacao" in email,
                "controle" in first_name or "controle" in last_name,
            ]
        ):
            return "controle"

        # Padrões para DIRETORIA
        if any(
            [
                "diretor" in email,
                "diretora" in email,
                "direcao" in email,
                "ceo" in email,
                "presidente" in email,
                "diretor" in first_name or "diretor" in last_name,
                "diretora" in first_name or "diretora" in last_name,
            ]
        ):
            return "diretoria"

        # Padrões para ADMIN
        if any(
            [
                username in ["admin", "administrator", "root", "matheusadm"],
                "admin" in email,
                email.endswith("@aprendereditora.com.br")
                and any(["sistema" in email, "tech" in email, "ti" in email]),
            ]
        ):
            return "admin"

        # Heurística baseada no domínio do email
        if "@aprendereditora.com.br" in email:
            # Se é da empresa mas não se encaixa em outros padrões,
            # provavelmente é coordenador
            return "coordenador"

        # Caso não se encaixe em nenhum padrão
        return None

    def exibir_grupos_atuais(self):
        """Exibe situação atual dos grupos"""
        self.stdout.write("\\n=== SITUAÇÃO ATUAL ===")
        for group in Group.objects.all():
            count = group.user_set.count()
            self.stdout.write(f"{group.name}: {count} usuários")

        sem_grupo = Usuario.objects.filter(groups__isnull=True).count()
        self.stdout.write(f"Sem grupo: {sem_grupo} usuários")
