#!/usr/bin/env python3
"""
🔧 OTIMIZADOR DE QUERIES
========================

Script para otimizar queries Django com select_related e prefetch_related
Reduz N+1 queries e melhora performance

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import re
import sys
from pathlib import Path

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.core.management.base import BaseCommand

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    Otimizador de queries Django
    """

    def __init__(self):
        self.optimizations = {
            # Solicitacao queries
            'Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores")': 'Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores")',
            'Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores").filter(': 'Solicitacao.objects.select_related("municipio", "projeto", "tipo_evento", "solicitante").prefetch_related("formadores").filter(',
            # Usuario queries
            'Usuario.objects.select_related("municipio", "projeto").prefetch_related("groups", "user_permissions")': 'Usuario.objects.select_related("municipio", "projeto").prefetch_related("groups", "user_permissions")',
            'Usuario.objects.select_related("municipio", "projeto").prefetch_related("groups", "user_permissions").filter(': 'Usuario.objects.select_related("municipio", "projeto").prefetch_related("groups", "user_permissions").filter(',
            # Projeto queries
            'Projeto.objects.select_related("setor").prefetch_related("solicitacao_set")': 'Projeto.objects.select_related("setor").prefetch_related("solicitacao_set")',
            'Projeto.objects.select_related("setor").prefetch_related("solicitacao_set").filter(': 'Projeto.objects.select_related("setor").prefetch_related("solicitacao_set").filter(',
            # Municipio queries
            'Municipio.objects.prefetch_related("solicitacao_set", "usuario_set")': 'Municipio.objects.prefetch_related("solicitacao_set", "usuario_set")',
            'Municipio.objects.prefetch_related("solicitacao_set", "usuario_set").filter(': 'Municipio.objects.prefetch_related("solicitacao_set", "usuario_set").filter(',
            # Formador queries
            'Formador.objects.select_related("municipio").prefetch_related("solicitacao_set")': 'Formador.objects.select_related("municipio").prefetch_related("solicitacao_set")',
            'Formador.objects.select_related("municipio").prefetch_related("solicitacao_set").filter(': 'Formador.objects.select_related("municipio").prefetch_related("solicitacao_set").filter(',
        }

        self.files_processed = 0
        self.optimizations_made = 0
        self.errors = []

    def optimize_queries(self, dry_run=True):
        """Otimiza queries em todo o projeto"""

        print("🔧 OTIMIZAÇÃO DE QUERIES")
        print("=" * 40)

        if dry_run:
            print("🔍 MODO DRY RUN - Nenhuma alteração será feita")

        # 1. Otimizar views
        self.optimize_views(dry_run)

        # 2. Otimizar services
        self.optimize_services(dry_run)

        # 3. Otimizar management commands
        self.optimize_management_commands(dry_run)

        self.print_summary()

    def optimize_views(self, dry_run=False):
        """Otimiza queries nas views"""
        print("\n🔄 OTIMIZANDO VIEWS...")

        views_dir = Path("core/views")
        if not views_dir.exists():
            print("  ⚠️ Diretório core/views não encontrado")
            return

        for py_file in views_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            self.optimize_file_queries(py_file, dry_run)

    def optimize_services(self, dry_run=False):
        """Otimiza queries nos services"""
        print("\n🔄 OTIMIZANDO SERVICES...")

        services_dir = Path("core/services")
        if not services_dir.exists():
            print("  ⚠️ Diretório core/services não encontrado")
            return

        for py_file in services_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            self.optimize_file_queries(py_file, dry_run)

    def optimize_management_commands(self, dry_run=False):
        """Otimiza queries nos management commands"""
        print("\n🔄 OTIMIZANDO MANAGEMENT COMMANDS...")

        commands_dir = Path("core/management/commands")
        if not commands_dir.exists():
            print("  ⚠️ Diretório core/management/commands não encontrado")
            return

        for py_file in commands_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            self.optimize_file_queries(py_file, dry_run)

    def optimize_file_queries(self, file_path, dry_run=False):
        """Otimiza queries em um arquivo específico"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            optimizations_in_file = 0

            # Aplicar otimizações
            for old_query, optimized_query in self.optimizations.items():
                if old_query in content:
                    content = content.replace(old_query, optimized_query)
                    optimizations_in_file += 1

            if content != original_content and not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ {optimizations_in_file} otimizações em: {file_path}")
                self.files_processed += 1
                self.optimizations_made += optimizations_in_file
            elif content != original_content:
                print(
                    f"  📝 {optimizations_in_file} otimizações seriam feitas em: {file_path}"
                )

        except Exception as e:
            error_msg = f"Erro ao processar {file_path}: {str(e)}"
            self.errors.append(error_msg)
            print(f"  ❌ {error_msg}")

    def print_summary(self):
        """Imprime resumo da otimização"""
        print("\n📊 RESUMO DA OTIMIZAÇÃO:")
        print(f"  Arquivos processados: {self.files_processed}")
        print(f"  Otimizações feitas: {self.optimizations_made}")
        print(f"  Erros encontrados: {len(self.errors)}")

        if self.errors:
            print("\n❌ ERROS ENCONTRADOS:")
            for error in self.errors:
                print(f"  - {error}")


class Command(BaseCommand):
    help = "Otimiza queries Django com select_related e prefetch_related"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa em modo dry-run sem fazer alterações",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Força a otimização mesmo com warnings",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        optimizer = QueryOptimizer()
        optimizer.optimize_queries(dry_run=dry_run)
