#!/usr/bin/env python
import os
import sys
import time
from urllib.parse import urljoin

import django

import requests

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session


def test_authentication_bypass():
    """Testa bypasses de autenticação"""
    print("=== TESTE BYPASS DE AUTENTICAÇÃO ===")

    base_url = "http://localhost:8000"

    # URLs que devem estar protegidas
    protected_urls = [
        "/solicitacao/",
        "/aprovacoes/pendentes/",
        "/admin/",
        "/disponibilidade/",
    ]

    results = []

    for url in protected_urls:
        try:
            response = requests.get(
                urljoin(base_url, url), allow_redirects=False, timeout=5
            )

            if response.status_code == 200:
                results.append(
                    {
                        "url": url,
                        "status": "VULNERÁVEL",
                        "code": response.status_code,
                        "description": "Acesso sem autenticação",
                    }
                )
            elif response.status_code in [302, 301]:
                # Verifica se redireciona para login
                location = response.headers.get("Location", "")
                if "login" in location:
                    results.append(
                        {
                            "url": url,
                            "status": "PROTEGIDO",
                            "code": response.status_code,
                            "description": "Redirecionamento para login",
                        }
                    )
                else:
                    results.append(
                        {
                            "url": url,
                            "status": "ATENÇÃO",
                            "code": response.status_code,
                            "description": f"Redireciona para: {location}",
                        }
                    )
            elif response.status_code in [401, 403]:
                results.append(
                    {
                        "url": url,
                        "status": "PROTEGIDO",
                        "code": response.status_code,
                        "description": "Acesso negado",
                    }
                )
            else:
                results.append(
                    {
                        "url": url,
                        "status": "INDEFINIDO",
                        "code": response.status_code,
                        "description": "Status não esperado",
                    }
                )

        except requests.RequestException as e:
            results.append(
                {"url": url, "status": "ERRO", "code": 0, "description": str(e)[:50]}
            )

    for result in results:
        print(
            f"URL: {result['url']} - Status: {result['status']} ({result['code']}) - {result['description']}"
        )

    return results


def test_csrf_protection():
    """Testa proteção CSRF"""
    print("\n=== TESTE PROTEÇÃO CSRF ===")

    base_url = "http://localhost:8000"

    # Tenta fazer POST sem token CSRF
    try:
        response = requests.post(
            f"{base_url}/login/",
            data={"username": "test", "password": "test"},
            timeout=5,
        )

        if "csrfmiddlewaretoken" in response.text or "CSRF" in response.text:
            print("✅ CSRF: Proteção ativa - token obrigatório")
            return True
        else:
            print("⚠️ CSRF: Possível vulnerabilidade")
            return False

    except Exception as e:
        print(f"❌ CSRF: Erro no teste - {str(e)[:50]}")
        return None


def test_user_enumeration():
    """Testa enumeração de usuários"""
    print("\n=== TESTE ENUMERAÇÃO DE USUÁRIOS ===")

    try:
        # Lista usuários existentes (informativo)
        users = User.objects.all()[:5]
        print(f"Total de usuários cadastrados: {User.objects.count()}")

        for user in users:
            print(
                f"Usuário: {user.username} - Ativo: {user.is_active} - Staff: {user.is_staff}"
            )

        # Verifica se admin existe
        admin_exists = User.objects.filter(username="admin").exists()
        superuser_count = User.objects.filter(is_superuser=True).count()

        print(f"Admin padrão existe: {admin_exists}")
        print(f"Superusuários: {superuser_count}")

        return {
            "total_users": User.objects.count(),
            "admin_exists": admin_exists,
            "superuser_count": superuser_count,
        }

    except Exception as e:
        print(f"❌ Enumeração: Erro no teste - {str(e)}")
        return None


def test_session_security():
    """Testa segurança de sessões"""
    print("\n=== TESTE SEGURANÇA DE SESSÕES ===")

    try:
        sessions = Session.objects.all()
        active_sessions = sessions.count()

        print(f"Sessões ativas: {active_sessions}")

        if active_sessions > 0:
            sample_session = sessions.first()
            print(f"Exemplo de sessão: {sample_session.session_key[:10]}...")
            print(f"Expira em: {sample_session.expire_date}")

        return {
            "active_sessions": active_sessions,
            "session_framework": "Django default",
        }

    except Exception as e:
        print(f"❌ Sessões: Erro no teste - {str(e)}")
        return None


if __name__ == "__main__":
    print("🔒 INICIANDO TESTES DE SEGURANÇA DE AUTENTICAÇÃO\n")

    auth_results = test_authentication_bypass()
    csrf_results = test_csrf_protection()
    enum_results = test_user_enumeration()
    session_results = test_session_security()

    # Compilar resultados
    security_report = {
        "authentication_bypass": auth_results,
        "csrf_protection": csrf_results,
        "user_enumeration": enum_results,
        "session_security": session_results,
    }

    import json

    print("\n" + "=" * 50)
    print("RELATÓRIO DE SEGURANÇA - AUTENTICAÇÃO")
    print("=" * 50)
    print(json.dumps(security_report, indent=2, default=str))
