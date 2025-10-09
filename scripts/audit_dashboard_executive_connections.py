#!/usr/bin/env python3
"""
🔍 AUDITORIA DE CONEXÕES DO DASHBOARD EXECUTIVO - SISTEMA APRENDER
===============================================================

Script para verificar e ajustar todas as referências e conexões
de dados do dashboard executivo e da plataforma.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Set, Any

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.db import connection
from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento, Solicitacao
from core.services import (
    UsuarioService,
    FormadorService,
    CoordinatorService,
    DashboardService,
    MunicipioService,
    SetorService,
    TipoEventoService,
)
from core.services.data_master_service import ProjetoService

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DashboardExecutiveAuditor:
    """
    Auditor de conexões do dashboard executivo
    """

    def __init__(self):
        self.audit_results = {
            "dashboard_service": {},
            "data_connections": {},
            "api_endpoints": {},
            "templates": {},
            "views": {},
            "issues": [],
            "recommendations": [],
        }

        self.issues = []
        self.warnings = []
        self.stats = {
            "total_connections": 0,
            "working_connections": 0,
            "broken_connections": 0,
            "missing_methods": 0,
        }

    def audit_all_connections(self):
        """Executa auditoria completa de conexões"""
        print("🔍 AUDITORIA DE CONEXÕES DO DASHBOARD EXECUTIVO")
        print("=" * 70)

        # 1. Auditoria do DashboardService
        self.audit_dashboard_service()

        # 2. Auditoria de conexões de dados
        self.audit_data_connections()

        # 3. Auditoria de views do dashboard
        self.audit_dashboard_views()

        # 4. Auditoria de templates
        self.audit_dashboard_templates()

        # 5. Auditoria de APIs
        self.audit_dashboard_apis()

        # 6. Teste de funcionalidade
        self.test_dashboard_functionality()

        # 7. Relatório final
        self.print_audit_report()

    def audit_dashboard_service(self):
        """Audita DashboardService"""
        print("\n🔧 AUDITORIA DO DASHBOARD SERVICE")
        print("-" * 50)

        try:
            # Verificar métodos disponíveis
            methods_to_check = [
                "get_estatisticas_gerais",
                "get_dashboard_stats",
                "get_formadores_por_area",
                "get_coordenadores_por_municipio",
                "get_projetos_por_setor",
                "get_solicitacoes_por_status",
                "get_eventos_por_tipo",
            ]

            working_methods = []
            broken_methods = []

            for method_name in methods_to_check:
                try:
                    method = getattr(DashboardService, method_name)
                    if callable(method):
                        # Testar execução
                        result = method()
                        working_methods.append(method_name)
                        print(f"  ✅ {method_name}: Funcionando")
                        self.audit_results["dashboard_service"][method_name] = {
                            "status": "working",
                            "result_type": type(result).__name__,
                            "result_count": (
                                len(result) if hasattr(result, "__len__") else "N/A"
                            ),
                        }
                    else:
                        broken_methods.append(method_name)
                        print(f"  ❌ {method_name}: Não é callable")
                except Exception as e:
                    broken_methods.append(method_name)
                    print(f"  ❌ {method_name}: Erro - {str(e)}")
                    self.issues.append(f"DashboardService.{method_name}: {str(e)}")

            self.stats["working_connections"] += len(working_methods)
            self.stats["broken_connections"] += len(broken_methods)
            self.stats["missing_methods"] = len(broken_methods)

            print(f"  📊 Métodos funcionando: {len(working_methods)}")
            print(f"  📊 Métodos com problemas: {len(broken_methods)}")

        except Exception as e:
            self.issues.append(f"Erro ao auditar DashboardService: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_data_connections(self):
        """Audita conexões de dados"""
        print("\n📊 AUDITORIA DE CONEXÕES DE DADOS")
        print("-" * 50)

        try:
            # Verificar conexões básicas
            connections = {
                "usuarios": UsuarioService.ativos().count(),
                "formadores": FormadorService.get_formadores_queryset().count(),
                "coordenadores": CoordinatorService.get_coordenadores_queryset().count(),
                "municipios": MunicipioService.ativos().count(),
                "projetos": ProjetoService.ativos().count(),
                "tipos_evento": TipoEventoService.ativos().count(),
                "setores": SetorService.ativos().count(),
            }

            self.audit_results["data_connections"] = connections

            print("  📈 Conexões de dados:")
            for service, count in connections.items():
                status = "✅" if count > 0 else "❌"
                print(f"    {status} {service}: {count} registros")
                if count > 0:
                    self.stats["working_connections"] += 1
                else:
                    self.stats["broken_connections"] += 1
                    self.issues.append(f"Service {service} retorna 0 registros")

            # Verificar relacionamentos
            self.audit_relationships()

        except Exception as e:
            self.issues.append(f"Erro ao auditar conexões de dados: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_relationships(self):
        """Audita relacionamentos entre entidades"""
        print("\n🔗 AUDITORIA DE RELACIONAMENTOS")
        print("-" * 40)

        try:
            relationships = {
                "usuario_setor": Usuario.objects.filter(setor__isnull=False).count(),
                "usuario_municipio": Usuario.objects.filter(
                    municipio__isnull=False
                ).count(),
                "projeto_setor": Projeto.objects.filter(setor__isnull=False).count(),
                "solicitacao_projeto": Solicitacao.objects.filter(
                    projeto__isnull=False
                ).count(),
                "solicitacao_municipio": Solicitacao.objects.filter(
                    municipio__isnull=False
                ).count(),
                "solicitacao_tipo_evento": Solicitacao.objects.filter(
                    tipo_evento__isnull=False
                ).count(),
            }

            print("  🔗 Relacionamentos:")
            for rel, count in relationships.items():
                status = "✅" if count > 0 else "⚠️"
                print(f"    {status} {rel}: {count} registros")
                if count == 0:
                    self.warnings.append(f"Relacionamento {rel} sem dados")

        except Exception as e:
            self.issues.append(f"Erro ao auditar relacionamentos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_dashboard_views(self):
        """Audita views do dashboard"""
        print("\n📱 AUDITORIA DE VIEWS DO DASHBOARD")
        print("-" * 50)

        try:
            # Verificar views do dashboard
            views_to_check = [
                "core.views.diretoria_views.DiretoriaExecutiveDashboardView",
                "core.views.diretoria_views.DashboardStatsAPIView",
                "core.views.diretoria_views.DashboardChartsAPIView",
                "core.views.diretoria_views.DashboardCursosAPIView",
                "core.views.diretoria_views.DashboardCoordenadoresAPIView",
            ]

            working_views = []
            broken_views = []

            for view_path in views_to_check:
                try:
                    module_path, class_name = view_path.rsplit(".", 1)
                    module = __import__(module_path, fromlist=[class_name])
                    view_class = getattr(module, class_name)
                    working_views.append(view_path)
                    print(f"  ✅ {class_name}: Disponível")
                except Exception as e:
                    broken_views.append(view_path)
                    print(f"  ❌ {class_path}: Erro - {str(e)}")
                    self.issues.append(f"View {view_path}: {str(e)}")

            self.audit_results["views"] = {
                "working": working_views,
                "broken": broken_views,
            }

            print(f"  📊 Views funcionando: {len(working_views)}")
            print(f"  📊 Views com problemas: {len(broken_views)}")

        except Exception as e:
            self.issues.append(f"Erro ao auditar views: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_dashboard_templates(self):
        """Audita templates do dashboard"""
        print("\n🎨 AUDITORIA DE TEMPLATES DO DASHBOARD")
        print("-" * 50)

        try:
            # Verificar templates do dashboard
            templates_to_check = [
                "core/diretoria/dashboard_executive.html",
                "core/diretoria/dashboard_working_original.html",
                "core/diretoria/relatorios.html",
                "core/diretoria/debug_dashboard.html",
            ]

            working_templates = []
            missing_templates = []

            for template_path in templates_to_check:
                template_file = Path(f"templates/{template_path}")
                if template_file.exists():
                    working_templates.append(template_path)
                    print(f"  ✅ {template_path}: Existe")
                else:
                    missing_templates.append(template_path)
                    print(f"  ❌ {template_path}: Não encontrado")
                    self.issues.append(f"Template {template_path} não encontrado")

            self.audit_results["templates"] = {
                "working": working_templates,
                "missing": missing_templates,
            }

            print(f"  📊 Templates funcionando: {len(working_templates)}")
            print(f"  📊 Templates faltando: {len(missing_templates)}")

        except Exception as e:
            self.issues.append(f"Erro ao auditar templates: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_dashboard_apis(self):
        """Audita APIs do dashboard"""
        print("\n🌐 AUDITORIA DE APIs DO DASHBOARD")
        print("-" * 50)

        try:
            # Verificar endpoints de API
            api_endpoints = [
                "/diretoria/api/estatisticas/",
                "/diretoria/api/metrics/",
                "/diretoria/api/charts/",
                "/diretoria/api/cursos/",
                "/diretoria/api/coordenadores/",
            ]

            working_apis = []
            broken_apis = []

            for endpoint in api_endpoints:
                # Verificar se a URL está configurada
                try:
                    from django.urls import reverse

                    reverse(f'core:{endpoint.strip("/").replace("/", "_")}')
                    working_apis.append(endpoint)
                    print(f"  ✅ {endpoint}: Configurado")
                except Exception as e:
                    broken_apis.append(endpoint)
                    print(f"  ❌ {endpoint}: Erro - {str(e)}")
                    self.issues.append(f"API {endpoint}: {str(e)}")

            self.audit_results["api_endpoints"] = {
                "working": working_apis,
                "broken": broken_apis,
            }

            print(f"  📊 APIs funcionando: {len(working_apis)}")
            print(f"  📊 APIs com problemas: {len(broken_apis)}")

        except Exception as e:
            self.issues.append(f"Erro ao auditar APIs: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def test_dashboard_functionality(self):
        """Testa funcionalidade do dashboard"""
        print("\n🧪 TESTE DE FUNCIONALIDADE DO DASHBOARD")
        print("-" * 50)

        try:
            # Testar DashboardService
            print("  🔧 Testando DashboardService:")

            # Testar get_dashboard_stats
            try:
                stats = DashboardService.get_dashboard_stats()
                print(f"    ✅ get_dashboard_stats: {len(stats)} estatísticas")
            except Exception as e:
                print(f"    ❌ get_dashboard_stats: {str(e)}")
                self.issues.append(f"get_dashboard_stats: {str(e)}")

            # Testar get_formadores_por_area
            try:
                formadores_area = DashboardService.get_formadores_por_area()
                print(f"    ✅ get_formadores_por_area: {len(formadores_area)} áreas")
            except Exception as e:
                print(f"    ❌ get_formadores_por_area: {str(e)}")
                self.issues.append(f"get_formadores_por_area: {str(e)}")

            # Testar get_coordenadores_por_municipio
            try:
                coords_municipio = DashboardService.get_coordenadores_por_municipio()
                print(
                    f"    ✅ get_coordenadores_por_municipio: {len(coords_municipio)} registros"
                )
            except Exception as e:
                print(f"    ❌ get_coordenadores_por_municipio: {str(e)}")
                self.issues.append(f"get_coordenadores_por_municipio: {str(e)}")

        except Exception as e:
            self.issues.append(f"Erro ao testar funcionalidade: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def print_audit_report(self):
        """Imprime relatório de auditoria"""
        print("\n📊 RELATÓRIO DE AUDITORIA")
        print("=" * 70)

        # Estatísticas gerais
        total_connections = (
            self.stats["working_connections"] + self.stats["broken_connections"]
        )
        success_rate = (
            (self.stats["working_connections"] / total_connections * 100)
            if total_connections > 0
            else 0
        )

        print(f"\n📈 ESTATÍSTICAS GERAIS:")
        print(f"  • Total de conexões: {total_connections}")
        print(f"  • Conexões funcionando: {self.stats['working_connections']}")
        print(f"  • Conexões com problemas: {self.stats['broken_connections']}")
        print(f"  • Taxa de sucesso: {success_rate:.1f}%")
        print(f"  • Métodos faltantes: {self.stats['missing_methods']}")

        # Problemas encontrados
        if self.issues:
            print(f"\n❌ PROBLEMAS ENCONTRADOS ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  • {issue}")
        else:
            print(f"\n✅ NENHUM PROBLEMA ENCONTRADO")

        # Avisos
        if self.warnings:
            print(f"\n⚠️ AVISOS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        else:
            print(f"\n✅ NENHUM AVISO")

        # Recomendações
        print(f"\n🔧 RECOMENDAÇÕES:")
        if self.stats["broken_connections"] > 0:
            print("  1. Corrigir conexões quebradas identificadas")
        if self.stats["missing_methods"] > 0:
            print("  2. Implementar métodos faltantes no DashboardService")
        if len(self.issues) > 0:
            print("  3. Resolver problemas de views e templates")
        print("  4. Testar dashboard executivo após correções")
        print("  5. Implementar monitoramento de conexões")

        # Conclusão
        print(f"\n🎯 CONCLUSÃO:")
        if success_rate >= 90:
            print("✅ Dashboard executivo funcionando bem")
        elif success_rate >= 70:
            print("⚠️ Dashboard executivo com alguns problemas")
        else:
            print("❌ Dashboard executivo precisa de correções significativas")


def main():
    """Função principal"""
    try:
        auditor = DashboardExecutiveAuditor()
        auditor.audit_all_connections()

    except Exception as e:
        logger.error(f"❌ Erro na auditoria: {str(e)}")
        raise


if __name__ == "__main__":
    main()
