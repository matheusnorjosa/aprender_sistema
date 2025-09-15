#!/usr/bin/env python3
"""
Script para testar dashboard com diferentes usuários
Verifica se o problema dos gráficos é relacionado a permissões de usuário
"""

import os
import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import Group
from core.models import Usuario

User = get_user_model()  # Pega o modelo de usuário configurado

def verificar_usuarios():
    print("AUDITORIA DE USUARIOS E PERMISSOES")
    print("=" * 50)
    
    # Listar todos os usuários
    usuarios = User.objects.all()
    print(f"Total de usuarios no sistema: {usuarios.count()}")
    print()
    
    for user in usuarios[:10]:  # Limitar a 10 primeiros
        print(f"Usuario: {user.username} ({user.nome_completo})")
        print(f"   Email: {user.email}")
        print(f"   Ativo: {user.is_active}")
        print(f"   Superuser: {user.is_superuser}")
        print(f"   Staff: {user.is_staff}")
        print(f"   Cargo: {user.get_cargo_display()}")
        
        # Verificar grupos
        grupos = user.groups.all()
        if grupos:
            print(f"   Grupos: {', '.join([g.name for g in grupos])}")
        else:
            print(f"   Grupos: Nenhum")
            
        # Verificar permissões específicas
        perms = ['view_relatorios', 'view_dashboard_executivo']
        user_perms = []
        for perm in perms:
            if user.has_perm(f'core.{perm}'):
                user_perms.append(perm)
        
        if user_perms:
            print(f"   Permissoes: {', '.join(user_perms)}")
        else:
            print(f"   Permissoes: Nenhuma das testadas")
        
        print()
    
    print("GRUPOS EXISTENTES")
    print("-" * 30)
    grupos = Group.objects.all()
    for grupo in grupos:
        print(f"Grupo: {grupo.name}")
        perms = grupo.permissions.filter(codename__in=['view_relatorios', 'view_dashboard_executivo'])
        if perms:
            print(f"   Permissoes dashboard: {', '.join([p.codename for p in perms])}")
        else:
            print(f"   Sem permissoes de dashboard")
        
        # Contar usuários no grupo
        usuarios_grupo = grupo.user_set.count()
        print(f"   Usuarios: {usuarios_grupo}")
        print()

def testar_autenticacao():
    print("TESTE DE AUTENTICACAO")
    print("=" * 30)
    
    # Testar usuário admin
    user_admin = authenticate(username='admin', password='admin123')
    if user_admin:
        print("Admin autenticado com sucesso")
        print(f"   Grupos: {', '.join([g.name for g in user_admin.groups.all()])}")
    else:
        print("Falha na autenticacao do admin")
    
    # Testar usuário diretoria_teste
    user_diretoria = authenticate(username='diretoria_teste', password='teste123')
    if user_diretoria:
        print("diretoria_teste autenticado com sucesso")
        print(f"   Grupos: {', '.join([g.name for g in user_diretoria.groups.all()])}")
    else:
        print("Falha na autenticacao do diretoria_teste")
    
    print()

def verificar_usuario_core():
    print("USUARIOS DO MODELO CORE")
    print("=" * 30)
    
    try:
        usuarios_core = Usuario.objects.all()
        print(f"Total usuários no modelo Usuario (core): {usuarios_core.count()}")
        
        for usuario in usuarios_core[:5]:
            print(f"Usuario: {usuario.nome} - {usuario.perfil}")
            print(f"   Email: {usuario.email}")
            print(f"   Ativo: {usuario.ativo}")
            
            # Verificar se tem User do Django associado
            try:
                django_user = User.objects.get(username=usuario.email)
                print(f"   User Django: {django_user.username}")
            except User.DoesNotExist:
                print(f"   Sem User Django associado")
            print()
            
    except Exception as e:
        print(f"Erro ao acessar modelo Usuario: {e}")

def recomendar_teste():
    print("RECOMENDACOES PARA TESTE")
    print("=" * 40)
    print("1. Teste o dashboard standalone em: http://localhost:8000/diretoria/test/")
    print("   - Não requer autenticação")
    print("   - Testa Chart.js diretamente")
    print("   - Mostra logs de debug detalhados")
    print()
    print("2. Teste com usuário diretoria_teste:")
    print("   - Logout do admin")
    print("   - Login: diretoria_teste / teste123")
    print("   - Acesse: http://localhost:8000/diretoria/dashboard/")
    print()
    print("3. Compare os resultados entre:")
    print("   - Admin vs diretoria_teste")
    print("   - Dashboard integrado vs standalone")
    print()
    print("4. Verifique o console do navegador (F12)")
    print("   - Erros de JavaScript")
    print("   - Falhas de carregamento de recursos")
    print("   - Mensagens de Chart.js")

if __name__ == "__main__":
    verificar_usuarios()
    testar_autenticacao()
    verificar_usuario_core()
    recomendar_teste()