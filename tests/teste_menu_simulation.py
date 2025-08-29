#!/usr/bin/env python
"""
Simulação de teste de menu - verifica se cada grupo veria os links corretos
baseado nas permissões atuais após as correções dos gaps.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.contrib.auth.models import Group, Permission

def simulate_menu_visibility():
    """
    Simula a visibilidade do menu baseado nas condições do base.html
    e nas permissões atuais dos grupos
    """
    print("=== SIMULACAO DE VISIBILIDADE DO MENU ===\n")
    
    # Condições do menu (baseado em base.html)
    menu_conditions = {
        'Início': lambda perms: True,  # Sem condição
        'Mapa Mensal': lambda perms: any(p in perms for p in ['view_aprovacao', 'view_relatorios', 'sync_calendar']),
        'Solicitar Evento': lambda perms: 'add_solicitacao' in perms,
        'Meus Eventos (Coord)': lambda perms: 'add_solicitacao' in perms,
        'Meus Eventos (Form)': lambda perms: 'add_disponibilidadeformadores' in perms,
        'Bloqueio de Agenda': lambda perms: 'add_disponibilidadeformadores' in perms,
        'Aprovações Pendentes': lambda perms: 'view_aprovacao' in perms,
        'Deslocamentos': lambda perms: 'view_aprovacao' in perms,
        'Criar Eventos (Lote)': lambda perms: 'sync_calendar' in perms,
        'Monitor Google Calendar': lambda perms: 'sync_calendar' in perms,
        'Logs de Auditoria': lambda perms: 'sync_calendar' in perms,
        'Status do Sistema': lambda perms: 'sync_calendar' in perms,
        'Formações': lambda perms: any(p in perms for p in ['view_formacao', 'add_compra']),
        'Importar Compras': lambda perms: any(p in perms for p in ['view_formacao', 'add_compra']),
        'Dashboard Executivo': lambda perms: 'view_relatorios' in perms,
        'Relatórios Consolidados': lambda perms: 'view_relatorios' in perms,
        'Visão Mensal': lambda perms: 'view_relatorios' in perms,
        'Métricas API': lambda perms: 'view_relatorios' in perms,
        'Formadores (Cadastro)': lambda perms: 'view_aprovacao' in perms,
        'Municípios (Cadastro)': lambda perms: 'view_aprovacao' in perms,
        'Projetos (Cadastro)': lambda perms: 'view_aprovacao' in perms,
        'Tipos de Evento (Cadastro)': lambda perms: 'view_aprovacao' in perms,
    }
    
    # Testar grupos principais
    grupos_teste = ['admin', 'controle', 'superintendencia']
    
    for grupo_nome in grupos_teste:
        grupo = Group.objects.get(name=grupo_nome)
        perms = list(grupo.permissions.values_list('codename', flat=True))
        
        print(f"=== GRUPO: {grupo_nome.upper()} ===")
        print(f"Permissões: {len(perms)}")
        
        links_visiveis = 0
        total_links = len(menu_conditions)
        
        for menu_item, condition in menu_conditions.items():
            visivel = condition(perms)
            status = "[VE]" if visivel else "[--]"
            print(f"  {status} {menu_item}")
            if visivel:
                links_visiveis += 1
        
        percentual = (links_visiveis / total_links) * 100
        print(f"\nResumo: {links_visiveis}/{total_links} links visíveis ({percentual:.1f}%)")
        print("-" * 50)
        print()

def test_specific_gaps():
    """
    Testa especificamente os gaps que foram corrigidos
    """
    print("=== TESTE DOS GAPS CORRIGIDOS ===\n")
    
    gaps_tests = [
        ("G1 - Admin vê Logs de Auditoria", "admin", "view_logauditoria"),
        ("G2 - Admin vê Formações", "admin", "view_formacao"),
        ("G3 - Admin vê Cadastros", "admin", "view_aprovacao"),
        ("G4 - Controle vê Logs", "controle", "view_logauditoria"),
        ("G5 - Controle vê Formações", "controle", "view_formacao"),
        ("G6 - Controle pode Importar Compras", "controle", "add_compra"),
        ("G7 - Superintendência acessa Municípios", "superintendencia", "view_municipio"),
    ]
    
    for descricao, grupo_nome, permissao in gaps_tests:
        grupo = Group.objects.get(name=grupo_nome)
        tem_permissao = grupo.permissions.filter(codename=permissao).exists()
        status = "[OK] CORRIGIDO" if tem_permissao else "[ERRO] FALHOU"
        print(f"{status} {descricao}")

if __name__ == "__main__":
    simulate_menu_visibility()
    test_specific_gaps()