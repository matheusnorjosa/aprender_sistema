#!/usr/bin/env python3
"""
🔍 INVESTIGAÇÃO DE DADOS FALSOS/EXEMPLO - SISTEMA APRENDER
=======================================================

Script para identificar e remover dados de exemplo/criados,
garantindo que apenas dados reais das planilhas sejam exibidos.

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

from django.db import transaction

from core.models import Municipio, Projeto, Setor, Solicitacao, TipoEvento, Usuario

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FakeDataInvestigator:
    """
    Investigador de dados falsos/exemplo
    """

    def __init__(self):
        self.fake_data_found = {
            "usuarios": [],
            "setores": [],
            "municipios": [],
            "projetos": [],
            "tipos_evento": [],
            "solicitacoes": [],
        }
        self.real_data = {
            "usuarios": [],
            "setores": [],
            "municipios": [],
            "projetos": [],
            "tipos_evento": [],
        }
        self.actions_taken = []

    def investigate_all_data(self):
        """Investiga todos os dados do sistema"""
        print("🔍 INVESTIGAÇÃO DE DADOS FALSOS/EXEMPLO")
        print("=" * 60)

        # 1. Investigar usuários
        self.investigate_usuarios()

        # 2. Investigar setores
        self.investigate_setores()

        # 3. Investigar municípios
        self.investigate_municipios()

        # 4. Investigar projetos
        self.investigate_projetos()

        # 5. Investigar tipos de evento
        self.investigate_tipos_evento()

        # 6. Investigar solicitações
        self.investigate_solicitacoes()

        # 7. Relatório final
        self.print_investigation_report()

    def investigate_usuarios(self):
        """Investiga usuários falsos/exemplo"""
        print("\n👥 INVESTIGANDO USUÁRIOS")
        print("-" * 40)

        try:
            usuarios = Usuario.objects.all()
            print(f"  📊 Total de usuários: {usuarios.count()}")

            # Identificar usuários falsos/exemplo
            fake_patterns = [
                "admin",
                "administrador",
                "teste",
                "test",
                "exemplo",
                "example",
                "demo",
                "user",
                "usuario",
                "fake",
                "dummy",
                "sample",
            ]

            for usuario in usuarios:
                nome_completo = usuario.get_full_name() or usuario.username
                email = usuario.email or ""

                is_fake = False
                fake_reason = ""

                # Verificar padrões de dados falsos
                for pattern in fake_patterns:
                    if (
                        pattern.lower() in nome_completo.lower()
                        or pattern.lower() in email.lower()
                    ):
                        is_fake = True
                        fake_reason = f"Contém '{pattern}'"
                        break

                # Verificar se é usuário de sistema
                if usuario.username in ["admin", "administrador", "sistema"]:
                    is_fake = True
                    fake_reason = "Usuário de sistema"

                # Verificar se tem dados incompletos
                if not usuario.first_name and not usuario.last_name:
                    is_fake = True
                    fake_reason = "Dados incompletos"

                if is_fake:
                    self.fake_data_found["usuarios"].append(
                        {
                            "id": usuario.id,
                            "nome": nome_completo,
                            "email": email,
                            "username": usuario.username,
                            "reason": fake_reason,
                        }
                    )
                    print(f"  ❌ FAKE: {nome_completo} - {fake_reason}")
                else:
                    self.real_data["usuarios"].append(
                        {
                            "id": usuario.id,
                            "nome": nome_completo,
                            "email": email,
                            "cargo": usuario.cargo,
                            "setor": usuario.setor.nome if usuario.setor else None,
                        }
                    )
                    print(f"  ✅ REAL: {nome_completo}")

            print(f"  📊 Usuários reais: {len(self.real_data['usuarios'])}")
            print(f"  📊 Usuários falsos: {len(self.fake_data_found['usuarios'])}")

        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")

    def investigate_setores(self):
        """Investiga setores falsos/exemplo"""
        print("\n🏢 INVESTIGANDO SETORES")
        print("-" * 40)

        try:
            setores = Setor.objects.all()
            print(f"  📊 Total de setores: {setores.count()}")

            # Identificar setores falsos/exemplo
            fake_patterns = [
                "exemplo",
                "example",
                "teste",
                "test",
                "demo",
                "fake",
                "dummy",
                "sample",
                "não definido",
                "outros",
            ]

            for setor in setores:
                is_fake = False
                fake_reason = ""

                # Verificar padrões de dados falsos
                for pattern in fake_patterns:
                    if pattern.lower() in setor.nome.lower():
                        is_fake = True
                        fake_reason = f"Contém '{pattern}'"
                        break

                # Verificar se é setor genérico
                if setor.nome in ["-", "Outros", "Não Definido"]:
                    is_fake = True
                    fake_reason = "Setor genérico"

                if is_fake:
                    self.fake_data_found["setores"].append(
                        {
                            "id": setor.id,
                            "nome": setor.nome,
                            "sigla": setor.sigla,
                            "reason": fake_reason,
                        }
                    )
                    print(f"  ❌ FAKE: {setor.nome} - {fake_reason}")
                else:
                    self.real_data["setores"].append(
                        {
                            "id": setor.id,
                            "nome": setor.nome,
                            "sigla": setor.sigla,
                            "ativo": setor.ativo,
                        }
                    )
                    print(f"  ✅ REAL: {setor.nome}")

            print(f"  📊 Setores reais: {len(self.real_data['setores'])}")
            print(f"  📊 Setores falsos: {len(self.fake_data_found['setores'])}")

        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")

    def investigate_municipios(self):
        """Investiga municípios falsos/exemplo"""
        print("\n🏘️ INVESTIGANDO MUNICÍPIOS")
        print("-" * 40)

        try:
            municipios = Municipio.objects.all()
            print(f"  📊 Total de municípios: {municipios.count()}")

            # Identificar municípios falsos/exemplo
            fake_patterns = [
                "exemplo",
                "example",
                "teste",
                "test",
                "demo",
                "fake",
                "dummy",
                "sample",
                "cidade",
                "municipio",
            ]

            for municipio in municipios:
                is_fake = False
                fake_reason = ""

                # Verificar padrões de dados falsos
                for pattern in fake_patterns:
                    if pattern.lower() in municipio.nome.lower():
                        is_fake = True
                        fake_reason = f"Contém '{pattern}'"
                        break

                # Verificar se tem dados incompletos
                if not municipio.uf or municipio.uf == "":
                    is_fake = True
                    fake_reason = "UF não definida"

                if is_fake:
                    self.fake_data_found["municipios"].append(
                        {
                            "id": municipio.id,
                            "nome": municipio.nome,
                            "uf": municipio.uf,
                            "reason": fake_reason,
                        }
                    )
                    print(f"  ❌ FAKE: {municipio.nome} - {fake_reason}")
                else:
                    self.real_data["municipios"].append(
                        {
                            "id": municipio.id,
                            "nome": municipio.nome,
                            "uf": municipio.uf,
                            "ativo": municipio.ativo,
                        }
                    )
                    print(f"  ✅ REAL: {municipio.nome} - {municipio.uf}")

            print(f"  📊 Municípios reais: {len(self.real_data['municipios'])}")
            print(f"  📊 Municípios falsos: {len(self.fake_data_found['municipios'])}")

        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")

    def investigate_projetos(self):
        """Investiga projetos falsos/exemplo"""
        print("\n📋 INVESTIGANDO PROJETOS")
        print("-" * 40)

        try:
            projetos = Projeto.objects.all()
            print(f"  📊 Total de projetos: {projetos.count()}")

            # Identificar projetos falsos/exemplo
            fake_patterns = [
                "exemplo",
                "example",
                "teste",
                "test",
                "demo",
                "fake",
                "dummy",
                "sample",
                "projeto",
                "outros",
            ]

            for projeto in projetos:
                is_fake = False
                fake_reason = ""

                # Verificar padrões de dados falsos
                for pattern in fake_patterns:
                    if pattern.lower() in projeto.nome.lower():
                        is_fake = True
                        fake_reason = f"Contém '{pattern}'"
                        break

                # Verificar se é projeto genérico
                if projeto.nome in ["Outros", "Projeto"]:
                    is_fake = True
                    fake_reason = "Projeto genérico"

                if is_fake:
                    self.fake_data_found["projetos"].append(
                        {
                            "id": projeto.id,
                            "nome": projeto.nome,
                            "setor": projeto.setor.nome if projeto.setor else None,
                            "reason": fake_reason,
                        }
                    )
                    print(f"  ❌ FAKE: {projeto.nome} - {fake_reason}")
                else:
                    self.real_data["projetos"].append(
                        {
                            "id": projeto.id,
                            "nome": projeto.nome,
                            "setor": projeto.setor.nome if projeto.setor else None,
                            "ativo": projeto.ativo,
                        }
                    )
                    print(f"  ✅ REAL: {projeto.nome}")

            print(f"  📊 Projetos reais: {len(self.real_data['projetos'])}")
            print(f"  📊 Projetos falsos: {len(self.fake_data_found['projetos'])}")

        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")

    def investigate_tipos_evento(self):
        """Investiga tipos de evento falsos/exemplo"""
        print("\n🏷️ INVESTIGANDO TIPOS DE EVENTO")
        print("-" * 40)

        try:
            tipos = TipoEvento.objects.all()
            print(f"  📊 Total de tipos: {tipos.count()}")

            # Identificar tipos falsos/exemplo
            fake_patterns = [
                "exemplo",
                "example",
                "teste",
                "test",
                "demo",
                "fake",
                "dummy",
                "sample",
                "tipo",
                "evento",
            ]

            for tipo in tipos:
                is_fake = False
                fake_reason = ""

                # Verificar padrões de dados falsos
                for pattern in fake_patterns:
                    if pattern.lower() in tipo.nome.lower():
                        is_fake = True
                        fake_reason = f"Contém '{pattern}'"
                        break

                if is_fake:
                    self.fake_data_found["tipos_evento"].append(
                        {
                            "id": tipo.id,
                            "nome": tipo.nome,
                            "online": tipo.online,
                            "reason": fake_reason,
                        }
                    )
                    print(f"  ❌ FAKE: {tipo.nome} - {fake_reason}")
                else:
                    self.real_data["tipos_evento"].append(
                        {
                            "id": tipo.id,
                            "nome": tipo.nome,
                            "online": tipo.online,
                            "ativo": tipo.ativo,
                        }
                    )
                    print(f"  ✅ REAL: {tipo.nome}")

            print(f"  📊 Tipos reais: {len(self.real_data['tipos_evento'])}")
            print(f"  📊 Tipos falsos: {len(self.fake_data_found['tipos_evento'])}")

        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")

    def investigate_solicitacoes(self):
        """Investiga solicitações falsas/exemplo"""
        print("\n📅 INVESTIGANDO SOLICITAÇÕES")
        print("-" * 40)

        try:
            solicitacoes = Solicitacao.objects.all()
            print(f"  📊 Total de solicitações: {solicitacoes.count()}")

            if solicitacoes.count() == 0:
                print("  ✅ Nenhuma solicitação encontrada (sistema limpo)")
                return

            # Identificar solicitações falsas/exemplo
            fake_patterns = [
                "exemplo",
                "example",
                "teste",
                "test",
                "demo",
                "fake",
                "dummy",
                "sample",
                "solicitação",
                "evento",
            ]

            for solicitacao in solicitacoes:
                is_fake = False
                fake_reason = ""

                # Verificar padrões de dados falsos
                for pattern in fake_patterns:
                    if (
                        pattern.lower() in solicitacao.observacoes.lower()
                        if solicitacao.observacoes
                        else False
                    ):
                        is_fake = True
                        fake_reason = f"Observações contêm '{pattern}'"
                        break

                if is_fake:
                    self.fake_data_found["solicitacoes"].append(
                        {
                            "id": solicitacao.id,
                            "projeto": (
                                solicitacao.projeto.nome
                                if solicitacao.projeto
                                else None
                            ),
                            "municipio": (
                                solicitacao.municipio.nome
                                if solicitacao.municipio
                                else None
                            ),
                            "reason": fake_reason,
                        }
                    )
                    print(f"  ❌ FAKE: Solicitação {solicitacao.id} - {fake_reason}")
                else:
                    print(f"  ✅ REAL: Solicitação {solicitacao.id}")

            print(
                f"  📊 Solicitações falsas: {len(self.fake_data_found['solicitacoes'])}"
            )

        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")

    def print_investigation_report(self):
        """Imprime relatório de investigação"""
        print("\n📊 RELATÓRIO DE INVESTIGAÇÃO")
        print("=" * 60)

        # Estatísticas gerais
        total_real = sum(len(data) for data in self.real_data.values())
        total_fake = sum(len(data) for data in self.fake_data_found.values())

        print(f"\n📈 ESTATÍSTICAS GERAIS:")
        print(f"  • Total de dados reais: {total_real}")
        print(f"  • Total de dados falsos: {total_fake}")
        print(
            f"  • Percentual de dados reais: {(total_real/(total_real+total_fake)*100):.1f}%"
        )

        # Resumo por entidade
        print(f"\n📋 RESUMO POR ENTIDADE:")
        entities = ["usuarios", "setores", "municipios", "projetos", "tipos_evento"]
        for entity in entities:
            real_count = len(self.real_data[entity])
            fake_count = len(self.fake_data_found[entity])
            total_count = real_count + fake_count
            if total_count > 0:
                percentage = real_count / total_count * 100
                status = "✅" if percentage >= 80 else "⚠️" if percentage >= 50 else "❌"
                print(
                    f"  {status} {entity.title()}: {real_count}/{total_count} reais ({percentage:.1f}%)"
                )

        # Dados falsos encontrados
        if total_fake > 0:
            print(f"\n❌ DADOS FALSOS ENCONTRADOS ({total_fake}):")
            for entity, items in self.fake_data_found.items():
                if items:
                    print(f"  📁 {entity.title()}:")
                    for item in items:
                        print(
                            f"    • {item.get('nome', item.get('id', 'N/A'))} - {item.get('reason', 'N/A')}"
                        )
        else:
            print(f"\n✅ NENHUM DADO FALSO ENCONTRADO")

        # Conclusão
        print(f"\n🎯 CONCLUSÃO:")
        if total_fake == 0:
            print("✅ Sistema contém apenas dados reais das planilhas")
        elif total_fake < total_real:
            print(
                "⚠️ Sistema contém principalmente dados reais, mas há alguns dados falsos"
            )
        else:
            print("❌ Sistema contém muitos dados falsos/exemplo")
            print("\n🔧 RECOMENDAÇÕES:")
            print("  1. Remover dados falsos identificados")
            print("  2. Verificar origem dos dados de exemplo")
            print("  3. Garantir que apenas dados reais sejam exibidos")


def main():
    """Função principal"""
    try:
        investigator = FakeDataInvestigator()
        investigator.investigate_all_data()

    except Exception as e:
        logger.error(f"❌ Erro na investigação: {str(e)}")
        raise


if __name__ == "__main__":
    main()
