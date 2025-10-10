#!/usr/bin/env python3
"""
🔧 CORREÇÃO DE MAPEAMENTO DE ENTIDADES - SISTEMA APRENDER
=======================================================

Script para corrigir e mapear corretamente todas as entidades
no banco de dados, garantindo fonte única para todas as páginas.

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import sys

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.db import transaction

from core.models import Municipio, Projeto, Setor, TipoEvento, Usuario

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EntityMappingFixer:
    """
    Corretor de mapeamento de entidades
    """

    def __init__(self):
        self.fixes_applied = []
        self.errors = []
        self.stats = {
            "usuarios_updated": 0,
            "coordenadores_created": 0,
            "formadores_created": 0,
            "setores_fixed": 0,
            "municipios_fixed": 0,
            "projetos_fixed": 0,
        }

    def fix_all_entities(self):
        """Corrige mapeamento de todas as entidades"""
        print("🔧 CORREÇÃO DE MAPEAMENTO DE ENTIDADES")
        print("=" * 50)

        # 1. Corrigir setores
        self.fix_setores()

        # 2. Corrigir municípios
        self.fix_municipios()

        # 3. Corrigir projetos
        self.fix_projetos()

        # 4. Mapear coordenadores
        self.map_coordenadores()

        # 5. Mapear formadores
        self.map_formadores()

        # 6. Corrigir usuários
        self.fix_usuarios()

        # Relatório final
        self.print_fix_report()

    def fix_setores(self):
        """Corrige setores"""
        print("\n🏢 CORRIGINDO SETORES")
        print("-" * 30)

        try:
            # Corrigir setor vazio
            setor_vazio = Setor.objects.filter(nome="-").first()
            if setor_vazio:
                setor_vazio.nome = "Não Definido"
                setor_vazio.sigla = "ND"
                setor_vazio.save()
                self.stats["setores_fixed"] += 1
                print("  ✅ Setor vazio corrigido para 'Não Definido'")

            # Verificar se todos os setores têm sigla válida
            for setor in Setor.objects.all():
                if not setor.sigla or setor.sigla == "-":
                    setor.sigla = setor.nome[:10].upper()
                    setor.save()
                    self.stats["setores_fixed"] += 1
                    print(f"  ✅ Sigla corrigida para setor: {setor.nome}")

            print(f"  📊 Total de setores corrigidos: {self.stats['setores_fixed']}")

        except Exception as e:
            self.errors.append(f"Erro ao corrigir setores: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def fix_municipios(self):
        """Corrige municípios"""
        print("\n🏘️ CORRIGINDO MUNICÍPIOS")
        print("-" * 30)

        try:
            # Verificar se todos os municípios têm UF
            municipios_sem_uf = Municipio.objects.filter(uf__isnull=True)
            for municipio in municipios_sem_uf:
                municipio.uf = "CE"  # Default para Ceará
                municipio.save()
                self.stats["municipios_fixed"] += 1
                print(f"  ✅ UF adicionada para município: {municipio.nome}")

            print(
                f"  📊 Total de municípios corrigidos: {self.stats['municipios_fixed']}"
            )

        except Exception as e:
            self.errors.append(f"Erro ao corrigir municípios: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def fix_projetos(self):
        """Corrige projetos"""
        print("\n📋 CORRIGINDO PROJETOS")
        print("-" * 30)

        try:
            # Verificar se todos os projetos têm setor
            projetos_sem_setor = Projeto.objects.filter(setor__isnull=True)
            setor_outros = Setor.objects.filter(nome="Outros").first()

            for projeto in projetos_sem_setor:
                if setor_outros:
                    projeto.setor = setor_outros
                    projeto.save()
                    self.stats["projetos_fixed"] += 1
                    print(f"  ✅ Setor 'Outros' atribuído ao projeto: {projeto.nome}")

            print(f"  📊 Total de projetos corrigidos: {self.stats['projetos_fixed']}")

        except Exception as e:
            self.errors.append(f"Erro ao corrigir projetos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def map_coordenadores(self):
        """Mapeia coordenadores baseado nos dados das planilhas"""
        print("\n👥 MAPEANDO COORDENADORES")
        print("-" * 30)

        try:
            # Baseado nos dados das planilhas, identificar coordenadores
            # Usuários da Superintendência que podem ser coordenadores
            usuarios_superintendencia = Usuario.objects.filter(
                setor__nome="Superintendência", is_active=True
            )

            # Mapear alguns usuários como coordenadores (baseado nos dados originais)
            coordenadores_candidatos = [
                "Alison Mendonça De Almeida",
                "Amanda Sales Rodrigues Melo",
                "Mikaelly Correia Araripe Cavalcante",
            ]

            for usuario in usuarios_superintendencia:
                if usuario.get_full_name() in coordenadores_candidatos:
                    usuario.cargo = "coordenador"
                    usuario.save()
                    self.stats["coordenadores_created"] += 1
                    print(f"  ✅ Coordenador mapeado: {usuario.get_full_name()}")

            print(
                f"  📊 Total de coordenadores mapeados: {self.stats['coordenadores_created']}"
            )

        except Exception as e:
            self.errors.append(f"Erro ao mapear coordenadores: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def map_formadores(self):
        """Mapeia formadores baseado nos dados das planilhas"""
        print("\n👨‍🏫 MAPEANDO FORMADORES")
        print("-" * 30)

        try:
            # Baseado nos dados das planilhas, identificar formadores
            formadores_candidatos = [
                "Alison Mendonça De Almeida",
                "Amanda Arruda Da Costa Rodrigues",
                "Bruno Pereira Dos Santos",
            ]

            for usuario in Usuario.objects.filter(is_active=True):
                if usuario.get_full_name() in formadores_candidatos:
                    usuario.cargo = "formador"
                    usuario.formador_ativo = True
                    usuario.save()
                    self.stats["formadores_created"] += 1
                    print(f"  ✅ Formador mapeado: {usuario.get_full_name()}")

            print(
                f"  📊 Total de formadores mapeados: {self.stats['formadores_created']}"
            )

        except Exception as e:
            self.errors.append(f"Erro ao mapear formadores: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def fix_usuarios(self):
        """Corrige usuários"""
        print("\n👤 CORRIGINDO USUÁRIOS")
        print("-" * 30)

        try:
            # Corrigir usuários sem setor
            usuarios_sem_setor = Usuario.objects.filter(setor__isnull=True)
            setor_outros = Setor.objects.filter(nome="Outros").first()

            for usuario in usuarios_sem_setor:
                if setor_outros:
                    usuario.setor = setor_outros
                    usuario.save()
                    self.stats["usuarios_updated"] += 1
                    print(
                        f"  ✅ Setor 'Outros' atribuído ao usuário: {usuario.get_full_name()}"
                    )

            # Corrigir usuários sem cargo
            usuarios_sem_cargo = Usuario.objects.filter(cargo="")
            for usuario in usuarios_sem_cargo:
                if usuario.cargo == "":
                    usuario.cargo = "outros"
                    usuario.save()
                    self.stats["usuarios_updated"] += 1
                    print(
                        f"  ✅ Cargo 'outros' atribuído ao usuário: {usuario.get_full_name()}"
                    )

            print(
                f"  📊 Total de usuários corrigidos: {self.stats['usuarios_updated']}"
            )

        except Exception as e:
            self.errors.append(f"Erro ao corrigir usuários: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def print_fix_report(self):
        """Imprime relatório de correções"""
        print("\n📊 RELATÓRIO DE CORREÇÕES")
        print("=" * 50)

        print(f"\n✅ CORREÇÕES APLICADAS:")
        print(f"  • Setores corrigidos: {self.stats['setores_fixed']}")
        print(f"  • Municípios corrigidos: {self.stats['municipios_fixed']}")
        print(f"  • Projetos corrigidos: {self.stats['projetos_fixed']}")
        print(f"  • Coordenadores mapeados: {self.stats['coordenadores_created']}")
        print(f"  • Formadores mapeados: {self.stats['formadores_created']}")
        print(f"  • Usuários corrigidos: {self.stats['usuarios_updated']}")

        if self.errors:
            print(f"\n❌ ERROS ENCONTRADOS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        else:
            print(f"\n✅ NENHUM ERRO ENCONTRADO")

        print(f"\n🎯 CONCLUSÃO:")
        if not self.errors:
            print("✅ Mapeamento de entidades corrigido com sucesso")
        else:
            print("❌ Algumas correções falharam - verifique os erros")


def main():
    """Função principal"""
    try:
        fixer = EntityMappingFixer()
        fixer.fix_all_entities()

    except Exception as e:
        logger.error(f"❌ Erro nas correções: {str(e)}")
        raise


if __name__ == "__main__":
    main()
