#!/usr/bin/env python
"""
Test para verificar se os coordenadores estão aparecendo corretamente no dashboard
após a correção das solicitações importadas.
"""

import os
import sys
import django
import requests
from datetime import datetime

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Usuario, Solicitacao
from django.db.models import Count


def test_dashboard_coordinators():
    """Testa se os coordenadores estão aparecendo corretamente no dashboard"""

    print("🔍 VERIFICAÇÃO DOS COORDENADORES NO DASHBOARD")
    print("=" * 60)

    # 1. Verificar quantas solicitações ainda têm admin como solicitante
    admin_user = Usuario.objects.filter(username="admin").first()

    if admin_user:
        admin_requests = Solicitacao.objects.filter(
            usuario_solicitante=admin_user
        ).count()
        print(f"📊 Solicitações ainda com admin como solicitante: {admin_requests}")

    # 2. Verificar coordenadores únicos nas solicitações
    coordinators_with_requests = (
        Solicitacao.objects.values(
            "usuario_solicitante__nome_completo", "usuario_solicitante__username"
        )
        .annotate(total_requests=Count("id"))
        .order_by("-total_requests")
    )

    print(
        f"\n👥 COORDENADORES COM SOLICITAÇÕES ({len(coordinators_with_requests)} total):"
    )
    print("-" * 60)

    for i, coord in enumerate(coordinators_with_requests[:10], 1):
        nome = coord["usuario_solicitante__nome_completo"] or "Nome não informado"
        username = coord["usuario_solicitante__username"]
        total = coord["total_requests"]
        print(f"{i:2d}. {nome} ({username}) - {total} solicitações")

    if len(coordinators_with_requests) > 10:
        print(f"    ... e mais {len(coordinators_with_requests) - 10} coordenadores")

    # 3. Verificar coordenadores por município (simulando API)
    coordinators_by_city = (
        Solicitacao.objects.values(
            "municipio__nome",
            "usuario_solicitante__nome_completo",
            "usuario_solicitante__username",
        )
        .annotate(total_eventos=Count("id"))
        .order_by("municipio__nome", "-total_eventos")
    )

    print(f"\n🏙️ COORDENADORES POR MUNICÍPIO (top 15):")
    print("-" * 60)

    current_city = None
    city_count = 0

    for coord in coordinators_by_city:
        city = coord["municipio__nome"]
        nome = coord["usuario_solicitante__nome_completo"] or "Nome não informado"
        username = coord["usuario_solicitante__username"]
        total = coord["total_eventos"]

        if city != current_city:
            current_city = city
            city_count += 1
            if city_count > 15:  # Limitar output
                break
            print(f"\n📍 {city}:")

        print(f"   • {nome} ({username}) - {total} eventos")

    # 4. Verificar se ainda há "admin" nos resultados
    has_admin = any(
        coord["usuario_solicitante__username"] == "admin"
        for coord in coordinators_with_requests
    )

    print(f"\n✅ RESULTADO DA VERIFICAÇÃO:")
    print("-" * 40)

    if has_admin:
        admin_count = next(
            coord["total_requests"]
            for coord in coordinators_with_requests
            if coord["usuario_solicitante__username"] == "admin"
        )
        print(f"⚠️  Ainda há {admin_count} solicitações com 'admin' como solicitante")
        print("   Pode ser necessário executar novamente o comando de correção")
    else:
        print("✅ Nenhuma solicitação tem 'admin' como solicitante")
        print("✅ Correção de coordenadores aplicada com sucesso!")

    # 5. Estatísticas gerais
    total_requests = Solicitacao.objects.count()
    total_coordinators = len(coordinators_with_requests)

    print(f"\n📈 ESTATÍSTICAS GERAIS:")
    print(f"   Total de solicitações: {total_requests}")
    print(f"   Total de coordenadores: {total_coordinators}")
    print(f"   Média por coordenador: {total_requests/total_coordinators:.1f}")


def test_api_endpoint():
    """Testa o endpoint da API do dashboard"""

    print(f"\n🌐 TESTE DO ENDPOINT DA API")
    print("=" * 40)

    try:
        # Tentar acessar a API local
        response = requests.get(
            "http://localhost:8000/api/dashboard/coordenadores/", timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ API respondeu com sucesso")
            print(f"📊 Dados retornados: {len(data)} registros")

            # Mostrar alguns exemplos
            if data:
                print("\n📋 Primeiros 5 registros:")
                for i, item in enumerate(data[:5], 1):
                    print(f"   {i}. {item}")

        else:
            print(f"❌ API retornou status {response.status_code}")
            print(f"   Resposta: {response.text}")

    except requests.exceptions.ConnectionError:
        print("⚠️  Servidor não está rodando em localhost:8000")
        print("   Execute: python manage.py runserver")

    except Exception as e:
        print(f"❌ Erro ao testar API: {e}")


if __name__ == "__main__":
    print(f"🕐 Início da verificação: {datetime.now().strftime('%H:%M:%S')}")
    test_dashboard_coordinators()
    test_api_endpoint()
    print(f"\n🕐 Fim da verificação: {datetime.now().strftime('%H:%M:%S')}")
