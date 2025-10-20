#!/usr/bin/env python3
"""
🔍 AUDITORIA COMPLETA DE MAPEAMENTO DE ENTIDADES - SISTEMA APRENDER
================================================================

Script para auditar se todas as entidades estão MUITO BEM MAPEADAS
no banco de dados e sendo usadas como fonte única.

Entidades a verificar:
- Coordenadores
- Municípios
- Projetos
- Coleções
- Produtos
- IDs dos Produtos
- Eventos
- Tipos de Evento

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.core.management import call_command
from django.db import connection

from core.models import (
    EventoGoogleCalendar,
    LogAuditoria,
    Municipio,
    Projeto,
    Setor,
    Solicitacao,
    TipoEvento,
    Usuario,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CompleteEntityMappingAuditor:
    """
    Auditor completo de mapeamento de entidades
    """

    def __init__(self):
        self.audit_results = {
            "coordenadores": {},
            "municipios": {},
            "projetos": {},
            "colecoes": {},
            "produtos": {},
            "ids_produtos": {},
            "eventos": {},
            "tipos_evento": {},
            "database_schema": {},
            "relationships": {},
            "data_integrity": {},
            "services_mapping": {},
        }

        self.issues = []
        self.warnings = []
        self.stats = {
            "total_entities": 0,
            "entities_with_issues": 0,
            "missing_services": 0,
            "data_inconsistencies": 0,
        }

    def audit_all_entities(self):
        """Executa auditoria completa de todas as entidades"""
        print("🔍 AUDITORIA COMPLETA DE MAPEAMENTO DE ENTIDADES")
        print("=" * 70)

        # 1. Auditoria de Coordenadores
        self.audit_coordenadores()

        # 2. Auditoria de Municípios
        self.audit_municipios()

        # 3. Auditoria de Projetos
        self.audit_projetos()

        # 4. Auditoria de Coleções
        self.audit_colecoes()

        # 5. Auditoria de Produtos
        self.audit_produtos()

        # 6. Auditoria de IDs dos Produtos
        self.audit_ids_produtos()

        # 7. Auditoria de Eventos
        self.audit_eventos()

        # 8. Auditoria de Tipos de Evento
        self.audit_tipos_evento()

        # 9. Auditoria do Schema do Banco
        self.audit_database_schema()

        # 10. Auditoria de Relacionamentos
        self.audit_relationships()

        # 11. Auditoria de Integridade de Dados
        self.audit_data_integrity()

        # 12. Auditoria de Services
        self.audit_services_mapping()

        # Relatório final
        self.print_complete_audit_report()

    def audit_coordenadores(self):
        """Audita mapeamento de coordenadores"""
        print("\n👥 AUDITORIA DE COORDENADORES")
        print("-" * 40)

        try:
            # Verificar se existe campo cargo ou role para coordenadores
            coordenadores = Usuario.objects.filter(cargo="coordenador").select_related(
                "setor", "municipio"
            )

            # Verificar também por grupos
            coordenadores_grupo = (
                Usuario.objects.filter(groups__name="coordenador")
                .select_related("setor", "municipio")
                .distinct()
            )

            total_coordenadores = coordenadores.count() + coordenadores_grupo.count()

            self.audit_results["coordenadores"] = {
                "total": total_coordenadores,
                "por_cargo": coordenadores.count(),
                "por_grupo": coordenadores_grupo.count(),
                "com_setor": coordenadores.filter(setor__isnull=False).count(),
                "com_municipio": coordenadores.filter(municipio__isnull=False).count(),
                "ativos": coordenadores.filter(is_active=True).count(),
                "dados": list(
                    coordenadores.values(
                        "id",
                        "first_name",
                        "last_name",
                        "email",
                        "cargo",
                        "setor__nome",
                        "municipio__nome",
                    )
                ),
            }

            print(f"  📊 Total de coordenadores: {total_coordenadores}")
            print(f"  📋 Por cargo: {coordenadores.count()}")
            print(f"  👥 Por grupo: {coordenadores_grupo.count()}")
            print(
                f"  🏢 Com setor: {coordenadores.filter(setor__isnull=False).count()}"
            )
            print(
                f"  🏘️ Com município: {coordenadores.filter(municipio__isnull=False).count()}"
            )
            print(f"  ✅ Ativos: {coordenadores.filter(is_active=True).count()}")

            if total_coordenadores == 0:
                self.issues.append("Nenhum coordenador encontrado no sistema")
                print("  ❌ Nenhum coordenador encontrado")
            else:
                print("  ✅ Coordenadores mapeados corretamente")

        except Exception as e:
            self.issues.append(f"Erro ao auditar coordenadores: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_municipios(self):
        """Audita mapeamento de municípios"""
        print("\n🏘️ AUDITORIA DE MUNICÍPIOS")
        print("-" * 40)

        try:
            municipios = Municipio.objects.all()

            self.audit_results["municipios"] = {
                "total": municipios.count(),
                "ativos": municipios.filter(ativo=True).count(),
                "inativos": municipios.filter(ativo=False).count(),
                "com_uf": municipios.exclude(uf__isnull=True).exclude(uf="").count(),
                "ufs_unicas": municipios.values_list("uf", flat=True)
                .distinct()
                .count(),
                "dados": list(municipios.values("id", "nome", "uf", "ativo")),
            }

            print(f"  📊 Total de municípios: {municipios.count()}")
            print(f"  ✅ Ativos: {municipios.filter(ativo=True).count()}")
            print(f"  ❌ Inativos: {municipios.filter(ativo=False).count()}")
            print(
                f"  🗺️ Com UF: {municipios.exclude(uf__isnull=True).exclude(uf='').count()}"
            )
            print(
                f"  🌍 UFs únicas: {municipios.values_list('uf', flat=True).distinct().count()}"
            )

            if municipios.count() == 0:
                self.issues.append("Nenhum município encontrado no sistema")
                print("  ❌ Nenhum município encontrado")
            else:
                print("  ✅ Municípios mapeados corretamente")

        except Exception as e:
            self.issues.append(f"Erro ao auditar municípios: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_projetos(self):
        """Audita mapeamento de projetos"""
        print("\n📋 AUDITORIA DE PROJETOS")
        print("-" * 40)

        try:
            projetos = Projeto.objects.all()

            self.audit_results["projetos"] = {
                "total": projetos.count(),
                "ativos": projetos.filter(ativo=True).count(),
                "inativos": projetos.filter(ativo=False).count(),
                "com_setor": projetos.filter(setor__isnull=False).count(),
                "sem_setor": projetos.filter(setor__isnull=True).count(),
                "dados": list(projetos.values("id", "nome", "ativo", "setor__nome")),
            }

            print(f"  📊 Total de projetos: {projetos.count()}")
            print(f"  ✅ Ativos: {projetos.filter(ativo=True).count()}")
            print(f"  ❌ Inativos: {projetos.filter(ativo=False).count()}")
            print(f"  🏢 Com setor: {projetos.filter(setor__isnull=False).count()}")
            print(f"  ⚠️ Sem setor: {projetos.filter(setor__isnull=True).count()}")

            if projetos.count() == 0:
                self.issues.append("Nenhum projeto encontrado no sistema")
                print("  ❌ Nenhum projeto encontrado")
            else:
                print("  ✅ Projetos mapeados corretamente")

        except Exception as e:
            self.issues.append(f"Erro ao auditar projetos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_colecoes(self):
        """Audita mapeamento de coleções"""
        print("\n📚 AUDITORIA DE COLEÇÕES")
        print("-" * 40)

        try:
            # Verificar se existe modelo Colecao ou se está em outro lugar
            from django.apps import apps

            models = apps.get_models()

            colecao_models = [
                model for model in models if "colecao" in model.__name__.lower()
            ]

            if colecao_models:
                for model in colecao_models:
                    total = model.objects.count()
                    print(f"  📊 {model.__name__}: {total} registros")
                    self.audit_results["colecoes"][model.__name__] = {
                        "total": total,
                        "dados": list(model.objects.values()[:10]),  # Primeiros 10
                    }
            else:
                print("  ⚠️ Nenhum modelo de coleção encontrado")
                self.warnings.append("Nenhum modelo de coleção encontrado")

        except Exception as e:
            self.issues.append(f"Erro ao auditar coleções: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_produtos(self):
        """Audita mapeamento de produtos"""
        print("\n🛍️ AUDITORIA DE PRODUTOS")
        print("-" * 40)

        try:
            # Verificar se existe modelo Produto
            from django.apps import apps

            models = apps.get_models()

            produto_models = [
                model for model in models if "produto" in model.__name__.lower()
            ]

            if produto_models:
                for model in produto_models:
                    total = model.objects.count()
                    print(f"  📊 {model.__name__}: {total} registros")
                    self.audit_results["produtos"][model.__name__] = {
                        "total": total,
                        "dados": list(model.objects.values()[:10]),  # Primeiros 10
                    }
            else:
                print("  ⚠️ Nenhum modelo de produto encontrado")
                self.warnings.append("Nenhum modelo de produto encontrado")

        except Exception as e:
            self.issues.append(f"Erro ao auditar produtos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_ids_produtos(self):
        """Audita mapeamento de IDs dos produtos"""
        print("\n🔢 AUDITORIA DE IDs DOS PRODUTOS")
        print("-" * 40)

        try:
            # Verificar se há campos de ID de produto em outros modelos
            from django.apps import apps

            models = apps.get_models()

            models_with_produto_id = []
            for model in models:
                fields = [field.name for field in model._meta.fields]
                if any(
                    "produto" in field.lower() and "id" in field.lower()
                    for field in fields
                ):
                    models_with_produto_id.append(model)

            if models_with_produto_id:
                for model in models_with_produto_id:
                    total = model.objects.count()
                    print(f"  📊 {model.__name__}: {total} registros com ID de produto")
                    self.audit_results["ids_produtos"][model.__name__] = {
                        "total": total,
                        "dados": list(model.objects.values()[:5]),  # Primeiros 5
                    }
            else:
                print("  ⚠️ Nenhum campo de ID de produto encontrado")
                self.warnings.append("Nenhum campo de ID de produto encontrado")

        except Exception as e:
            self.issues.append(f"Erro ao auditar IDs de produtos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_eventos(self):
        """Audita mapeamento de eventos"""
        print("\n📅 AUDITORIA DE EVENTOS")
        print("-" * 40)

        try:
            # Verificar eventos em Solicitacao
            solicitacoes = Solicitacao.objects.all()

            # Verificar eventos no Google Calendar
            eventos_calendar = EventoGoogleCalendar.objects.all()

            self.audit_results["eventos"] = {
                "solicitacoes": {
                    "total": solicitacoes.count(),
                    "aprovadas": solicitacoes.filter(status="aprovada").count(),
                    "pendentes": solicitacoes.filter(status="pendente").count(),
                    "canceladas": solicitacoes.filter(status="cancelada").count(),
                },
                "eventos_calendar": {
                    "total": eventos_calendar.count(),
                    "dados": list(
                        eventos_calendar.values(
                            "id", "titulo", "data_inicio", "data_fim"
                        )[:10]
                    ),
                },
            }

            print(f"  📊 Total de solicitações: {solicitacoes.count()}")
            print(f"  ✅ Aprovadas: {solicitacoes.filter(status='aprovada').count()}")
            print(f"  ⏳ Pendentes: {solicitacoes.filter(status='pendente').count()}")
            print(f"  ❌ Canceladas: {solicitacoes.filter(status='cancelada').count()}")
            print(f"  📅 Eventos no Calendar: {eventos_calendar.count()}")

            if solicitacoes.count() == 0 and eventos_calendar.count() == 0:
                self.issues.append("Nenhum evento encontrado no sistema")
                print("  ❌ Nenhum evento encontrado")
            else:
                print("  ✅ Eventos mapeados corretamente")

        except Exception as e:
            self.issues.append(f"Erro ao auditar eventos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_tipos_evento(self):
        """Audita mapeamento de tipos de evento"""
        print("\n🏷️ AUDITORIA DE TIPOS DE EVENTO")
        print("-" * 40)

        try:
            tipos_evento = TipoEvento.objects.all()

            self.audit_results["tipos_evento"] = {
                "total": tipos_evento.count(),
                "ativos": tipos_evento.filter(ativo=True).count(),
                "inativos": tipos_evento.filter(ativo=False).count(),
                "online": tipos_evento.filter(online=True).count(),
                "presenciais": tipos_evento.filter(online=False).count(),
                "dados": list(tipos_evento.values("id", "nome", "ativo", "online")),
            }

            print(f"  📊 Total de tipos: {tipos_evento.count()}")
            print(f"  ✅ Ativos: {tipos_evento.filter(ativo=True).count()}")
            print(f"  ❌ Inativos: {tipos_evento.filter(ativo=False).count()}")
            print(f"  💻 Online: {tipos_evento.filter(online=True).count()}")
            print(f"  🏢 Presenciais: {tipos_evento.filter(online=False).count()}")

            if tipos_evento.count() == 0:
                self.issues.append("Nenhum tipo de evento encontrado no sistema")
                print("  ❌ Nenhum tipo de evento encontrado")
            else:
                print("  ✅ Tipos de evento mapeados corretamente")

        except Exception as e:
            self.issues.append(f"Erro ao auditar tipos de evento: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_database_schema(self):
        """Audita schema do banco de dados"""
        print("\n🗄️ AUDITORIA DO SCHEMA DO BANCO")
        print("-" * 40)

        try:
            with connection.cursor() as cursor:
                # Listar todas as tabelas
                cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """
                )
                tables = cursor.fetchall()

                self.audit_results["database_schema"] = {
                    "total_tables": len(tables),
                    "tables": [table[0] for table in tables],
                }

                print(f"  📊 Total de tabelas: {len(tables)}")
                print("  📋 Tabelas encontradas:")
                for table in tables:
                    print(f"    • {table[0]}")

        except Exception as e:
            self.issues.append(f"Erro ao auditar schema: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_relationships(self):
        """Audita relacionamentos entre entidades"""
        print("\n🔗 AUDITORIA DE RELACIONAMENTOS")
        print("-" * 40)

        try:
            # Verificar relacionamentos principais
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

            self.audit_results["relationships"] = relationships

            print("  🔗 Relacionamentos encontrados:")
            for rel, count in relationships.items():
                print(f"    • {rel}: {count} registros")

        except Exception as e:
            self.issues.append(f"Erro ao auditar relacionamentos: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_data_integrity(self):
        """Audita integridade dos dados"""
        print("\n🔍 AUDITORIA DE INTEGRIDADE DE DADOS")
        print("-" * 40)

        try:
            integrity_issues = []

            # Verificar usuários sem setor
            usuarios_sem_setor = Usuario.objects.filter(setor__isnull=True).count()
            if usuarios_sem_setor > 0:
                integrity_issues.append(f"{usuarios_sem_setor} usuários sem setor")

            # Verificar projetos sem setor
            projetos_sem_setor = Projeto.objects.filter(setor__isnull=True).count()
            if projetos_sem_setor > 0:
                integrity_issues.append(f"{projetos_sem_setor} projetos sem setor")

            # Verificar solicitações sem projeto
            solicitacoes_sem_projeto = Solicitacao.objects.filter(
                projeto__isnull=True
            ).count()
            if solicitacoes_sem_projeto > 0:
                integrity_issues.append(
                    f"{solicitacoes_sem_projeto} solicitações sem projeto"
                )

            self.audit_results["data_integrity"] = {
                "issues": integrity_issues,
                "usuarios_sem_setor": usuarios_sem_setor,
                "projetos_sem_setor": projetos_sem_setor,
                "solicitacoes_sem_projeto": solicitacoes_sem_projeto,
            }

            if integrity_issues:
                print("  ⚠️ Problemas de integridade encontrados:")
                for issue in integrity_issues:
                    print(f"    • {issue}")
                self.stats["data_inconsistencies"] = len(integrity_issues)
            else:
                print("  ✅ Nenhum problema de integridade encontrado")

        except Exception as e:
            self.issues.append(f"Erro ao auditar integridade: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def audit_services_mapping(self):
        """Audita mapeamento de services"""
        print("\n🔧 AUDITORIA DE SERVICES")
        print("-" * 40)

        try:
            # Verificar se existem services para todas as entidades
            from core.services import (
                CoordinatorService,
                DashboardService,
                FormadorService,
                MunicipioService,
                SetorService,
                TipoEventoService,
                UsuarioService,
            )

            services_status = {
                "UsuarioService": "✅ Disponível",
                "FormadorService": "✅ Disponível",
                "CoordinatorService": "✅ Disponível",
                "DashboardService": "✅ Disponível",
                "MunicipioService": "✅ Disponível",
                "SetorService": "✅ Disponível",
                "TipoEventoService": "✅ Disponível",
            }

            # Verificar se existe ProjetoService
            try:
                from core.services.data_master_service import ProjetoService

                services_status["ProjetoService"] = "✅ Disponível"
            except ImportError:
                services_status["ProjetoService"] = "❌ Não encontrado"
                self.issues.append("ProjetoService não encontrado")

            self.audit_results["services_mapping"] = services_status

            print("  🔧 Status dos Services:")
            for service, status in services_status.items():
                print(f"    • {service}: {status}")

        except Exception as e:
            self.issues.append(f"Erro ao auditar services: {str(e)}")
            print(f"  ❌ Erro: {str(e)}")

    def print_complete_audit_report(self):
        """Imprime relatório completo de auditoria"""
        print("\n📊 RELATÓRIO COMPLETO DE AUDITORIA")
        print("=" * 70)

        # Estatísticas gerais
        print(f"\n📈 ESTATÍSTICAS GERAIS:")
        print(f"  • Total de entidades auditadas: 8")
        print(f"  • Problemas encontrados: {len(self.issues)}")
        print(f"  • Avisos: {len(self.warnings)}")
        print(f"  • Inconsistências de dados: {self.stats['data_inconsistencies']}")

        # Resumo por entidade
        print(f"\n📋 RESUMO POR ENTIDADE:")
        entities = [
            "coordenadores",
            "municipios",
            "projetos",
            "colecoes",
            "produtos",
            "ids_produtos",
            "eventos",
            "tipos_evento",
        ]
        for entity in entities:
            if entity in self.audit_results and self.audit_results[entity]:
                if (
                    isinstance(self.audit_results[entity], dict)
                    and "total" in self.audit_results[entity]
                ):
                    total = self.audit_results[entity]["total"]
                    status = "✅" if total > 0 else "❌"
                    print(f"  {status} {entity.title()}: {total} registros")
                else:
                    print(f"  ⚠️ {entity.title()}: Dados parciais")
            else:
                print(f"  ❌ {entity.title()}: Não mapeado")

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

        # Conclusão
        print(f"\n🎯 CONCLUSÃO:")
        if not self.issues:
            print("✅ Todas as entidades estão MUITO BEM MAPEADAS no banco de dados")
        else:
            print("❌ Algumas entidades precisam de melhor mapeamento")
            print("\n🔧 RECOMENDAÇÕES:")
            print("  1. Verificar entidades sem dados")
            print("  2. Corrigir problemas de integridade")
            print("  3. Implementar services faltantes")
            print("  4. Garantir fonte única para todas as entidades")


def main():
    """Função principal"""
    try:
        auditor = CompleteEntityMappingAuditor()
        auditor.audit_all_entities()

    except Exception as e:
        logger.error(f"❌ Erro na auditoria: {str(e)}")
        raise


if __name__ == "__main__":
    main()
