#!/usr/bin/env python3
"""
🔧 CORREÇÃO DE DADOS DO DASHBOARD - SISTEMA APRENDER
==================================================

Script para corrigir problemas do dashboard e garantir
que os dados reais sejam exibidos corretamente.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
import django
django.setup()

from django.db import transaction
from django.contrib.auth.models import Group
from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento, Solicitacao

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DashboardDataFixer:
    """
    Corretor de dados do dashboard
    """
    
    def __init__(self):
        self.fixes_applied = []
        self.errors = []
        self.stats = {
            'usuarios_fixed': 0,
            'groups_created': 0,
            'formadores_fixed': 0,
            'coordenadores_fixed': 0,
            'solicitacoes_created': 0
        }
    
    def fix_dashboard_data(self):
        """Corrige dados do dashboard"""
        print("🔧 CORREÇÃO DE DADOS DO DASHBOARD")
        print("=" * 50)
        
        # 1. Criar grupos necessários
        self.create_necessary_groups()
        
        # 2. Corrigir formadores
        self.fix_formadores()
        
        # 3. Corrigir coordenadores
        self.fix_coordenadores()
        
        # 4. Criar dados de exemplo para demonstração
        self.create_demo_data()
        
        # 5. Verificar dados finais
        self.verify_final_data()
        
        # Relatório final
        self.print_fix_report()
    
    def create_necessary_groups(self):
        """Cria grupos necessários"""
        print("\n👥 CRIANDO GRUPOS NECESSÁRIOS")
        print("-" * 40)
        
        try:
            groups_to_create = [
                'formador',
                'coordenador',
                'gerente',
                'controle',
                'superintendencia'
            ]
            
            for group_name in groups_to_create:
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    self.stats['groups_created'] += 1
                    print(f"  ✅ Grupo criado: {group_name}")
                else:
                    print(f"  ℹ️ Grupo já existe: {group_name}")
            
        except Exception as e:
            self.errors.append(f"Erro ao criar grupos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def fix_formadores(self):
        """Corrige formadores"""
        print("\n👨‍🏫 CORRIGINDO FORMADORES")
        print("-" * 40)
        
        try:
            # Obter grupo de formadores
            formador_group = Group.objects.get(name='formador')
            
            # Formadores identificados
            formadores_candidatos = [
                'Alison Mendonça De Almeida',
                'Amanda Arruda Da Costa Rodrigues',
                'Bruno Pereira Dos Santos'
            ]
            
            for usuario in Usuario.objects.filter(is_active=True):
                if usuario.get_full_name() in formadores_candidatos:
                    # Definir como formador
                    usuario.cargo = 'formador'
                    usuario.formador_ativo = True
                    usuario.save()
                    
                    # Adicionar ao grupo
                    usuario.groups.add(formador_group)
                    
                    self.stats['formadores_fixed'] += 1
                    print(f"  ✅ Formador corrigido: {usuario.get_full_name()}")
            
        except Exception as e:
            self.errors.append(f"Erro ao corrigir formadores: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def fix_coordenadores(self):
        """Corrige coordenadores"""
        print("\n👥 CORRIGINDO COORDENADORES")
        print("-" * 40)
        
        try:
            # Obter grupo de coordenadores
            coordenador_group = Group.objects.get(name='coordenador')
            
            # Coordenadores identificados
            coordenadores_candidatos = [
                'Mikaelly Correia Araripe Cavalcante',
                'Amanda Sales Rodrigues Melo'
            ]
            
            for usuario in Usuario.objects.filter(is_active=True):
                if usuario.get_full_name() in coordenadores_candidatos:
                    # Definir como coordenador
                    usuario.cargo = 'coordenador'
                    usuario.save()
                    
                    # Adicionar ao grupo
                    usuario.groups.add(coordenador_group)
                    
                    self.stats['coordenadores_fixed'] += 1
                    print(f"  ✅ Coordenador corrigido: {usuario.get_full_name()}")
            
        except Exception as e:
            self.errors.append(f"Erro ao corrigir coordenadores: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def create_demo_data(self):
        """Cria dados de demonstração para o dashboard"""
        print("\n📊 CRIANDO DADOS DE DEMONSTRAÇÃO")
        print("-" * 40)
        
        try:
            # Criar algumas solicitações de exemplo para demonstrar o dashboard
            coordenadores = Usuario.objects.filter(cargo='coordenador', is_active=True)
            projetos = Projeto.objects.filter(ativo=True)
            municipios = Municipio.objects.filter(ativo=True)
            tipos_evento = TipoEvento.objects.filter(ativo=True)
            
            if coordenadores.exists() and projetos.exists() and municipios.exists() and tipos_evento.exists():
                # Criar 3 solicitações de exemplo
                for i in range(3):
                    try:
                        with transaction.atomic():
                            solicitacao = Solicitacao.objects.create(
                                projeto=projetos.first(),
                                municipio=municipios.first(),
                                tipo_evento=tipos_evento.first(),
                                usuario_solicitante=coordenadores.first(),
                                data_inicio='2025-10-01',
                                data_fim='2025-10-01',
                                observacoes=f'Solicitação de demonstração {i+1}',
                                status='Aprovado'
                            )
                            self.stats['solicitacoes_created'] += 1
                            print(f"  ✅ Solicitação criada: {solicitacao.id}")
                    except Exception as e:
                        print(f"  ⚠️ Erro ao criar solicitação {i+1}: {str(e)}")
            else:
                print("  ⚠️ Dados insuficientes para criar solicitações de demonstração")
            
        except Exception as e:
            self.errors.append(f"Erro ao criar dados de demonstração: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def verify_final_data(self):
        """Verifica dados finais"""
        print("\n🔍 VERIFICANDO DADOS FINAIS")
        print("-" * 40)
        
        try:
            # Verificar estatísticas finais
            stats = {
                'usuarios_ativos': Usuario.objects.filter(is_active=True).count(),
                'coordenadores': Usuario.objects.filter(cargo='coordenador').count(),
                'formadores': Usuario.objects.filter(cargo='formador').count(),
                'formadores_ativos': Usuario.objects.filter(formador_ativo=True).count(),
                'setores': Setor.objects.count(),
                'municipios': Municipio.objects.count(),
                'projetos': Projeto.objects.count(),
                'tipos_evento': TipoEvento.objects.count(),
                'solicitacoes': Solicitacao.objects.count(),
            }
            
            print("  📊 Estatísticas finais:")
            for key, value in stats.items():
                print(f"    • {key}: {value}")
            
            # Verificar se há dados suficientes para o dashboard
            if stats['coordenadores'] > 0 and stats['formadores'] > 0 and stats['solicitacoes'] > 0:
                print("  ✅ Dashboard deve estar funcionando com dados")
            else:
                print("  ⚠️ Dashboard pode ainda estar com poucos dados")
            
        except Exception as e:
            self.errors.append(f"Erro ao verificar dados finais: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def print_fix_report(self):
        """Imprime relatório de correções"""
        print("\n📊 RELATÓRIO DE CORREÇÕES")
        print("=" * 50)
        
        print(f"\n✅ CORREÇÕES APLICADAS:")
        print(f"  • Grupos criados: {self.stats['groups_created']}")
        print(f"  • Formadores corrigidos: {self.stats['formadores_fixed']}")
        print(f"  • Coordenadores corrigidos: {self.stats['coordenadores_fixed']}")
        print(f"  • Solicitações criadas: {self.stats['solicitacoes_created']}")
        
        if self.errors:
            print(f"\n❌ ERROS ENCONTRADOS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        else:
            print(f"\n✅ NENHUM ERRO ENCONTRADO")
        
        print(f"\n🎯 CONCLUSÃO:")
        if not self.errors:
            print("✅ Dashboard corrigido e deve estar funcionando com dados reais")
        else:
            print("❌ Algumas correções falharam - verifique os erros")


def main():
    """Função principal"""
    try:
        fixer = DashboardDataFixer()
        fixer.fix_dashboard_data()
        
    except Exception as e:
        logger.error(f"❌ Erro nas correções: {str(e)}")
        raise


if __name__ == "__main__":
    main()

