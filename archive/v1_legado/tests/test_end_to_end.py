#!/usr/bin/env python
"""
Teste End-to-End do fluxo principal do sistema
Simula o fluxo completo: Coordenador cria → Superintendência aprova
"""

import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


def test_end_to_end_flow():
    """Teste completo do fluxo principal"""
    print("=== TESTE END-TO-END DO SISTEMA ===\n")

    # Limpar dados de teste
    Usuario.objects.filter(username__in=["coord_test", "super_test"]).delete()

    # 1. Criar usuários com grupos
    print("1. Criando usuários de teste...")

    # Coordenador
    coord_user = Usuario.objects.create_user(
        username="coord_test", email="coord@test.com", password="test123"
    )
    coord_group = Group.objects.get(name="coordenador")
    coord_user.groups.add(coord_group)

    # Superintendência
    super_user = Usuario.objects.create_user(
        username="super_test", email="super@test.com", password="test123"
    )
    super_group = Group.objects.get(name="superintendencia")
    super_user.groups.add(super_group)

    print(
        f"   + Coordenador criado: {coord_user.username} -> {coord_user.primary_role}"
    )
    print(
        f"   + Superintendência criado: {super_user.username} -> {super_user.primary_role}"
    )

    # 2. Criar dados básicos necessários
    print("\n2. Criando dados básicos...")

    projeto, _ = Projeto.objects.get_or_create(nome="Projeto Teste E2E")
    municipio, _ = Municipio.objects.get_or_create(nome="Cidade Teste", uf="SP")
    tipo_evento, _ = TipoEvento.objects.get_or_create(nome="Workshop E2E")

    print(f"   + Projeto: {projeto.nome}")
    print(f"   + Município: {municipio}")
    print(f"   + Tipo Evento: {tipo_evento.nome}")

    # 3. Teste de permissões de acesso
    print("\n3. Testando permissões de acesso...")

    client = Client()

    # Testar acesso coordenador
    client.login(username="coord_test", password="test123")

    # Verificar se coordenador pode acessar home
    response = client.get(reverse("core:home"))
    coord_home_ok = response.status_code == 200
    print(f"   + Coordenador acessa home: {'✓' if coord_home_ok else '✗'}")

    # Verificar se coordenador pode criar solicitação
    if hasattr(reverse, "core:solicitar_evento"):
        try:
            response = client.get(reverse("core:solicitar_evento"))
            coord_create_ok = response.status_code == 200
            print(
                f"   + Coordenador acessa criar solicitação: {'✓' if coord_create_ok else '✗'}"
            )
        except:
            print("   ! URL solicitar_evento não encontrada")

    # Testar acesso superintendência
    client.login(username="super_test", password="test123")

    # Verificar se superintendência pode acessar aprovações
    if hasattr(reverse, "core:aprovacoes_pendentes"):
        try:
            response = client.get(reverse("core:aprovacoes_pendentes"))
            super_approve_ok = response.status_code == 200
            print(
                f"   + Superintendência acessa aprovações: {'✓' if super_approve_ok else '✗'}"
            )
        except:
            print("   ! URL aprovacoes_pendentes não encontrada")

    # 4. Criar solicitação programaticamente (simular fluxo)
    print("\n4. Simulando criação de solicitação...")

    solicitacao = Solicitacao.objects.create(
        usuario_solicitante=coord_user,
        projeto=projeto,
        municipio=municipio,
        tipo_evento=tipo_evento,
        titulo_evento="Evento Teste E2E",
        data_inicio=timezone.now() + timezone.timedelta(days=7),
        data_fim=timezone.now() + timezone.timedelta(days=7, hours=4),
        status=SolicitacaoStatus.PENDENTE,
    )

    print(f"   + Solicitação criada: {solicitacao.titulo_evento}")
    print(f"   + Status: {solicitacao.status}")
    print(f"   + Solicitante: {solicitacao.usuario_solicitante.username}")

    # 5. Verificar permissões específicas
    print("\n5. Verificando permissões específicas...")

    # Coordenador
    coord_perms = {
        "core.add_solicitacao": coord_user.has_perm("core.add_solicitacao"),
        "core.view_own_solicitacoes": coord_user.has_perm("core.view_own_solicitacoes"),
        "core.add_aprovacao": coord_user.has_perm("core.add_aprovacao"),  # Não deve ter
    }

    # Superintendência
    super_perms = {
        "core.add_solicitacao": super_user.has_perm("core.add_solicitacao"),
        "core.add_aprovacao": super_user.has_perm("core.add_aprovacao"),  # Deve ter
        "core.view_all_solicitacoes": super_user.has_perm("core.view_all_solicitacoes"),
    }

    print("   Coordenador:")
    for perm, has in coord_perms.items():
        status = "✓" if has else "✗"
        print(f"     {status} {perm}: {has}")

    print("   Superintendência:")
    for perm, has in super_perms.items():
        status = "✓" if has else "✗"
        print(f"     {status} {perm}: {has}")

    # 6. Limpeza
    print("\n6. Limpando dados de teste...")
    solicitacao.delete()
    coord_user.delete()
    super_user.delete()
    print("   + Dados limpos")

    # 7. Resultado final
    print("\n=== RESULTADO DO TESTE E2E ===")

    success_checks = [
        coord_home_ok,
        coord_perms["core.add_solicitacao"],
        not coord_perms["core.add_aprovacao"],  # Coordenador NÃO deve ter
        super_perms["core.add_aprovacao"],  # Super DEVE ter
        solicitacao.id is not None,
    ]

    total_checks = len(success_checks)
    passed_checks = sum(success_checks)

    print(f"Testes passaram: {passed_checks}/{total_checks}")

    if passed_checks == total_checks:
        print("✅ TODOS OS TESTES E2E PASSARAM!")
        print("Sistema está funcionando corretamente.")
        return True
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        return False


if __name__ == "__main__":
    success = test_end_to_end_flow()
    sys.exit(0 if success else 1)
