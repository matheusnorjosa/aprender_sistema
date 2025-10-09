#!/usr/bin/env python
"""
Script de teste final para validar dashboard após correções
Testa todos os endpoints críticos do dashboard executivo
"""

import os
import sys
import django
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from core.models import Usuario


def test_dashboard_endpoints():
    """Testa todos os endpoints críticos do dashboard"""

    print("🔍 INICIANDO TESTES DO DASHBOARD EXECUTIVO")
    print("=" * 60)

    # Setup cliente de teste
    client = Client()

    # Login como admin (assumindo que existe)
    try:
        admin_user = Usuario.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("❌ ERRO: Nenhum usuário admin encontrado")
            return False

        client.force_login(admin_user)
        print(f"✅ Login realizado como: {admin_user.username}")

    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return False

    # Lista de endpoints para testar
    endpoints = [
        ("/diretoria/dashboard/", "Dashboard Principal"),
        ("/api/dashboard/stats/", "API Stats"),
        ("/api/dashboard/charts/?chart=monthly_evolution", "API Charts - Monthly"),
        ("/api/dashboard/charts/?chart=top_formadores", "API Charts - Formadores"),
        ("/api/dashboard/charts/?chart=distribuicao_setores", "API Charts - Setores"),
        (
            "/api/dashboard/charts/?chart=municipios_atendidos",
            "API Charts - Municípios",
        ),
        ("/api/dashboard/charts/?chart=tipos_evento", "API Charts - Tipos"),
        ("/api/dashboard/charts/?chart=projetos_stats", "API Charts - Projetos"),
        ("/api/dashboard/cursos/", "API Cursos"),
        ("/api/dashboard/coordenadores/", "API Coordenadores"),
    ]

    results = {}

    for endpoint, description in endpoints:
        try:
            print(f"\n🧪 Testando: {description}")
            print(f"   URL: {endpoint}")

            response = client.get(endpoint)
            status_code = response.status_code

            if status_code == 200:
                print(f"   ✅ Status: {status_code} OK")

                # Para APIs JSON, verificar estrutura
                if endpoint.startswith("/api/"):
                    try:
                        import json

                        data = json.loads(response.content)

                        if "success" in data:
                            print(f"   ✅ JSON válido com success: {data['success']}")
                        elif "data" in data:
                            print(f"   ✅ JSON válido com data")
                        else:
                            print(f"   ⚠️  JSON válido mas estrutura inesperada")

                    except json.JSONDecodeError:
                        print(f"   ❌ Resposta não é JSON válido")

                results[endpoint] = "OK"

            elif status_code == 500:
                print(f"   ❌ Status: {status_code} ERRO INTERNO")
                results[endpoint] = "ERRO_500"

            elif status_code == 404:
                print(f"   ❌ Status: {status_code} NÃO ENCONTRADO")
                results[endpoint] = "ERRO_404"

            else:
                print(f"   ⚠️  Status: {status_code}")
                results[endpoint] = f"STATUS_{status_code}"

        except Exception as e:
            print(f"   ❌ Exceção: {str(e)[:100]}...")
            results[endpoint] = f"EXCEÇÃO: {str(e)[:50]}"

    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL DOS TESTES")
    print("=" * 60)

    success_count = sum(1 for result in results.values() if result == "OK")
    total_count = len(results)

    print(f"\n✅ Sucessos: {success_count}/{total_count}")
    print(f"❌ Falhas: {total_count - success_count}/{total_count}")

    if success_count == total_count:
        print("\n🎉 TODOS OS TESTES PASSARAM! Dashboard funcionando corretamente.")
        return True
    else:
        print(f"\n⚠️  {total_count - success_count} endpoints com problemas:")
        for endpoint, result in results.items():
            if result != "OK":
                print(f"   - {endpoint}: {result}")
        return False


def check_database_connectivity():
    """Verifica conectividade com o banco"""
    try:
        from django.db import connection

        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ Conectividade com banco PostgreSQL: OK")
        return True
    except Exception as e:
        print(f"❌ Erro de conectividade: {e}")
        return False


def check_models_integrity():
    """Verifica integridade dos modelos após unificação"""
    try:
        from core.models import Usuario, Solicitacao, FormadoresSolicitacao

        print("\n🔍 Verificando integridade dos modelos...")

        # Verificar contagens básicas
        usuarios_count = Usuario.objects.count()
        solicitacoes_count = Solicitacao.objects.count()
        formadores_sol_count = FormadoresSolicitacao.objects.count()

        print(f"   - Usuários: {usuarios_count}")
        print(f"   - Solicitações: {solicitacoes_count}")
        print(f"   - FormadoresSolicitacao: {formadores_sol_count}")

        # Testar query com novo campo usuario
        try:
            test_query = FormadoresSolicitacao.objects.select_related("usuario").first()
            if test_query and hasattr(test_query, "usuario"):
                print("   ✅ Campo 'usuario' acessível em FormadoresSolicitacao")
            else:
                print("   ❌ Campo 'usuario' não encontrado em FormadoresSolicitacao")
                return False
        except Exception as e:
            print(f"   ❌ Erro ao acessar campo usuario: {e}")
            return False

        print("✅ Integridade dos modelos: OK")
        return True

    except Exception as e:
        print(f"❌ Erro na verificação dos modelos: {e}")
        return False


if __name__ == "__main__":
    print(f"🚀 Iniciando validação completa - {datetime.now().strftime('%H:%M:%S')}")

    # Verificações preliminares
    db_ok = check_database_connectivity()
    models_ok = check_models_integrity()

    if not (db_ok and models_ok):
        print("\n❌ Falhas nas verificações preliminares. Abortando testes.")
        sys.exit(1)

    # Testes do dashboard
    dashboard_ok = test_dashboard_endpoints()

    if dashboard_ok:
        print(
            f"\n🎉 VALIDAÇÃO COMPLETA FINALIZADA COM SUCESSO - {datetime.now().strftime('%H:%M:%S')}"
        )
        sys.exit(0)
    else:
        print(f"\n❌ VALIDAÇÃO FALHOU - {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(1)
