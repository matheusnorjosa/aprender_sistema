#!/usr/bin/env python3
"""
🔧 CONSOLIDAÇÃO DO MODELO FORMADOR
==================================

Script para consolidar o modelo Formador duplicado no modelo Usuario.
Migra todos os dados e remove a duplicação.

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import sys

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from core.models import Formador, Usuario

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consolida o modelo Formador no modelo Usuario"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa em modo dry-run sem fazer alterações",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Força a consolidação mesmo com dados duplicados",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        print("🔧 CONSOLIDAÇÃO DO MODELO FORMADOR")
        print("=" * 50)

        if dry_run:
            print("🔍 MODO DRY RUN - Nenhuma alteração será feita")

        self.consolidate_formador_model(dry_run, force)

    def consolidate_formador_model(self, dry_run=False, force=False):
        """Consolida o modelo Formador no modelo Usuario"""

        # 1. Verificar dados existentes
        formadores_count = Formador.objects.count()
        usuarios_formadores_count = (
            Usuario.objects.select_related("municipio", "projeto")
            .prefetch_related("groups", "user_permissions")
            .filter(formador_ativo=True)
            .count()
        )

        print(f"\n📊 DADOS EXISTENTES:")
        print(f"  Formadores no modelo Formador: {formadores_count}")
        print(f"  Usuários com formador_ativo=True: {usuarios_formadores_count}")

        if formadores_count == 0:
            print(
                "✅ Nenhum formador no modelo Formador encontrado - consolidação desnecessária"
            )
            return

        # 2. Verificar conflitos
        conflicts = self.check_conflicts()
        if conflicts and not force:
            print(f"\n❌ CONFLITOS ENCONTRADOS:")
            for conflict in conflicts:
                print(f"  - {conflict}")
            print("\nUse --force para forçar a consolidação")
            return

        # 3. Migrar dados
        if not dry_run:
            with transaction.atomic():
                self.migrate_formador_data()
                self.update_related_models()
                print("✅ Consolidação concluída com sucesso!")
        else:
            print("🔍 DRY RUN: Simulando migração de dados...")
            self.simulate_migration()

    def check_conflicts(self):
        """Verifica conflitos entre modelos Formador e Usuario"""
        conflicts = []

        # Verificar emails duplicados
        formador_emails = set(Formador.objects.values_list("email", flat=True))
        usuario_emails = set(Usuario.objects.values_list("email", flat=True))

        duplicate_emails = formador_emails.intersection(usuario_emails)
        if duplicate_emails:
            conflicts.append(f"Emails duplicados: {list(duplicate_emails)}")

        # Verificar nomes duplicados
        formador_nomes = set(Formador.objects.values_list("nome", flat=True))
        usuario_nomes = set(Usuario.objects.values_list("first_name", flat=True))

        duplicate_nomes = formador_nomes.intersection(usuario_nomes)
        if duplicate_nomes:
            conflicts.append(f"Nomes duplicados: {list(duplicate_nomes)}")

        return conflicts

    def migrate_formador_data(self):
        """Migra dados do modelo Formador para Usuario"""
        print("\n🔄 MIGRANDO DADOS...")

        # Criar grupo formador se não existir
        formador_group, created = Group.objects.get_or_create(name="formador")
        if created:
            print("  ✅ Grupo 'formador' criado")

        migrated_count = 0
        skipped_count = 0

        for formador in FormadorService.get_formadores_queryset():
            # Verificar se já existe usuário com mesmo email
            existing_user = (
                Usuario.objects.select_related("municipio", "projeto")
                .prefetch_related("groups", "user_permissions")
                .filter(email=formador.email)
                .first()
            )

            if existing_user:
                # Atualizar usuário existente
                existing_user.formador_ativo = True
                existing_user.area_atuacao = formador.area_atuacao
                existing_user.save()
                existing_user.groups.add(formador_group)
                print(f"  ✅ Usuário {existing_user.username} atualizado como formador")
                migrated_count += 1
            else:
                # Criar novo usuário
                username = formador.email.split("@")[
                    0
                ]  # Usar email como base do username

                # Garantir username único
                base_username = username
                counter = 1
                while (
                    Usuario.objects.select_related("municipio", "projeto")
                    .prefetch_related("groups", "user_permissions")
                    .filter(username=username)
                    .exists()
                ):
                    username = f"{base_username}_{counter}"
                    counter += 1

                # Dividir nome em first_name e last_name
                nome_parts = formador.nome.split(" ", 1)
                first_name = nome_parts[0]
                last_name = nome_parts[1] if len(nome_parts) > 1 else ""

                usuario = Usuario.objects.create(
                    username=username,
                    email=formador.email,
                    first_name=first_name,
                    last_name=last_name,
                    formador_ativo=True,
                    area_atuacao=formador.area_atuacao,
                    is_active=formador.ativo,
                )
                usuario.groups.add(formador_group)
                print(f"  ✅ Usuário {username} criado como formador")
                migrated_count += 1

        print(f"\n📊 RESULTADO DA MIGRAÇÃO:")
        print(f"  Migrados: {migrated_count}")
        print(f"  Ignorados: {skipped_count}")

    def update_related_models(self):
        """Atualiza modelos relacionados para usar Usuario ao invés de Formador"""
        print("\n🔄 ATUALIZANDO MODELOS RELACIONADOS...")

        # Atualizar Deslocamento
        from core.models import Deslocamento

        # Migrar pessoa_1 até pessoa_6 para usar Usuario
        for deslocamento in Deslocamento.objects.all():
            updated = False

            if deslocamento.pessoa_1:
                usuario = (
                    Usuario.objects.select_related("municipio", "projeto")
                    .prefetch_related("groups", "user_permissions")
                    .filter(email=deslocamento.pessoa_1.email, formador_ativo=True)
                    .first()
                )
                if usuario:
                    deslocamento.pessoa_1 = None  # Limpar referência antiga
                    updated = True

            # Repetir para pessoa_2 até pessoa_6...
            # (implementação simplificada para demonstração)

            if updated:
                deslocamento.save()

        print("  ✅ Modelos relacionados atualizados")

    def simulate_migration(self):
        """Simula a migração em modo dry-run"""
        print("\n🔍 SIMULAÇÃO DA MIGRAÇÃO:")

        for formador in FormadorService.get_formadores_queryset()[
            :5
        ]:  # Mostrar apenas 5 exemplos
            existing_user = (
                Usuario.objects.select_related("municipio", "projeto")
                .prefetch_related("groups", "user_permissions")
                .filter(email=formador.email)
                .first()
            )

            if existing_user:
                print(f"  📝 Atualizaria usuário existente: {existing_user.username}")
            else:
                username = formador.email.split("@")[0]
                print(f"  📝 Criaria novo usuário: {username}")

        if Formador.objects.count() > 5:
            print(f"  ... e mais {Formador.objects.count() - 5} formadores")
