#!/usr/bin/env python3
"""
Script para criar usuário de teste da diretoria e testar APIs.
"""

import os
import sys

import django

# Configuração do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth.models import Group

from core.models import Usuario


def create_test_user():
    """Cria usuário de teste da diretoria"""

    # Verificar se usuário já existe
    username = "diretoria_teste"
    if Usuario.objects.filter(username=username).exists():
        user = Usuario.objects.get(username=username)
        print(f"Usuario '{username}' ja existe")
    else:
        # Criar usuário
        user = Usuario.objects.create_user(
            username=username,
            password="teste123",
            email="diretoria@teste.com",
            first_name="Usuario",
            last_name="Diretoria Teste",
        )
        print(f"Usuario '{username}' criado com sucesso")

    # Adicionar ao grupo diretoria
    diretoria_group = Group.objects.filter(name="diretoria").first()
    if diretoria_group:
        if not user.groups.filter(name="diretoria").exists():
            user.groups.add(diretoria_group)
            print("Usuario adicionado ao grupo 'diretoria'")
        else:
            print("Usuario ja estava no grupo 'diretoria'")
    else:
        print("ERRO: Grupo 'diretoria' nao encontrado!")
        return False

    # Verificar permissões
    has_view_relatorios = user.has_perm("core.view_relatorios")
    print(f"Usuario tem permissao 'view_relatorios': {has_view_relatorios}")

    if has_view_relatorios:
        print(f"\n=== DADOS DE LOGIN ===")
        print(f"URL: http://localhost:8000/login/")
        print(f"Usuario: {username}")
        print(f"Senha: teste123")
        print(f"======================")

    return True


if __name__ == "__main__":
    print("=== Criando usuario de teste da diretoria ===")
    success = create_test_user()
    if success:
        print("\nUsuario criado com sucesso!")
    else:
        print("\nErro ao criar usuario!")
        sys.exit(1)
