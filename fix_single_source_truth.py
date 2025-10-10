#!/usr/bin/env python3
"""
🔧 CORREÇÃO SINGLE SOURCE OF TRUTH - SISTEMA APRENDER
====================================================

Script para corrigir todas as inconsistências de Single Source of Truth
substituindo queries diretas por services centralizados.

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SingleSourceTruthFixer:
    """
    Corretor de Single Source of Truth
    """

    def __init__(self):
        self.fixes_applied = []
        self.errors = []

        # Mapeamento de correções
        self.fix_mappings = {
            # Formadores
            "Formador.objects.filter(ativo=True)": "FormadorService.get_formadores_queryset()",
            "Formador.objects.filter(ativo=True).order_by": "FormadorService.get_formadores_queryset().order_by",
            "Formador.objects.get(id=admin_formador_id, ativo=True)": "FormadorService.get_formadores_queryset().get(id=admin_formador_id)",
            "Formador.objects.get(email=user.email, ativo=True)": "FormadorService.get_formadores_queryset().get(email=user.email)",
            "Formador.objects.filter(ativo=True).count()": "FormadorService.get_formadores_queryset().count()",
            # Municípios
            "Municipio.objects.filter(ativo=True)": "MunicipioService.ativos()",
            "Municipio.objects.filter(id=municipio_id).first()": "MunicipioService.ativos().filter(id=municipio_id).first()",
            "Municipio.objects.filter(nome__iexact=municipio_nome_param)": "MunicipioService.ativos().filter(nome__iexact=municipio_nome_param)",
            "Municipio.objects.get(id=municipio_id)": "MunicipioService.ativos().get(id=municipio_id)",
            "Municipio.objects.all()": "MunicipioService.ativos()",
            "Municipio.objects.values_list": "MunicipioService.ativos().values_list",
            "Municipio.objects.filter(ativo=False).count()": "MunicipioService.inativos().count()",
            # Projetos
            "Projeto.objects.filter(ativo=True)": "ProjetoService.ativos()",
            "Projeto.objects.filter(ativo=True).order_by": "ProjetoService.ativos().order_by",
            "Projeto.objects.get(id=projeto_id)": "ProjetoService.ativos().get(id=projeto_id)",
            "Projeto.objects.count()": "ProjetoService.ativos().count()",
            # Tipos de Evento
            "TipoEvento.objects.filter(ativo=True)": "TipoEventoService.ativos()",
            "TipoEvento.objects.count()": "TipoEventoService.ativos().count()",
            "TipoEvento.objects.all()": "TipoEventoService.ativos()",
            # Setores
            "Setor.objects.all()": "SetorService.ativos()",
            # Usuários
            "Usuario.objects.filter(cargo='coordenador')": "UsuarioService.por_cargo('coordenador')",
            "Usuario.objects.filter(formador_ativo=True)": "FormadorService.get_formadores_queryset()",
            "Usuario.objects.filter(formador_ativo=False)": "UsuarioService.get_optimized_queryset().filter(formador_ativo=False)",
            "Usuario.objects.filter(is_active=True).count()": "UsuarioService.ativos().count()",
        }

    def fix_all_files(self):
        """Aplica correções em todos os arquivos"""
        print("🔧 CORREÇÃO SINGLE SOURCE OF TRUTH")
        print("=" * 50)

        # Arquivos para corrigir
        files_to_fix = [
            "core/views/base.py",
            "core/views/controle_pre_agenda_views.py",
            "core/views/controle_views.py",
            "core/views/coordenador_views.py",
            "core/views/deslocamento_views.py",
            "core/views/diretoria_views.py",
            "core/views/formador_views.py",
            "core/views/gestao_views.py",
            "core/views/health_views.py",
            "core/views/mapa_realtime_views.py",
        ]

        for file_path in files_to_fix:
            self.fix_file(file_path)

        self.print_fix_report()

    def fix_file(self, file_path: str):
        """Corrige um arquivo específico"""
        print(f"\n📁 Corrigindo: {file_path}")
        print("-" * 40)

        try:
            path = Path(file_path)
            if not path.exists():
                self.errors.append(f"Arquivo {file_path} não encontrado")
                print(f"  ❌ Arquivo não encontrado")
                return

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            fixes_in_file = 0

            # Aplicar correções
            for old_pattern, new_pattern in self.fix_mappings.items():
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    fixes_in_file += 1
                    self.fixes_applied.append(
                        f"{file_path}: {old_pattern} → {new_pattern}"
                    )
                    print(f"  ✅ {old_pattern} → {new_pattern}")

            # Adicionar imports necessários se houver mudanças
            if content != original_content:
                content = self.add_necessary_imports(content, file_path)

                # Salvar arquivo corrigido
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"  📝 {fixes_in_file} correções aplicadas")
            else:
                print(f"  ℹ️ Nenhuma correção necessária")

        except Exception as e:
            self.errors.append(f"Erro ao corrigir {file_path}: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def add_necessary_imports(self, content: str, file_path: str) -> str:
        """Adiciona imports necessários para services"""

        # Verificar se já tem imports de services
        if "from core.services import" in content:
            return content

        # Verificar quais services são necessários
        needed_services = []
        if "FormadorService" in content:
            needed_services.append("FormadorService")
        if "MunicipioService" in content:
            needed_services.append("MunicipioService")
        if "ProjetoService" in content:
            needed_services.append("ProjetoService")
        if "TipoEventoService" in content:
            needed_services.append("TipoEventoService")
        if "SetorService" in content:
            needed_services.append("SetorService")
        if "UsuarioService" in content:
            needed_services.append("UsuarioService")

        if not needed_services:
            return content

        # Adicionar imports
        import_line = f"from core.services import {', '.join(needed_services)}\n"

        # Encontrar onde adicionar o import
        lines = content.split("\n")
        insert_index = 0

        # Procurar por outros imports
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                insert_index = i + 1

        # Inserir import
        lines.insert(insert_index, import_line)

        return "\n".join(lines)

    def print_fix_report(self):
        """Imprime relatório de correções"""
        print("\n📊 RELATÓRIO DE CORREÇÕES")
        print("=" * 50)

        print(f"\n✅ CORREÇÕES APLICADAS ({len(self.fixes_applied)}):")
        for fix in self.fixes_applied:
            print(f"  • {fix}")

        if self.errors:
            print(f"\n❌ ERROS ENCONTRADOS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        else:
            print(f"\n✅ NENHUM ERRO ENCONTRADO")

        print(f"\n🎯 CONCLUSÃO:")
        if not self.errors:
            print("✅ Single Source of Truth corrigido com sucesso")
        else:
            print("❌ Algumas correções falharam - verifique os erros")


def main():
    """Função principal"""
    try:
        fixer = SingleSourceTruthFixer()
        fixer.fix_all_files()

    except Exception as e:
        logger.error(f"❌ Erro nas correções: {str(e)}")
        raise


if __name__ == "__main__":
    main()
