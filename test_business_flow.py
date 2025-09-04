#!/usr/bin/env python
"""
Teste do fluxo de negócio principal - versão simplificada
Verifica permissões e criação de dados
"""

import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import Group
from django.utils import timezone

from core.models import (
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


def test_business_flow():
    """Teste do fluxo de negócio principal"""
    print("=== TESTE DE FLUXO DE NEGOCIO ===\n")

    # Limpar dados de teste
    Usuario.objects.filter(username__in=["coord_flow", "super_flow"]).delete()

    # 1. Criar usuários com papéis específicos
    print("1. Criando usuarios com papeis...")

    # Coordenador
    coord_user = Usuario.objects.create_user(
        username="coord_flow", email="coord@flow.com", password="test123"
    )
    coord_group = Group.objects.get(name="coordenador")
    coord_user.groups.add(coord_group)

    # Superintendência
    super_user = Usuario.objects.create_user(
        username="super_flow", email="super@flow.com", password="test123"
    )
    super_group = Group.objects.get(name="superintendencia")
    super_user.groups.add(super_group)

    # Formador
    form_user = Usuario.objects.create_user(
        username="form_flow", email="form@flow.com", password="test123"
    )
    form_group = Group.objects.get(name="formador")
    form_user.groups.add(form_group)

    print(f"   + Coordenador: {coord_user.username} -> {coord_user.primary_role}")
    print(f"   + Superintendencia: {super_user.username} -> {super_user.primary_role}")
    print(f"   + Formador: {form_user.username} -> {form_user.primary_role}")

    # 2. Verificar permissões por papel
    print("\n2. Verificando permissoes por papel...")

    # Permissões esperadas
    permissions_test = {
        "coordenador": {
            "core.add_solicitacao": True,
            "core.view_own_solicitacoes": True,
            "core.sync_calendar": True,
            "core.add_aprovacao": False,  # NÃO deve ter
            "core.view_all_solicitacoes": False,  # NÃO deve ter
        },
        "superintendencia": {
            "core.add_solicitacao": True,
            "core.view_own_solicitacoes": True,
            "core.add_aprovacao": True,  # DEVE ter
            "core.view_all_solicitacoes": True,  # DEVE ter
            "core.view_calendar": True,
        },
        "formador": {
            "core.view_own_events": True,  # DEVE ter
            "core.add_solicitacao": False,  # NÃO deve ter
            "core.add_aprovacao": False,  # NÃO deve ter
        },
    }

    users_test = {
        "coordenador": coord_user,
        "superintendencia": super_user,
        "formador": form_user,
    }

    all_passed = True

    for role, user in users_test.items():
        print(f"\n   {role.upper()}:")
        role_perms = permissions_test[role]

        for perm, expected in role_perms.items():
            actual = user.has_perm(perm)
            status = "+" if actual == expected else "-"

            if actual != expected:
                all_passed = False

            print(f"     {status} {perm}: esperado={expected}, atual={actual}")

    # 3. Criar dados básicos
    print("\n3. Criando dados basicos para teste...")

    projeto, _ = Projeto.objects.get_or_create(nome="Projeto Flow Test")
    municipio, _ = Municipio.objects.get_or_create(nome="Cidade Flow", uf="RJ")
    tipo_evento, _ = TipoEvento.objects.get_or_create(nome="Workshop Flow")

    print(f"   + Projeto: {projeto.nome}")
    print(f"   + Municipio: {municipio}")
    print(f"   + Tipo: {tipo_evento.nome}")

    # 4. Simular criação de solicitação pelo coordenador
    print("\n4. Simulando fluxo: Coordenador cria solicitacao...")

    try:
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=coord_user,
            projeto=projeto,
            municipio=municipio,
            tipo_evento=tipo_evento,
            titulo_evento="Evento Flow Test",
            data_inicio=timezone.now() + timezone.timedelta(days=10),
            data_fim=timezone.now() + timezone.timedelta(days=10, hours=6),
            status=SolicitacaoStatus.PENDENTE,
        )

        print(f"   + Solicitacao criada: {solicitacao.titulo_evento}")
        print(f"   + Status inicial: {solicitacao.status}")
        print(f"   + Criada por: {solicitacao.usuario_solicitante.primary_role}")
        solicitacao_created = True

    except Exception as e:
        print(f"   - Erro ao criar solicitacao: {e}")
        solicitacao_created = False
        all_passed = False

    # 5. Verificar se superintendência pode "ver" a solicitação
    print("\n5. Verificando acesso a solicitacao...")

    # Superintendência deve poder ver todas as solicitações
    super_can_view_all = super_user.has_perm("core.view_all_solicitacoes")
    print(f"   + Super pode ver todas: {super_can_view_all}")

    # Coordenador pode ver apenas as próprias
    coord_can_view_own = coord_user.has_perm("core.view_own_solicitacoes")
    print(f"   + Coord pode ver proprias: {coord_can_view_own}")

    # Formador não deve poder ver solicitações administrativas
    form_cannot_view = not form_user.has_perm("core.view_all_solicitacoes")
    print(f"   + Formador NAO ve admin: {form_cannot_view}")

    # 6. Limpeza
    print("\n6. Limpeza dos dados de teste...")
    if solicitacao_created:
        solicitacao.delete()

    coord_user.delete()
    super_user.delete()
    form_user.delete()
    print("   + Usuarios removidos")

    # 7. Resultado
    print("\n=== RESULTADO DO TESTE DE FLUXO ===")

    if all_passed and solicitacao_created and super_can_view_all and coord_can_view_own:
        print("+ TESTE DE FLUXO DE NEGOCIO PASSOU!")
        print("Sistema esta funcionando conforme especificado.")
        return True
    else:
        print("- TESTE DE FLUXO DE NEGOCIO FALHOU!")
        print("Verificar permissoes e configuracoes.")
        return False


if __name__ == "__main__":
    success = test_business_flow()
    sys.exit(0 if success else 1)
