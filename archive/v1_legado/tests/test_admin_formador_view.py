#!/usr/bin/env python
"""
Teste para validar o modo admin da FormadorEventosView
"""
import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Formador,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)

User = get_user_model()


def test_admin_formador_view():
    """Teste da funcionalidade admin na FormadorEventosView"""

    print("🧪 INICIANDO TESTES DA FORMADOR EVENTOS VIEW")
    print("=" * 60)

    # Setup client
    client = Client()

    # 1. Teste com usuário superuser (matheusadm)
    print("\n1️⃣ Testando acesso com superuser matheusadm...")

    try:
        user_admin = User.objects.get(username="matheusadm")
        print(
            f"   ✅ Usuário encontrado: {user_admin.username} (superuser: {user_admin.is_superuser})"
        )
    except User.DoesNotExist:
        print("   ❌ Usuário matheusadm não encontrado")
        return False

    # Login como matheusadm
    login_success = client.login(
        username="matheusadm", password="admin123"
    )  # Assumindo senha padrão
    if not login_success:
        print("   ⚠️  Login falhou, tentando forçar sessão...")
        client.force_login(user_admin)

    # Testar acesso normal (deve funcionar agora)
    print("\n   📋 Testando acesso normal ao /formador/eventos/...")
    response = client.get("/formador/eventos/")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        print("   ✅ Acesso normal funcionando!")
        context = response.context
        print(f"   🔍 Admin mode: {context.get('admin_mode', False)}")
        print(f"   📊 Total eventos: {context.get('total_eventos', 0)}")
        print(f"   💬 Admin message: {context.get('admin_message', 'N/A')}")
    else:
        print(f"   ❌ Acesso falhou com status {response.status_code}")
        return False

    # Testar modo admin geral
    print("\n   🔧 Testando modo admin geral...")
    response = client.get("/formador/eventos/?admin_mode=geral")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        context = response.context
        print(f"   ✅ Modo admin geral ativo: {context.get('admin_mode', False)}")
        print(
            f"   📋 Formadores disponíveis: {len(context.get('formadores_disponiveis', []))}"
        )
        print(f"   📊 Total formadores: {context.get('total_formadores', 0)}")

    # Testar simulação de formador específico
    print("\n   👤 Testando simulação de formador específico...")

    # Pegar um formador para testar
    formador_teste = Formador.objects.filter(ativo=True).first()
    if formador_teste:
        print(f"   🎯 Usando formador: {formador_teste.nome}")
        response = client.get(
            f"/formador/eventos/?admin_mode=formador&admin_formador_id={formador_teste.id}"
        )

        if response.status_code == 200:
            context = response.context
            simulado = context.get("admin_formador_simulado")
            print(f"   ✅ Simulação ativa: {simulado.nome if simulado else 'N/A'}")
            print(f"   📊 Eventos do formador: {context.get('total_eventos', 0)}")
        else:
            print(f"   ❌ Simulação falhou: {response.status_code}")
    else:
        print("   ⚠️  Nenhum formador disponível para teste")

    # 2. Teste com usuário normal (coordenador)
    print("\n2️⃣ Testando acesso com usuário normal (coordenador)...")

    try:
        user_coord = User.objects.get(username="coord_test")
        print(
            f"   ✅ Usuário encontrado: {user_coord.username} (superuser: {user_coord.is_superuser})"
        )

        client.force_login(user_coord)
        response = client.get("/formador/eventos/")

        if response.status_code == 200:
            context = response.context
            admin_mode = context.get("admin_mode", False)
            erro = context.get("erro")

            print(f"   🔍 Admin mode (deve ser False): {admin_mode}")
            print(f"   💬 Erro esperado: {erro[:50] if erro else 'N/A'}...")

            if not admin_mode and erro:
                print(
                    "   ✅ Comportamento correto: usuário normal vê erro sem modo admin"
                )
            else:
                print("   ⚠️  Comportamento inesperado detectado")
        else:
            print(f"   Status: {response.status_code}")

    except User.DoesNotExist:
        print("   ⚠️  Usuário coord_test não encontrado, pulando teste")

    print("\n" + "=" * 60)
    print("🎉 TESTES CONCLUÍDOS!")
    return True


if __name__ == "__main__":
    test_admin_formador_view()
