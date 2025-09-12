#!/usr/bin/env python
"""
Script para validação completa dos testes do dashboard
Executa todos os testes e gera relatório de cobertura

Uso:
    python validate_dashboard_tests.py
    python validate_dashboard_tests.py --verbose
    python validate_dashboard_tests.py --coverage
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Adicionar o projeto ao path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")

import django

django.setup()

from django.conf import settings
from django.core.management import call_command
from django.test.utils import get_runner


class DashboardTestValidator:
    """Validador completo dos testes do dashboard"""

    def __init__(self, verbose=False, coverage=False):
        self.verbose = verbose
        self.coverage = coverage
        self.test_modules = [
            "core.test_dashboard_api",
            "core.test_dashboard_template",
            "core.test_dashboard_filters",
            "core.test_dashboard_performance",
            "core.test_metricas_avancadas",
            "core.test_dashboard_suite",
        ]

    def print_header(self, title):
        """Imprimir cabeçalho formatado"""
        print("\n" + "=" * 60)
        print(f" {title}")
        print("=" * 60)

    def print_section(self, title):
        """Imprimir seção formatada"""
        print(f"\n{'─'*40}")
        print(f" {title}")
        print("─" * 40)

    def run_basic_tests(self):
        """Executar testes básicos sem coverage"""
        self.print_header("EXECUTANDO TESTES BÁSICOS DO DASHBOARD")

        results = {}

        for module in self.test_modules:
            self.print_section(f"Testando: {module}")

            try:
                # Executar teste específico
                runner = get_runner(settings)
                test_runner = runner(verbosity=1 if self.verbose else 0)

                # Capturar resultado
                result = test_runner.run_tests([module])

                if result == 0:
                    print(f"✅ {module}: PASSOU")
                    results[module] = "PASSOU"
                else:
                    print(f"❌ {module}: FALHOU")
                    results[module] = "FALHOU"

            except Exception as e:
                print(f"💥 {module}: ERRO - {str(e)}")
                results[module] = f"ERRO: {str(e)}"

        return results

    def run_coverage_tests(self):
        """Executar testes com análise de cobertura"""
        self.print_header("EXECUTANDO TESTES COM ANÁLISE DE COBERTURA")

        try:
            # Verificar se coverage está instalado
            import coverage

            # Inicializar coverage
            cov = coverage.Coverage(
                source=["core"],
                omit=[
                    "*/migrations/*",
                    "*/tests*",
                    "*/venv/*",
                    "*/env/*",
                    "*/__pycache__/*",
                ],
            )

            cov.start()

            # Executar todos os testes
            self.print_section("Executando testes com coverage...")

            runner = get_runner(settings)
            test_runner = runner(verbosity=1 if self.verbose else 0)
            result = test_runner.run_tests(self.test_modules)

            cov.stop()
            cov.save()

            # Gerar relatório
            self.print_section("Relatório de Cobertura")

            print("Cobertura por arquivo:")
            cov.report(show_missing=True)

            # Gerar relatório HTML se possível
            try:
                html_dir = BASE_DIR / "htmlcov"
                cov.html_report(directory=str(html_dir))
                print(f"\n📊 Relatório HTML gerado em: {html_dir}/index.html")
            except Exception:
                print("⚠️  Não foi possível gerar relatório HTML")

            return result == 0

        except ImportError:
            print("❌ Pacote 'coverage' não está instalado")
            print("   Instale com: pip install coverage")
            return False
        except Exception as e:
            print(f"💥 Erro ao executar coverage: {str(e)}")
            return False

    def run_performance_benchmark(self):
        """Executar benchmark de performance da API"""
        self.print_header("BENCHMARK DE PERFORMANCE")

        try:
            import time

            from django.contrib.auth import get_user_model
            from django.test import Client
            from django.urls import reverse

            import requests

            # Criar usuário de teste
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username="benchmark_user",
                defaults={"email": "benchmark@test.com", "papel": "coordenador"},
            )
            if created:
                user.set_password("testpass123")
                user.save()

            client = Client()
            client.login(username="benchmark_user", password="testpass123")

            # Testar API
            url = reverse("core:dashboard_stats_api")

            # Warm up
            client.get(url)

            # Benchmark cold cache
            from django.core.cache import cache

            cache.clear()

            start_time = time.time()
            response = client.get(url)
            cold_time = time.time() - start_time

            print(f"🔥 Cold cache: {cold_time:.3f}s")

            # Benchmark warm cache
            start_time = time.time()
            response = client.get(url)
            warm_time = time.time() - start_time

            print(f"⚡ Warm cache: {warm_time:.3f}s")
            print(f"🚀 Speedup: {cold_time/warm_time:.1f}x")

            # Verificar se está dentro dos limites
            if cold_time < 1.0:
                print("✅ Cold cache dentro do limite (< 1s)")
            else:
                print("❌ Cold cache muito lento (> 1s)")

            if warm_time < 0.1:
                print("✅ Warm cache dentro do limite (< 0.1s)")
            else:
                print("❌ Warm cache muito lento (> 0.1s)")

            return cold_time < 1.0 and warm_time < 0.1

        except Exception as e:
            print(f"💥 Erro no benchmark: {str(e)}")
            return False

    def validate_api_endpoints(self):
        """Validar se todos os endpoints estão funcionais"""
        self.print_header("VALIDAÇÃO DE ENDPOINTS")

        try:
            import json

            from django.contrib.auth import get_user_model
            from django.test import Client
            from django.urls import reverse

            # Criar usuário
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username="endpoint_user",
                defaults={"email": "endpoint@test.com", "papel": "coordenador"},
            )
            if created:
                user.set_password("testpass123")
                user.save()

            client = Client()
            client.login(username="endpoint_user", password="testpass123")

            endpoints = [
                ("core:home", "GET", None),
                ("core:dashboard_stats_api", "GET", None),
                ("core:dashboard_stats_api", "GET", {"periodo": "7"}),
                ("core:dashboard_stats_api", "GET", {"periodo": "30"}),
                ("core:dashboard_stats_api", "GET", {"periodo": "90"}),
            ]

            results = {}

            for name, method, params in endpoints:
                try:
                    url = reverse(name)

                    if method == "GET":
                        if params:
                            response = client.get(url, params)
                            endpoint_key = f"{name}?{params}"
                        else:
                            response = client.get(url)
                            endpoint_key = name

                    if response.status_code == 200:
                        print(f"✅ {endpoint_key}: {response.status_code}")
                        results[endpoint_key] = True

                        # Validar JSON para APIs
                        if "api" in name:
                            try:
                                data = json.loads(response.content)
                                if "estatisticas" in data:
                                    print(f"   📊 JSON válido com estatísticas")
                                else:
                                    print(f"   ⚠️  JSON sem campo estatísticas")
                            except:
                                print(f"   ❌ JSON inválido")
                                results[endpoint_key] = False
                    else:
                        print(f"❌ {endpoint_key}: {response.status_code}")
                        results[endpoint_key] = False

                except Exception as e:
                    print(f"💥 {name}: ERRO - {str(e)}")
                    results[name] = False

            return all(results.values())

        except Exception as e:
            print(f"💥 Erro na validação de endpoints: {str(e)}")
            return False

    def generate_final_report(
        self, basic_results, coverage_passed, performance_passed, endpoints_passed
    ):
        """Gerar relatório final consolidado"""
        self.print_header("RELATÓRIO FINAL DE VALIDAÇÃO")

        # Estatísticas básicas
        total_modules = len(self.test_modules)
        passed_modules = sum(
            1 for result in basic_results.values() if result == "PASSOU"
        )
        failed_modules = total_modules - passed_modules

        print(f"📊 Módulos de teste: {total_modules}")
        print(f"✅ Sucessos: {passed_modules}")
        print(f"❌ Falhas: {failed_modules}")

        if failed_modules > 0:
            print(f"\n🔍 Módulos com falha:")
            for module, result in basic_results.items():
                if result != "PASSOU":
                    print(f"   • {module}: {result}")

        print(
            f"\n🧪 Testes de cobertura: {'✅ PASSOU' if coverage_passed else '❌ FALHOU'}"
        )
        print(
            f"⚡ Testes de performance: {'✅ PASSOU' if performance_passed else '❌ FALHOU'}"
        )
        print(
            f"🌐 Validação de endpoints: {'✅ PASSOU' if endpoints_passed else '❌ FALHOU'}"
        )

        # Score geral
        total_checks = 4  # básicos, coverage, performance, endpoints
        passed_checks = sum(
            [failed_modules == 0, coverage_passed, performance_passed, endpoints_passed]
        )

        score = (passed_checks / total_checks) * 100

        print(f"\n🎯 SCORE GERAL: {score:.1f}% ({passed_checks}/{total_checks})")

        if score >= 95:
            print("🏆 EXCELENTE - Dashboard pronto para produção!")
        elif score >= 80:
            print("👍 BOM - Dashboard funcional com algumas melhorias")
        elif score >= 60:
            print("⚠️  REGULAR - Dashboard precisa de correções")
        else:
            print("❌ CRÍTICO - Dashboard não está pronto")

        return score >= 80

    def run(self):
        """Executar validação completa"""
        self.print_header("VALIDADOR DE TESTES DO DASHBOARD")
        print("Sistema Aprender - Commits 1-6 completos")

        # 1. Testes básicos
        basic_results = self.run_basic_tests()

        # 2. Cobertura (se solicitada)
        coverage_passed = True
        if self.coverage:
            coverage_passed = self.run_coverage_tests()
        else:
            print("\n📝 Coverage não executado (use --coverage para ativar)")

        # 3. Performance benchmark
        performance_passed = self.run_performance_benchmark()

        # 4. Validação de endpoints
        endpoints_passed = self.validate_api_endpoints()

        # 5. Relatório final
        success = self.generate_final_report(
            basic_results, coverage_passed, performance_passed, endpoints_passed
        )

        return success


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Validador de testes do dashboard")
    parser.add_argument("--verbose", "-v", action="store_true", help="Output verbose")
    parser.add_argument(
        "--coverage", "-c", action="store_true", help="Executar análise de cobertura"
    )

    args = parser.parse_args()

    validator = DashboardTestValidator(verbose=args.verbose, coverage=args.coverage)
    success = validator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
