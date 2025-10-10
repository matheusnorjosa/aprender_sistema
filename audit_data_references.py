#!/usr/bin/env python3
"""
🔍 AUDITORIA DE REFERÊNCIAS DE DADOS - SISTEMA APRENDER
======================================================

Script para auditar todas as referências aos dados importados
e verificar se estão uniformes e adequadas.

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import sys

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.db import connection

from core.models import Municipio, Projeto, Setor, TipoEvento, Usuario

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataReferencesAuditor:
    """
    Auditor de referências de dados
    """

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.stats = {}

    def audit_all(self):
        """Executa auditoria completa"""
        print("🔍 AUDITORIA COMPLETA DE REFERÊNCIAS DE DADOS")
        print("=" * 60)

        self.audit_users()
        self.audit_sectors()
        self.audit_municipalities()
        self.audit_projects()
        self.audit_event_types()
        self.audit_relationships()
        self.audit_data_consistency()

        self.print_audit_report()

    def audit_users(self):
        """Audita usuários importados"""
        print("\n👥 AUDITORIA DE USUÁRIOS")
        print("-" * 30)

        users = Usuario.objects.all()
        self.stats["total_users"] = users.count()

        print(f"Total de usuários: {self.stats['total_users']}")

        # Verificar usuários sem CPF
        users_without_cpf = users.filter(cpf__isnull=True).count()
        if users_without_cpf > 0:
            self.warnings.append(f"{users_without_cpf} usuários sem CPF")
            print(f"⚠️ Usuários sem CPF: {users_without_cpf}")

        # Verificar usuários sem email
        users_without_email = users.filter(email="").count()
        if users_without_email > 0:
            self.warnings.append(f"{users_without_email} usuários sem email")
            print(f"⚠️ Usuários sem email: {users_without_email}")

        # Verificar usuários sem setor
        users_without_sector = users.filter(setor__isnull=True).count()
        if users_without_sector > 0:
            self.warnings.append(f"{users_without_sector} usuários sem setor")
            print(f"⚠️ Usuários sem setor: {users_without_sector}")

        # Listar usuários importados
        print("\n📋 USUÁRIOS IMPORTADOS:")
        for user in users:
            print(f"  • {user.first_name} {user.last_name}")
            print(f"    CPF: {user.cpf or 'N/A'}")
            print(f"    Email: {user.email or 'N/A'}")
            print(f"    Setor: {user.setor or 'N/A'}")
            print(f"    Ativo: {user.is_active}")
            print()

    def audit_sectors(self):
        """Audita setores"""
        print("\n🏢 AUDITORIA DE SETORES")
        print("-" * 30)

        sectors = Setor.objects.all()
        self.stats["total_sectors"] = sectors.count()

        print(f"Total de setores: {self.stats['total_sectors']}")

        # Verificar setores sem sigla
        sectors_without_sigla = sectors.filter(sigla="").count()
        if sectors_without_sigla > 0:
            self.issues.append(f"{sectors_without_sigla} setores sem sigla")
            print(f"❌ Setores sem sigla: {sectors_without_sigla}")

        # Listar setores
        print("\n📋 SETORES CRIADOS:")
        for sector in sectors:
            print(f"  • {sector.nome}")
            print(f"    Sigla: {sector.sigla}")
            print(f"    Superintendência: {sector.vinculado_superintendencia}")
            print(f"    Ativo: {sector.ativo}")
            print()

    def audit_municipalities(self):
        """Audita municípios"""
        print("\n🏘️ AUDITORIA DE MUNICÍPIOS")
        print("-" * 30)

        municipalities = Municipio.objects.all()
        self.stats["total_municipalities"] = municipalities.count()

        print(f"Total de municípios: {self.stats['total_municipalities']}")

        # Listar municípios
        print("\n📋 MUNICÍPIOS CRIADOS:")
        for municipality in municipalities:
            print(f"  • {municipality.nome}/{municipality.uf}")
            print(f"    Ativo: {municipality.ativo}")
            print()

    def audit_projects(self):
        """Audita projetos"""
        print("\n📋 AUDITORIA DE PROJETOS")
        print("-" * 30)

        projects = Projeto.objects.all()
        self.stats["total_projects"] = projects.count()

        print(f"Total de projetos: {self.stats['total_projects']}")

        # Verificar projetos sem setor
        projects_without_sector = projects.filter(setor__isnull=True).count()
        if projects_without_sector > 0:
            self.warnings.append(f"{projects_without_sector} projetos sem setor")
            print(f"⚠️ Projetos sem setor: {projects_without_sector}")

        # Listar projetos
        print("\n📋 PROJETOS CRIADOS:")
        for project in projects:
            print(f"  • {project.nome}")
            print(f"    Setor: {project.setor or 'N/A'}")
            print(f"    Ativo: {project.ativo}")
            print()

    def audit_event_types(self):
        """Audita tipos de evento"""
        print("\n📅 AUDITORIA DE TIPOS DE EVENTO")
        print("-" * 30)

        event_types = TipoEvento.objects.all()
        self.stats["total_event_types"] = event_types.count()

        print(f"Total de tipos de evento: {self.stats['total_event_types']}")

        # Listar tipos de evento
        print("\n📋 TIPOS DE EVENTO CRIADOS:")
        for event_type in event_types:
            print(f"  • {event_type.nome}")
            print(f"    Online: {event_type.online}")
            print(f"    Ativo: {event_type.ativo}")
            print()

    def audit_relationships(self):
        """Audita relacionamentos entre entidades"""
        print("\n🔗 AUDITORIA DE RELACIONAMENTOS")
        print("-" * 30)

        # Verificar usuários com setores válidos
        users_with_valid_sectors = Usuario.objects.filter(setor__isnull=False).count()
        print(f"Usuários com setor válido: {users_with_valid_sectors}")

        # Verificar projetos com setores válidos
        projects_with_valid_sectors = Projeto.objects.filter(
            setor__isnull=False
        ).count()
        print(f"Projetos com setor válido: {projects_with_valid_sectors}")

        # Verificar consistência de setores
        user_sectors = set(
            Usuario.objects.filter(setor__isnull=False).values_list(
                "setor__nome", flat=True
            )
        )
        project_sectors = set(
            Projeto.objects.filter(setor__isnull=False).values_list(
                "setor__nome", flat=True
            )
        )

        if user_sectors != project_sectors:
            self.warnings.append("Inconsistência entre setores de usuários e projetos")
            print("⚠️ Inconsistência entre setores de usuários e projetos")
            print(f"  Setores de usuários: {user_sectors}")
            print(f"  Setores de projetos: {project_sectors}")

    def audit_data_consistency(self):
        """Audita consistência dos dados"""
        print("\n✅ AUDITORIA DE CONSISTÊNCIA")
        print("-" * 30)

        # Verificar CPFs duplicados
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT cpf, COUNT(*)
                FROM core_usuario
                WHERE cpf IS NOT NULL AND cpf != ''
                GROUP BY cpf
                HAVING COUNT(*) > 1
            """
            )
            duplicate_cpfs = cursor.fetchall()

            if duplicate_cpfs:
                self.issues.append(
                    f"CPFs duplicados encontrados: {len(duplicate_cpfs)}"
                )
                print(f"❌ CPFs duplicados: {len(duplicate_cpfs)}")
                for cpf, count in duplicate_cpfs:
                    print(f"  CPF {cpf}: {count} ocorrências")

        # Verificar emails duplicados
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT email, COUNT(*)
                FROM core_usuario
                WHERE email IS NOT NULL AND email != ''
                GROUP BY email
                HAVING COUNT(*) > 1
            """
            )
            duplicate_emails = cursor.fetchall()

            if duplicate_emails:
                self.issues.append(
                    f"Emails duplicados encontrados: {len(duplicate_emails)}"
                )
                print(f"❌ Emails duplicados: {len(duplicate_emails)}")
                for email, count in duplicate_emails:
                    print(f"  Email {email}: {count} ocorrências")

    def print_audit_report(self):
        """Imprime relatório de auditoria"""
        print("\n📊 RELATÓRIO DE AUDITORIA")
        print("=" * 60)

        print(f"\n📈 ESTATÍSTICAS:")
        for key, value in self.stats.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")

        if self.issues:
            print(f"\n❌ PROBLEMAS ENCONTRADOS ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  • {issue}")
        else:
            print(f"\n✅ NENHUM PROBLEMA CRÍTICO ENCONTRADO")

        if self.warnings:
            print(f"\n⚠️ AVISOS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        else:
            print(f"\n✅ NENHUM AVISO")

        print(f"\n🎯 CONCLUSÃO:")
        if not self.issues:
            print("✅ Sistema com referências adequadas e uniformes")
        else:
            print("❌ Sistema precisa de correções nas referências")


def main():
    """Função principal"""
    try:
        auditor = DataReferencesAuditor()
        auditor.audit_all()

    except Exception as e:
        logger.error(f"❌ Erro na auditoria: {str(e)}")
        raise


if __name__ == "__main__":
    main()
