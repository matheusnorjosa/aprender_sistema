#!/usr/bin/env python
"""
SEMANA 3 - DIA 5: Testes end-to-end do fluxo completo
Script de teste automatizado que simula todo o fluxo do sistema.
"""

import json
import os
import sys
from datetime import datetime, timedelta

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.models import (
    AprovacaoStatus,
    Formador,
    LogComunicacao,
    Municipio,
    Notificacao,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


class EndToEndFlowTester:
    """Testa o fluxo completo do sistema do início ao fim"""

    def __init__(self):
        self.client = Client()
        self.coordenador = None
        self.superintendente = None
        self.controle = None
        self.formador = None
        self.solicitacao_id = None
        self.results = []

    def log_result(self, test_name, success, message=""):
        """Log dos resultados dos testes"""
        status = "✅ PASSOU" if success else "❌ FALHOU"
        self.results.append(
            {
                "test": test_name,
                "status": status,
                "success": success,
                "message": message,
            }
        )
        print(f"{status}: {test_name} {message}")

    def setup_users(self):
        """Configurar usuários de teste"""
        try:
            # Limpar usuários de teste existentes
            Usuario.objects.filter(
                username__in=[
                    "coord_teste",
                    "super_teste",
                    "controle_teste",
                    "admin_teste",
                ]
            ).delete()

            # Coordenador
            self.coordenador = Usuario.objects.create_user(
                username="coord_teste", email="coord@teste.com", password="teste123"
            )
            coord_group = Group.objects.get(name="coordenador")
            self.coordenador.groups.add(coord_group)

            # Superintendente
            self.superintendente = Usuario.objects.create_user(
                username="super_teste", email="super@teste.com", password="teste123"
            )
            super_group = Group.objects.get(name="superintendencia")
            self.superintendente.groups.add(super_group)

            # Controle
            self.controle = Usuario.objects.create_user(
                username="controle_teste",
                email="controle@teste.com",
                password="teste123",
            )
            controle_group, _ = Group.objects.get_or_create(name="controle")
            self.controle.groups.add(controle_group)

            # Formador
            self.formador = Formador.objects.first()

            self.log_result("Setup de Usuários", True, "- Usuários configurados")
            return True

        except Exception as e:
            self.log_result("Setup de Usuários", False, f"- Erro: {str(e)}")
            return False

    def test_01_home_page(self):
        """Teste 1: Página inicial carrega corretamente"""
        try:
            self.client.force_login(self.coordenador)
            response = self.client.get("/")

            success = response.status_code == 200
            message = f"- Status: {response.status_code}"

            self.log_result("01. Página Inicial", success, message)
            return success

        except Exception as e:
            self.log_result("01. Página Inicial", False, f"- Erro: {str(e)}")
            return False

    def test_02_criar_solicitacao(self):
        """Teste 2: Coordenador cria nova solicitação"""
        try:
            self.client.force_login(self.coordenador)

            # Buscar ou criar dados necessários
            projeto, _ = Projeto.objects.get_or_create(nome="Projeto Teste E2E")
            municipio, _ = Municipio.objects.get_or_create(nome="Cidade Teste", uf="SP")
            tipo_evento, _ = TipoEvento.objects.get_or_create(nome="Workshop E2E")

            if not self.formador:
                self.log_result(
                    "02. Criar Solicitação", False, "- Nenhum formador disponível"
                )
                return False

            # Criar solicitação via POST
            data_inicio = timezone.now() + timedelta(days=30)
            data_fim = data_inicio + timedelta(hours=8)

            form_data = {
                "titulo_evento": "Teste End-to-End - Evento de Teste",
                "projeto": projeto.id,
                "municipio": municipio.id,
                "tipo_evento": tipo_evento.id,
                "data_inicio": data_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "data_fim": data_fim.strftime("%Y-%m-%d %H:%M:%S"),
                "formadores": [self.formador.id],
                "coordenador_acompanha": False,
                "observacoes": "Teste automatizado do fluxo completo",
            }

            response = self.client.post("/solicitar/", form_data)

            # Verificar se foi criada
            if response.status_code == 302:  # Redirect após sucesso
                solicitacao = Solicitacao.objects.filter(
                    titulo_evento="Teste End-to-End - Evento de Teste"
                ).first()

                if solicitacao:
                    self.solicitacao_id = solicitacao.id
                    success = True
                    message = f"- Solicitação criada: {solicitacao.id}"
                else:
                    success = False
                    message = "- Solicitação não encontrada"
            else:
                success = False
                message = f"- Status: {response.status_code}"

            self.log_result("02. Criar Solicitação", success, message)
            return success

        except Exception as e:
            self.log_result("02. Criar Solicitação", False, f"- Erro: {str(e)}")
            return False

    def test_03_listar_pendentes(self):
        """Teste 3: Superintendência visualiza solicitações pendentes"""
        try:
            self.client.force_login(self.superintendente)

            # Testar página HTML
            response = self.client.get("/aprovacoes/pendentes/")
            html_success = response.status_code == 200

            # Testar API
            api_response = self.client.get("/api/solicitacoes-pendentes/")
            api_success = api_response.status_code == 200

            success = html_success and api_success
            message = f"- HTML: {response.status_code}, API: {api_response.status_code}"

            self.log_result("03. Listar Pendentes", success, message)
            return success

        except Exception as e:
            self.log_result("03. Listar Pendentes", False, f"- Erro: {str(e)}")
            return False

    def test_04_aprovar_solicitacao(self):
        """Teste 4: Superintendência aprova solicitação"""
        try:
            if not self.solicitacao_id:
                self.log_result(
                    "04. Aprovar Solicitação", False, "- Sem solicitação para testar"
                )
                return False

            self.client.force_login(self.superintendente)

            # Aprovar via API de lote
            response = self.client.post(
                "/api/bulk-approval/",
                json.dumps(
                    {
                        "solicitacao_ids": [str(self.solicitacao_id)],
                        "acao": "aprovar",
                        "justificativa": "Aprovação automática - teste end-to-end",
                    }
                ),
                content_type="application/json",
            )

            success = response.status_code == 200
            if success:
                data = response.json()
                if data.get("success"):
                    # Verificar se mudou para PRE_AGENDA
                    solicitacao = Solicitacao.objects.get(id=self.solicitacao_id)
                    if solicitacao.status == SolicitacaoStatus.PRE_AGENDA:
                        message = "- Aprovada e status PRE_AGENDA ✓"
                    else:
                        success = False
                        message = f"- Status incorreto: {solicitacao.status}"
                else:
                    success = False
                    message = f"- API retornou erro"
            else:
                message = f"- Status: {response.status_code}"

            self.log_result("04. Aprovar Solicitação", success, message)
            return success

        except Exception as e:
            self.log_result("04. Aprovar Solicitação", False, f"- Erro: {str(e)}")
            return False

    def test_05_pre_agenda_controle(self):
        """Teste 5: Controle visualiza pré-agenda"""
        try:
            self.client.force_login(self.controle)

            response = self.client.get("/controle/pre-agenda/")
            success = response.status_code == 200
            message = f"- Status: {response.status_code}"

            self.log_result("05. Pré-Agenda Controle", success, message)
            return success

        except Exception as e:
            self.log_result("05. Pré-Agenda Controle", False, f"- Erro: {str(e)}")
            return False

    def test_06_api_notificacoes(self):
        """Teste 6: APIs de notificações funcionando"""
        try:
            self.client.force_login(self.coordenador)

            # Testar API de notificações
            response = self.client.get("/api/notifications/user/")
            success = response.status_code == 200

            message = f"- Status: {response.status_code}"
            if success:
                data = response.json()
                count = len(data.get("notifications", []))
                message += f", {count} notificações"

            self.log_result("06. API Notificações", success, message)
            return success

        except Exception as e:
            self.log_result("06. API Notificações", False, f"- Erro: {str(e)}")
            return False

    def test_07_logs_admin(self):
        """Teste 7: Admin visualiza logs de comunicação"""
        try:
            # Criar usuário admin
            admin_user = Usuario.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = Usuario.objects.create_superuser(
                    username="admin_teste", email="admin@teste.com", password="teste123"
                )

            self.client.force_login(admin_user)

            # Testar página de logs
            response = self.client.get("/admin/communication-logs/")
            success = response.status_code == 200
            message = f"- Status: {response.status_code}"

            self.log_result("07. Logs Admin", success, message)
            return success

        except Exception as e:
            self.log_result("07. Logs Admin", False, f"- Erro: {str(e)}")
            return False

    def cleanup(self):
        """Limpar dados de teste"""
        try:
            # Remover solicitação de teste
            if self.solicitacao_id:
                Solicitacao.objects.filter(id=self.solicitacao_id).delete()

            # Remover usuários de teste
            Usuario.objects.filter(
                username__in=[
                    "coord_teste",
                    "super_teste",
                    "controle_teste",
                    "admin_teste",
                ]
            ).delete()

            print("\n🧹 Dados de teste limpos")

        except Exception as e:
            print(f"⚠️ Erro na limpeza: {str(e)}")

    def run_all_tests(self):
        """Executar todos os testes em sequência"""
        print("🚀 SEMANA 3 - DIA 5: TESTES END-TO-END DO FLUXO COMPLETO")
        print("=" * 65)

        # Setup
        if not self.setup_users():
            print("❌ Falha no setup - interrompendo testes")
            return False

        # Executar testes em sequência
        tests = [
            self.test_01_home_page,
            self.test_02_criar_solicitacao,
            self.test_03_listar_pendentes,
            self.test_04_aprovar_solicitacao,
            self.test_05_pre_agenda_controle,
            self.test_06_api_notificacoes,
            self.test_07_logs_admin,
        ]

        total_tests = len(tests)
        passed_tests = 0

        for test in tests:
            if test():
                passed_tests += 1

        # Limpeza
        self.cleanup()

        print("\n" + "=" * 65)
        print("📊 RESUMO DOS TESTES END-TO-END")
        print(f"✅ Testes aprovados: {passed_tests}/{total_tests}")
        print(f"❌ Testes falharam: {total_tests - passed_tests}/{total_tests}")
        print(f"🎯 Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")

        if passed_tests == total_tests:
            print("\n🎉 TODOS OS TESTES END-TO-END PASSARAM!")
            print("✅ Sistema Aprender funcionando corretamente.")
            print("✅ Fluxo completo: Coordenador → Superintendência → Controle")
        else:
            print(f"\n⚠️ {total_tests - passed_tests} testes falharam.")
            print("📝 Verificar logs acima para detalhes dos erros.")

        return passed_tests == total_tests


def main():
    """Função principal para executar os testes"""
    tester = EndToEndFlowTester()
    success = tester.run_all_tests()
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
