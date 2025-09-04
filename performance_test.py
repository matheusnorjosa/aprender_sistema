#!/usr/bin/env python
import json
import os
import sys
import time
from datetime import datetime

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client

Usuario = get_user_model()


def test_database_performance():
    """Testa performance do banco de dados"""
    print("=== TESTE PERFORMANCE DATABASE ===")

    results = {}

    # Teste 1: Queries básicas
    start_time = time.time()
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM core_usuario")
        user_count = cursor.fetchone()[0]
    db_query_time = time.time() - start_time

    results["database_queries"] = {
        "simple_count_query": f"{db_query_time:.4f}s",
        "user_count": user_count,
    }

    # Teste 2: ORM vs Raw SQL
    start_time = time.time()
    orm_users = list(Usuario.objects.all()[:10])
    orm_time = time.time() - start_time

    start_time = time.time()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM core_usuario LIMIT 10")
        raw_users = cursor.fetchall()
    raw_time = time.time() - start_time

    results["orm_vs_raw"] = {
        "orm_query_10_users": f"{orm_time:.4f}s",
        "raw_query_10_users": f"{raw_time:.4f}s",
        "raw_sql_advantage": (
            f"{((orm_time - raw_time) / raw_time * 100):.1f}% faster"
            if raw_time > 0
            else "N/A"
        ),
    }

    # Teste 3: Conexões
    start_time = time.time()
    for _ in range(5):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    connection_time = time.time() - start_time

    results["connection_pool"] = {
        "five_connections": f"{connection_time:.4f}s",
        "avg_per_connection": f"{connection_time/5:.4f}s",
    }

    return results


def test_view_performance():
    """Testa performance das views"""
    print("\n=== TESTE PERFORMANCE VIEWS ===")

    client = Client()
    results = {}

    # URLs para testar
    test_urls = [
        "/login/",
        "/admin/login/",  # Página de admin
    ]

    for url in test_urls:
        times = []
        for _ in range(3):  # Testar 3 vezes cada URL
            start_time = time.time()
            try:
                response = client.get(url)
                end_time = time.time()
                times.append(end_time - start_time)
                status_code = response.status_code
            except Exception as e:
                times.append(999)  # Erro
                status_code = "ERROR"

        avg_time = sum(times) / len(times) if times else 0
        results[url.replace("/", "_")] = {
            "avg_response_time": f"{avg_time:.4f}s",
            "min_time": f"{min(times):.4f}s",
            "max_time": f"{max(times):.4f}s",
            "status_code": status_code,
        }

    return results


def test_memory_usage():
    """Testa uso de memória (básico)"""
    print("\n=== TESTE MEMÓRIA ===")

    import os

    import psutil

    # Processo atual
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    results = {
        "process_memory": {
            "rss_mb": f"{memory_info.rss / 1024 / 1024:.1f} MB",
            "vms_mb": f"{memory_info.vms / 1024 / 1024:.1f} MB",
        }
    }

    # Memória do sistema
    system_memory = psutil.virtual_memory()
    results["system_memory"] = {
        "total_gb": f"{system_memory.total / 1024 / 1024 / 1024:.1f} GB",
        "available_gb": f"{system_memory.available / 1024 / 1024 / 1024:.1f} GB",
        "percent_used": f"{system_memory.percent}%",
    }

    return results


def analyze_static_files():
    """Analisa arquivos estáticos"""
    print("\n=== ANÁLISE ARQUIVOS ESTÁTICOS ===")

    import requests

    static_assets = [
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
    ]

    results = {}

    for asset_url in static_assets:
        start_time = time.time()
        try:
            response = requests.get(asset_url, timeout=10)
            load_time = time.time() - start_time

            asset_name = asset_url.split("/")[-1].split("?")[0]
            results[asset_name] = {
                "load_time": f"{load_time:.4f}s",
                "size_kb": f"{len(response.content) / 1024:.1f} KB",
                "status": response.status_code,
            }
        except Exception as e:
            asset_name = asset_url.split("/")[-1].split("?")[0]
            results[asset_name] = {
                "load_time": "ERROR",
                "size_kb": "ERROR",
                "status": "TIMEOUT/ERROR",
                "error": str(e)[:50],
            }

    return results


if __name__ == "__main__":
    print("⚡ INICIANDO TESTES DE PERFORMANCE\n")

    # Executar todos os testes
    db_results = test_database_performance()
    view_results = test_view_performance()
    memory_results = test_memory_usage()
    static_results = analyze_static_files()

    # Compilar relatório
    performance_report = {
        "timestamp": datetime.now().isoformat(),
        "test_environment": "Docker Development",
        "database_performance": db_results,
        "view_performance": view_results,
        "memory_analysis": memory_results,
        "static_assets": static_results,
    }

    print("\n" + "=" * 60)
    print("RELATÓRIO DE PERFORMANCE - SISTEMA APRENDER")
    print("=" * 60)
    print(json.dumps(performance_report, indent=2))
