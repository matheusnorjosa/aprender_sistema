#!/usr/bin/env python3
"""
🔍 VERIFICAÇÃO DE DADOS DO DASHBOARD - SISTEMA APRENDER
====================================================

Script para verificar por que o dashboard está zerado
e garantir que os dados reais sejam exibidos.

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

from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento, Solicitacao
from core.services import (
    UsuarioService, FormadorService, CoordinatorService,
    DashboardService, MunicipioService, SetorService, TipoEventoService
)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DashboardDataChecker:
    """
    Verificador de dados do dashboard
    """
    
    def __init__(self):
        self.dashboard_stats = {}
        self.issues = []
    
    def check_dashboard_data(self):
        """Verifica dados do dashboard"""
        print("🔍 VERIFICAÇÃO DE DADOS DO DASHBOARD")
        print("=" * 50)
        
        # 1. Verificar dados básicos
        self.check_basic_data()
        
        # 2. Verificar services
        self.check_services()
        
        # 3. Verificar dashboard service
        self.check_dashboard_service()
        
        # 4. Verificar dados específicos do dashboard
        self.check_dashboard_specific_data()
        
        # 5. Relatório final
        self.print_dashboard_report()
    
    def check_basic_data(self):
        """Verifica dados básicos do sistema"""
        print("\n📊 VERIFICANDO DADOS BÁSICOS")
        print("-" * 40)
        
        try:
            # Contar registros básicos
            stats = {
                'usuarios_total': Usuario.objects.count(),
                'usuarios_ativos': Usuario.objects.filter(is_active=True).count(),
                'coordenadores': Usuario.objects.filter(cargo='coordenador').count(),
                'formadores': Usuario.objects.filter(cargo='formador').count(),
                'setores': Setor.objects.count(),
                'municipios': Municipio.objects.count(),
                'projetos': Projeto.objects.count(),
                'tipos_evento': TipoEvento.objects.count(),
                'solicitacoes': Solicitacao.objects.count(),
            }
            
            self.dashboard_stats.update(stats)
            
            print("  📈 Estatísticas básicas:")
            for key, value in stats.items():
                print(f"    • {key}: {value}")
            
            # Verificar se há dados suficientes
            if stats['usuarios_ativos'] == 0:
                self.issues.append("Nenhum usuário ativo encontrado")
            if stats['coordenadores'] == 0:
                self.issues.append("Nenhum coordenador encontrado")
            if stats['formadores'] == 0:
                self.issues.append("Nenhum formador encontrado")
            if stats['solicitacoes'] == 0:
                self.issues.append("Nenhuma solicitação encontrada")
            
        except Exception as e:
            self.issues.append(f"Erro ao verificar dados básicos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def check_services(self):
        """Verifica se os services estão funcionando"""
        print("\n🔧 VERIFICANDO SERVICES")
        print("-" * 40)
        
        try:
            # Testar UsuarioService
            usuarios_ativos = UsuarioService.ativos()
            print(f"  ✅ UsuarioService.ativos(): {usuarios_ativos.count()} usuários")
            
            # Testar FormadorService
            formadores = FormadorService.get_formadores_queryset()
            print(f"  ✅ FormadorService: {formadores.count()} formadores")
            
            # Testar CoordinatorService
            coordenadores = CoordinatorService.get_coordenadores_queryset()
            print(f"  ✅ CoordinatorService: {coordenadores.count()} coordenadores")
            
            # Testar MunicipioService
            municipios = MunicipioService.ativos()
            print(f"  ✅ MunicipioService: {municipios.count()} municípios")
            
            # Testar ProjetoService
            try:
                from core.services.data_master_service import ProjetoService
                projetos = ProjetoService.ativos()
                print(f"  ✅ ProjetoService: {projetos.count()} projetos")
            except ImportError:
                print("  ❌ ProjetoService não encontrado")
                self.issues.append("ProjetoService não encontrado")
            
            # Testar TipoEventoService
            tipos = TipoEventoService.ativos()
            print(f"  ✅ TipoEventoService: {tipos.count()} tipos de evento")
            
            # Testar SetorService
            setores = SetorService.ativos()
            print(f"  ✅ SetorService: {setores.count()} setores")
            
        except Exception as e:
            self.issues.append(f"Erro ao verificar services: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def check_dashboard_service(self):
        """Verifica DashboardService"""
        print("\n📊 VERIFICANDO DASHBOARD SERVICE")
        print("-" * 40)
        
        try:
            # Testar métodos do DashboardService
            dashboard_stats = DashboardService.get_dashboard_stats()
            print(f"  ✅ DashboardService.get_dashboard_stats(): {len(dashboard_stats)} estatísticas")
            
            # Verificar estatísticas específicas
            if 'total_usuarios' in dashboard_stats:
                print(f"    • Total usuários: {dashboard_stats['total_usuarios']}")
            if 'total_coordenadores' in dashboard_stats:
                print(f"    • Total coordenadores: {dashboard_stats['total_coordenadores']}")
            if 'total_formadores' in dashboard_stats:
                print(f"    • Total formadores: {dashboard_stats['total_formadores']}")
            if 'total_municipios' in dashboard_stats:
                print(f"    • Total municípios: {dashboard_stats['total_municipios']}")
            if 'total_projetos' in dashboard_stats:
                print(f"    • Total projetos: {dashboard_stats['total_projetos']}")
            
            self.dashboard_stats['dashboard_service'] = dashboard_stats
            
        except Exception as e:
            self.issues.append(f"Erro ao verificar DashboardService: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def check_dashboard_specific_data(self):
        """Verifica dados específicos do dashboard"""
        print("\n📈 VERIFICANDO DADOS ESPECÍFICOS DO DASHBOARD")
        print("-" * 40)
        
        try:
            # Verificar dados de coordenadores por município
            coordenadores_por_municipio = DashboardService.get_coordenadores_por_municipio()
            print(f"  📊 Coordenadores por município: {len(coordenadores_por_municipio)} registros")
            
            # Verificar dados de formadores por área
            formadores_por_area = DashboardService.get_formadores_por_area()
            print(f"  📊 Formadores por área: {len(formadores_por_area)} registros")
            
            # Verificar dados de projetos por setor
            projetos_por_setor = DashboardService.get_projetos_por_setor()
            print(f"  📊 Projetos por setor: {len(projetos_por_setor)} registros")
            
            # Verificar dados de solicitações por status
            solicitacoes_por_status = DashboardService.get_solicitacoes_por_status()
            print(f"  📊 Solicitações por status: {len(solicitacoes_por_status)} registros")
            
            # Verificar dados de eventos por tipo
            eventos_por_tipo = DashboardService.get_eventos_por_tipo()
            print(f"  📊 Eventos por tipo: {len(eventos_por_tipo)} registros")
            
            self.dashboard_stats.update({
                'coordenadores_por_municipio': len(coordenadores_por_municipio),
                'formadores_por_area': len(formadores_por_area),
                'projetos_por_setor': len(projetos_por_setor),
                'solicitacoes_por_status': len(solicitacoes_por_status),
                'eventos_por_tipo': len(eventos_por_tipo),
            })
            
        except Exception as e:
            self.issues.append(f"Erro ao verificar dados específicos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")
    
    def print_dashboard_report(self):
        """Imprime relatório do dashboard"""
        print("\n📊 RELATÓRIO DO DASHBOARD")
        print("=" * 50)
        
        # Estatísticas gerais
        print(f"\n📈 ESTATÍSTICAS GERAIS:")
        for key, value in self.dashboard_stats.items():
            if isinstance(value, dict):
                print(f"  📊 {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    • {sub_key}: {sub_value}")
            else:
                print(f"  • {key}: {value}")
        
        # Problemas encontrados
        if self.issues:
            print(f"\n❌ PROBLEMAS ENCONTRADOS ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  • {issue}")
        else:
            print(f"\n✅ NENHUM PROBLEMA ENCONTRADO")
        
        # Conclusão
        print(f"\n🎯 CONCLUSÃO:")
        if not self.issues:
            print("✅ Dashboard deve estar funcionando corretamente")
        else:
            print("❌ Dashboard pode estar zerado devido aos problemas encontrados")
            print("\n🔧 RECOMENDAÇÕES:")
            print("  1. Verificar se os dados estão sendo carregados corretamente")
            print("  2. Verificar se os services estão retornando dados")
            print("  3. Verificar se as views estão usando os services corretamente")
            print("  4. Verificar se há erros no console do navegador")


def main():
    """Função principal"""
    try:
        checker = DashboardDataChecker()
        checker.check_dashboard_data()
        
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {str(e)}")
        raise


if __name__ == "__main__":
    main()

