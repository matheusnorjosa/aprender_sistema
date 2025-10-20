#!/usr/bin/env python
"""
Teste simples para validar a view FormadorEventosView
"""
import os

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest

from core.models import Formador, Usuario
from core.views import FormadorEventosView


def test_view_logic():
    """Testa a lógica da view diretamente"""

    print("🧪 TESTE DIRETO DA LÓGICA DA VIEW")
    print("=" * 50)

    # Criar view instance
    view = FormadorEventosView()

    # Simular request com superuser
    request = HttpRequest()
    request.method = "GET"
    request.GET = {}  # Query params vazios primeiro

    try:
        user = Usuario.objects.get(username="matheusadm")
        request.user = user

        print(f"👤 Usuário: {user.username}")
        print(f"🔑 Is superuser: {user.is_superuser}")
        print(f"📧 Email: '{user.email}'")

        # Testar contexto normal
        print("\n1️⃣ Teste modo normal...")
        view.request = request
        context = view.get_context_data()

        print(f"   Admin mode: {context.get('admin_mode', False)}")
        print(f"   Formador: {context.get('formador')}")
        print(f"   Erro: {context.get('erro', 'N/A')}")
        print(f"   Total eventos: {context.get('total_eventos', 0)}")
        print(f"   Admin message: {context.get('admin_message', 'N/A')}")

        # Testar com parâmetros admin
        print("\n2️⃣ Teste modo admin geral...")
        request.GET = {"admin_mode": "geral"}
        view.request = request
        context = view.get_context_data()

        print(f"   Admin mode: {context.get('admin_mode', False)}")
        print(f"   Admin mode type: {context.get('admin_mode_type', 'N/A')}")
        print(
            f"   Formadores disponíveis: {len(context.get('formadores_disponiveis', []))}"
        )
        print(f"   Total formadores: {context.get('total_formadores', 0)}")
        print(f"   Total eventos: {context.get('total_eventos', 0)}")

        # Testar simulação de formador
        print("\n3️⃣ Teste simulação formador...")
        formador_teste = Formador.objects.filter(ativo=True).first()
        if formador_teste:
            request.GET = {
                "admin_mode": "formador",
                "admin_formador_id": str(formador_teste.id),
            }
            view.request = request
            context = view.get_context_data()

            print(f"   Formador simulado: {context.get('admin_formador_simulado')}")
            print(f"   Total eventos: {context.get('total_eventos', 0)}")
        else:
            print("   ⚠️  Nenhum formador disponível")

        print("\n✅ Testes da lógica concluídos com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_formador_normal():
    """Testa com usuário formador normal"""
    print("\n" + "=" * 50)
    print("🧪 TESTE COM USUÁRIO FORMADOR NORMAL")

    # Encontrar um formador com email
    formador = Formador.objects.filter(ativo=True).exclude(email="").first()
    if not formador:
        print("⚠️  Nenhum formador com email encontrado")
        return False

    print(f"👤 Formador: {formador.nome} ({formador.email})")

    # Criar usuário temporário com email do formador
    try:
        user, created = Usuario.objects.get_or_create(
            email=formador.email,
            defaults={
                "username": f"test_formador_{formador.id}",
                "is_superuser": False,
            },
        )
        print(f"👤 Usuário: {user.username} (criado: {created})")

        # Testar view
        view = FormadorEventosView()
        request = HttpRequest()
        request.method = "GET"
        request.GET = {}
        request.user = user
        view.request = request

        context = view.get_context_data()

        print(f"   Admin mode: {context.get('admin_mode', False)}")
        print(f"   Formador encontrado: {context.get('formador')}")
        print(f"   Total eventos: {context.get('total_eventos', 0)}")

        if created:
            user.delete()  # Limpar usuário teste

        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == "__main__":
    success1 = test_view_logic()
    success2 = test_formador_normal()

    if success1 and success2:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("\n⚠️  Alguns testes falharam")
