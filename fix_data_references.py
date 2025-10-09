#!/usr/bin/env python3
"""
🔧 CORREÇÃO DE REFERÊNCIAS DE DADOS - SISTEMA APRENDER
=====================================================

Script para corrigir problemas identificados na auditoria
e garantir que todas as referências estejam uniformes.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import logging

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.db import transaction
from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataReferencesFixer:
    """
    Corretor de referências de dados
    """

    def __init__(self):
        self.fixes_applied = []
        self.errors = []

    def fix_all_issues(self):
        """Aplica todas as correções identificadas"""
        print("🔧 CORREÇÃO DE REFERÊNCIAS DE DADOS")
        print("=" * 50)

        self.fix_projects_sectors()
        self.fix_user_sectors()
        self.fix_duplicate_data()
        self.fix_missing_data()

        self.print_fix_report()

    def fix_projects_sectors(self):
        """Corrige projetos sem setor"""
        print("\n📋 CORRIGINDO PROJETOS SEM SETOR")
        print("-" * 40)

        try:
            with transaction.atomic():
                # Mapear projetos para setores
                project_sector_mapping = {
                    "ACerta": "ACerta",
                    "Brincando": "Outros",
                    "Vidas": "Outros",
                    "Superintendência": "Superintendência",
                    "Outros": "Outros",
                }

                for project_name, sector_name in project_sector_mapping.items():
                    try:
                        project = Projeto.objects.get(nome=project_name)
                        sector = Setor.objects.get(nome=sector_name)

                        project.setor = sector
                        project.save()

                        self.fixes_applied.append(
                            f"Projeto '{project_name}' vinculado ao setor '{sector_name}'"
                        )
                        print(f"  ✅ Projeto '{project_name}' → Setor '{sector_name}'")

                    except (Projeto.DoesNotExist, Setor.DoesNotExist) as e:
                        self.errors.append(
                            f"Erro ao vincular projeto {project_name}: {str(e)}"
                        )
                        print(f"  ❌ Erro: {str(e)}")

        except Exception as e:
            self.errors.append(f"Erro na transação de projetos: {str(e)}")
            print(f"  ❌ Erro na transação: {str(e)}")

    def fix_user_sectors(self):
        """Corrige usuários sem setor"""
        print("\n👥 CORRIGINDO USUÁRIOS SEM SETOR")
        print("-" * 40)

        try:
            with transaction.atomic():
                # Usuários sem setor
                users_without_sector = Usuario.objects.filter(setor__isnull=True)

                for user in users_without_sector:
                    # Tentar inferir setor baseado no cargo ou email
                    if (
                        "superintendência" in user.email.lower()
                        or "superintendencia" in user.email.lower()
                    ):
                        sector_name = "Superintendência"
                    elif "acerta" in user.email.lower():
                        sector_name = "ACerta"
                    else:
                        sector_name = "Outros"  # Setor padrão

                    try:
                        sector = Setor.objects.get(nome=sector_name)
                        user.setor = sector
                        user.save()

                        self.fixes_applied.append(
                            f"Usuário '{user.first_name} {user.last_name}' → Setor '{sector_name}'"
                        )
                        print(
                            f"  ✅ {user.first_name} {user.last_name} → Setor '{sector_name}'"
                        )

                    except Setor.DoesNotExist:
                        self.errors.append(
                            f"Setor '{sector_name}' não encontrado para usuário {user.first_name}"
                        )
                        print(f"  ❌ Setor '{sector_name}' não encontrado")

        except Exception as e:
            self.errors.append(f"Erro na transação de usuários: {str(e)}")
            print(f"  ❌ Erro na transação: {str(e)}")

    def fix_duplicate_data(self):
        """Corrige dados duplicados"""
        print("\n🔄 CORRIGINDO DADOS DUPLICADOS")
        print("-" * 40)

        # Verificar CPFs duplicados
        from django.db import connection

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
                print(f"  ⚠️ {len(duplicate_cpfs)} CPFs duplicados encontrados")
                for cpf, count in duplicate_cpfs:
                    print(f"    CPF {cpf}: {count} ocorrências")
                    # Manter apenas o primeiro, marcar os outros como inativos
                    users_with_cpf = Usuario.objects.filter(cpf=cpf).order_by("id")
                    if users_with_cpf.count() > 1:
                        for i, user in enumerate(users_with_cpf[1:], 1):
                            user.is_active = False
                            user.save()
                            self.fixes_applied.append(
                                f"Usuário duplicado {user.first_name} marcado como inativo"
                            )
                            print(
                                f"    ✅ Usuário duplicado {user.first_name} marcado como inativo"
                            )
            else:
                print("  ✅ Nenhum CPF duplicado encontrado")

    def fix_missing_data(self):
        """Corrige dados faltantes"""
        print("\n📝 CORRIGINDO DADOS FALTANTES")
        print("-" * 40)

        # Usuários sem CPF
        users_without_cpf = Usuario.objects.filter(cpf__isnull=True)
        if users_without_cpf.exists():
            print(f"  ⚠️ {users_without_cpf.count()} usuários sem CPF")
            for user in users_without_cpf:
                if (
                    user.username
                    and user.username.isdigit()
                    and len(user.username) == 11
                ):
                    # Username é um CPF válido
                    user.cpf = user.username
                    user.save()
                    self.fixes_applied.append(
                        f"CPF {user.username} adicionado ao usuário {user.first_name}"
                    )
                    print(
                        f"    ✅ CPF {user.username} adicionado ao usuário {user.first_name}"
                    )
                else:
                    print(f"    ⚠️ Usuário {user.first_name} sem CPF válido")
        else:
            print("  ✅ Todos os usuários têm CPF")

    def print_fix_report(self):
        """Imprime relatório de correções"""
        print("\n📊 RELATÓRIO DE CORREÇÕES")
        print("=" * 50)

        print(f"\n✅ CORREÇÕES APLICADAS ({len(self.fixes_applied)}):")
        for fix in self.fixes_applied:
            print(f"  • {fix}")

        if self.errors:
            print(f"\n❌ ERROS ENCONTRADOS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        else:
            print(f"\n✅ NENHUM ERRO ENCONTRADO")

        print(f"\n🎯 CONCLUSÃO:")
        if not self.errors:
            print("✅ Todas as referências foram corrigidas com sucesso")
        else:
            print("❌ Algumas correções falharam - verifique os erros")


def main():
    """Função principal"""
    try:
        fixer = DataReferencesFixer()
        fixer.fix_all_issues()

    except Exception as e:
        logger.error(f"❌ Erro nas correções: {str(e)}")
        raise


if __name__ == "__main__":
    main()
