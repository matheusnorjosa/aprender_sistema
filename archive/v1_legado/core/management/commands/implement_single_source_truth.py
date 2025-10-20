#!/usr/bin/env python3
"""
🔧 IMPLEMENTAÇÃO SINGLE SOURCE OF TRUTH
=======================================

Script para substituir todas as queries diretas por services centralizados.
Garante consistência e elimina duplicação de código.

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import re
import sys
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
import django

django.setup()

from django.core.management.base import BaseCommand

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SingleSourceOfTruthImplementer:
    """
    Implementador de Single Source of Truth
    """

    def __init__(self):
        self.replacements = {
            # Formador queries
            'FormadorService.get_formadores_queryset()': 'FormadorService.get_formadores_queryset()',
            'FormadorService.get_formadores_queryset()': 'FormadorService.get_formadores_queryset()',
            'FormadorService.get_formador(': 'FormadorService.get_formador(',
            'FormadorService.filter_formadores(': 'FormadorService.filter_formadores(',

            # Usuario queries
            "UsuarioService.por_cargo("coordenador")": 'UsuarioService.por_cargo("coordenador")',
            "UsuarioService.por_cargo("gerente")": 'UsuarioService.por_cargo("gerente")',
            "UsuarioService.por_cargo("formador")": 'UsuarioService.por_cargo("formador")',
            'UsuarioService.ativos()': 'UsuarioService.ativos()',

            # Projeto queries
            'ProjetoService.ativos()': 'ProjetoService.ativos()',
            'ProjetoService.todos()': 'ProjetoService.todos()',

            # Municipio queries
            'MunicipioService.ativos()': 'MunicipioService.ativos()',
            'MunicipioService.todos()': 'MunicipioService.todos()',
        }

        self.files_processed = 0
        self.replacements_made = 0
        self.errors = []

    def implement_single_source_truth(self, dry_run=True):
        """Implementa Single Source of Truth em todo o projeto"""

        print("🔧 IMPLEMENTAÇÃO SINGLE SOURCE OF TRUTH")
        print("=" * 50)

        if dry_run:
            print("🔍 MODO DRY RUN - Nenhuma alteração será feita")

        # 1. Atualizar imports
        self.update_imports(dry_run)

        # 2. Substituir queries diretas
        self.replace_direct_queries(dry_run)

        # 3. Criar services faltantes
        self.create_missing_services(dry_run)

        self.print_summary()

    def update_imports(self, dry_run=False):
        """Atualiza imports para incluir services"""
        print("\n🔄 ATUALIZANDO IMPORTS...")

        core_views_dir = Path("core/views")
        if not core_views_dir.exists():
            print("  ⚠️ Diretório core/views não encontrado")
            return

        for py_file in core_views_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            self.update_file_imports(py_file, dry_run)

    def update_file_imports(self, file_path, dry_run=False):
        """Atualiza imports de um arquivo específico"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Verificar se já tem import de services
            if 'from core.services import' not in content:
                # Adicionar import de services
                import_line = "from core.services import FormadorService, UsuarioService, ProjetoService, MunicipioService\n"

                # Encontrar onde inserir o import
                lines = content.split('\n')
                insert_index = 0

                for i, line in enumerate(lines):
                    if line.startswith('from ') or line.startswith('import '):
                        insert_index = i + 1
                    elif line.strip() == '':
                        continue
                    else:
                        break

                lines.insert(insert_index, import_line)
                content = '\n'.join(lines)

            if content != original_content and not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ Imports atualizados: {file_path}")
                self.files_processed += 1
            elif content != original_content:
                print(f"  📝 Imports seriam atualizados: {file_path}")

        except Exception as e:
            error_msg = f"Erro ao processar {file_path}: {str(e)}"
            self.errors.append(error_msg)
            print(f"  ❌ {error_msg}")

    def replace_direct_queries(self, dry_run=False):
        """Substitui queries diretas por services"""
        print("\n🔄 SUBSTITUINDO QUERIES DIRETAS...")

        core_dir = Path("core")
        if not core_dir.exists():
            print("  ⚠️ Diretório core não encontrado")
            return

        for py_file in core_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            self.replace_queries_in_file(py_file, dry_run)

    def replace_queries_in_file(self, file_path, dry_run=False):
        """Substitui queries diretas em um arquivo específico"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            replacements_in_file = 0

            # Aplicar substituições
            for old_query, new_service in self.replacements.items():
                if old_query in content:
                    content = content.replace(old_query, new_service)
                    replacements_in_file += 1

            if content != original_content and not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ {replacements_in_file} substituições em: {file_path}")
                self.files_processed += 1
                self.replacements_made += replacements_in_file
            elif content != original_content:
                print(f"  📝 {replacements_in_file} substituições seriam feitas em: {file_path}")

        except Exception as e:
            error_msg = f"Erro ao processar {file_path}: {str(e)}"
            self.errors.append(error_msg)
            print(f"  ❌ {error_msg}")

    def create_missing_services(self, dry_run=False):
        """Cria services que estão faltando"""
        print("\n🔄 CRIANDO SERVICES FALTANTES...")

        services_file = Path("core/services/data_services.py")

        # Verificar se ProjetoService e MunicipioService existem
        if services_file.exists():
            with open(services_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'class ProjetoService' not in content:
                self.add_projeto_service(services_file, dry_run)

            if 'class MunicipioService' not in content:
                self.add_municipio_service(services_file, dry_run)

    def add_projeto_service(self, services_file, dry_run=False):
        """Adiciona ProjetoService ao arquivo de services"""
        projeto_service = '''

class ProjetoService(BaseService):
    """
    Service para Projetos - Queries otimizadas
    """

    @classmethod
    def ativos(cls):
        """Projetos ativos otimizados"""
        from core.models import Projeto
        return ProjetoService.ativos().order_by('nome')

    @classmethod
    def todos(cls):
        """Todos os projetos"""
        from core.models import Projeto
        return ProjetoService.todos().order_by('nome')

    @classmethod
    def por_setor(cls, setor):
        """Projetos por setor"""
        return cls.ativos().filter(setor=setor)

    @classmethod
    def superintendencia(cls):
        """Projetos da superintendência"""
        return cls.ativos().filter(setor__vinculado_superintendencia=True)
'''

        if not dry_run:
            with open(services_file, 'a', encoding='utf-8') as f:
                f.write(projeto_service)
            print("  ✅ ProjetoService adicionado")
        else:
            print("  📝 ProjetoService seria adicionado")

    def add_municipio_service(self, services_file, dry_run=False):
        """Adiciona MunicipioService ao arquivo de services"""
        municipio_service = '''

class MunicipioService(BaseService):
    """
    Service para Municípios - Queries otimizadas
    """

    @classmethod
    def ativos(cls):
        """Municípios ativos otimizados"""
        from core.models import Municipio
        return MunicipioService.ativos().order_by('nome', 'uf')

    @classmethod
    def todos(cls):
        """Todos os municípios"""
        from core.models import Municipio
        return MunicipioService.todos().order_by('nome', 'uf')

    @classmethod
    def por_uf(cls, uf):
        """Municípios por UF"""
        return cls.ativos().filter(uf=uf)

    @classmethod
    def com_eventos(cls):
        """Municípios que têm eventos"""
        return cls.ativos().filter(solicitacao__isnull=False).distinct()
'''

        if not dry_run:
            with open(services_file, 'a', encoding='utf-8') as f:
                f.write(municipio_service)
            print("  ✅ MunicipioService adicionado")
        else:
            print("  📝 MunicipioService seria adicionado")

    def print_summary(self):
        """Imprime resumo da implementação"""
        print("\n📊 RESUMO DA IMPLEMENTAÇÃO:")
        print(f"  Arquivos processados: {self.files_processed}")
        print(f"  Substituições feitas: {self.replacements_made}")
        print(f"  Erros encontrados: {len(self.errors)}")

        if self.errors:
            print("\n❌ ERROS ENCONTRADOS:")
            for error in self.errors:
                print(f"  - {error}")


class Command(BaseCommand):
    help = 'Implementa Single Source of Truth substituindo queries diretas por services'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa em modo dry-run sem fazer alterações',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a implementação mesmo com warnings',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        implementer = SingleSourceOfTruthImplementer()
        implementer.implement_single_source_truth(dry_run=dry_run)
