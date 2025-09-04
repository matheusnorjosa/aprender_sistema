"""
Testes para as APIs de aprovação avançada.
SEMANA 3 - DIA 2: Sistema de aprovação/rejeição aprimorado
"""

import json
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Aprovacao,
    AprovacaoStatus,
    Formador,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)

Usuario = get_user_model()


class BulkApprovalAPITest(TestCase):

    def setUp(self):
        """Setup inicial para os testes"""
        # Criar usuários de teste
        self.superintendente = Usuario.objects.create_user(
            username="superintendente_test",
            email="super@test.com",
            password="testpass123",
        )

        self.coordenador = Usuario.objects.create_user(
            username="coordenador_test", email="coord@test.com", password="testpass123"
        )

        # Criar dados básicos
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)

        self.projeto = Projeto.objects.create(
            nome="Projeto Teste Aprovação",
            descricao="Projeto para testar aprovações",
            ativo=True,
            vinculado_superintendencia=True,  # Requer aprovação
        )

        self.tipo_evento = TipoEvento.objects.create(
            nome="Capacitação Aprovação", online=False, ativo=True
        )

        # Criar formador
        self.formador = Formador.objects.create(
            nome="João Silva Aprovação", email="joao.aprovacao@test.com", ativo=True
        )

        # Criar solicitações de teste
        self.solicitacoes = []
        for i in range(3):
            solicitacao = Solicitacao.objects.create(
                usuario_solicitante=self.coordenador,
                projeto=self.projeto,
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                titulo_evento=f"Evento Teste {i+1}",
                data_inicio=timezone.now() + timedelta(days=i + 1, hours=9),
                data_fim=timezone.now() + timedelta(days=i + 1, hours=17),
                status=SolicitacaoStatus.PENDENTE,
            )
            solicitacao.formadores.add(self.formador)
            self.solicitacoes.append(solicitacao)

        # URLs das APIs
        self.bulk_approval_url = reverse("core:bulk_approval_api")
        self.solicitacoes_pendentes_url = reverse("core:solicitacoes_pendentes_api")

        # Login do superintendente
        self.client.login(username="superintendente_test", password="testpass123")

    def test_bulk_approval_requires_permission(self):
        """Testa se a API exige permissão correta"""
        # Logout para testar sem autenticação
        self.client.logout()

        response = self.client.post(
            self.bulk_approval_url,
            json.dumps({"solicitacao_ids": ["123"], "acao": "aprovar"}),
            content_type="application/json",
        )

        # Deve redirecionar para login ou retornar 403
        self.assertIn(response.status_code, [302, 403])

    def test_bulk_approval_success(self):
        """Testa aprovação em lote bem-sucedida"""
        solicitacao_ids = [str(sol.id) for sol in self.solicitacoes[:2]]

        data = {
            "solicitacao_ids": solicitacao_ids,
            "acao": "aprovar",
            "justificativa": "Aprovação em lote para teste",
        }

        response = self.client.post(
            self.bulk_approval_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(result["processadas"], 2)
        self.assertEqual(result["sucessos"], 2)
        self.assertEqual(result["erros"], 0)

        # Verificar se as solicitações foram atualizadas
        for sol_id in solicitacao_ids:
            solicitacao = Solicitacao.objects.get(id=sol_id)
            self.assertEqual(solicitacao.status, SolicitacaoStatus.PRE_AGENDA)
            self.assertEqual(solicitacao.usuario_aprovador, self.superintendente)
            self.assertIsNotNone(solicitacao.data_aprovacao_rejeicao)

            # Verificar se foi criado registro de aprovação
            aprovacao = Aprovacao.objects.get(solicitacao=solicitacao)
            self.assertEqual(aprovacao.status_decisao, AprovacaoStatus.APROVADO)
            self.assertEqual(aprovacao.justificativa, "Aprovação em lote para teste")

    def test_bulk_rejection_success(self):
        """Testa rejeição em lote bem-sucedida"""
        solicitacao_ids = [str(sol.id) for sol in self.solicitacoes[:2]]

        data = {
            "solicitacao_ids": solicitacao_ids,
            "acao": "reprovar",
            "justificativa": "Rejeição em lote para teste",
        }

        response = self.client.post(
            self.bulk_approval_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(result["sucessos"], 2)

        # Verificar se as solicitações foram rejeitadas
        for sol_id in solicitacao_ids:
            solicitacao = Solicitacao.objects.get(id=sol_id)
            self.assertEqual(solicitacao.status, SolicitacaoStatus.REPROVADO)

            aprovacao = Aprovacao.objects.get(solicitacao=solicitacao)
            self.assertEqual(aprovacao.status_decisao, AprovacaoStatus.REPROVADO)

    def test_bulk_approval_invalid_action(self):
        """Testa ação inválida"""
        data = {
            "solicitacao_ids": [str(self.solicitacoes[0].id)],
            "acao": "acao_invalida",
        }

        response = self.client.post(
            self.bulk_approval_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])
        self.assertIn("Ação inválida", result["error"])

    def test_bulk_approval_no_solicitacoes(self):
        """Testa sem selecionar solicitações"""
        data = {"solicitacao_ids": [], "acao": "aprovar"}

        response = self.client.post(
            self.bulk_approval_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])
        self.assertIn("Nenhuma solicitação selecionada", result["error"])

    def test_bulk_approval_already_processed(self):
        """Testa processamento de solicitação já processada"""
        # Marcar uma solicitação como já aprovada
        solicitacao = self.solicitacoes[0]
        solicitacao.status = SolicitacaoStatus.APROVADO
        solicitacao.save()

        data = {"solicitacao_ids": [str(solicitacao.id)], "acao": "aprovar"}

        response = self.client.post(
            self.bulk_approval_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])  # Deve falhar pois já foi processada
        self.assertEqual(result["sucessos"], 0)

    def test_bulk_approval_invalid_json(self):
        """Testa JSON inválido"""
        response = self.client.post(
            self.bulk_approval_url, "invalid json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])
        self.assertIn("JSON inválidos", result["error"])


class SolicitacoesPendentesAPITest(TestCase):

    def setUp(self):
        """Setup inicial para os testes"""
        self.superintendente = Usuario.objects.create_user(
            username="super_pendentes",
            email="super.pendentes@test.com",
            password="testpass123",
        )

        # Criar dados básicos
        self.municipio1 = Municipio.objects.create(
            nome="Fortaleza", uf="CE", ativo=True
        )
        self.municipio2 = Municipio.objects.create(
            nome="São Paulo", uf="SP", ativo=True
        )

        self.projeto = Projeto.objects.create(
            nome="Projeto Pendentes", ativo=True, vinculado_superintendencia=True
        )

        self.tipo_evento = TipoEvento.objects.create(nome="Tipo Pendentes", ativo=True)

        self.formador = Formador.objects.create(
            nome="Formador Pendentes", email="formador.pendentes@test.com", ativo=True
        )

        # Criar solicitações com diferentes características
        for i in range(5):
            solicitacao = Solicitacao.objects.create(
                usuario_solicitante=self.superintendente,
                projeto=self.projeto,
                municipio=self.municipio1 if i % 2 == 0 else self.municipio2,
                tipo_evento=self.tipo_evento,
                titulo_evento=f"Evento {i+1}",
                data_inicio=timezone.now() + timedelta(days=i + 1, hours=9),
                data_fim=timezone.now() + timedelta(days=i + 1, hours=17),
                status=SolicitacaoStatus.PENDENTE,
            )
            solicitacao.formadores.add(self.formador)

        self.api_url = reverse("core:solicitacoes_pendentes_api")
        self.client.login(username="super_pendentes", password="testpass123")

    def test_list_solicitacoes_success(self):
        """Testa listagem básica de solicitações"""
        response = self.client.get(self.api_url)

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(len(result["solicitacoes"]), 5)
        self.assertIn("pagination", result)

        # Verificar estrutura de cada solicitação
        for sol in result["solicitacoes"]:
            self.assertIn("id", sol)
            self.assertIn("titulo_evento", sol)
            self.assertIn("has_conflicts", sol)
            self.assertIn("conflicts_count", sol)
            self.assertIn("formadores", sol)

    def test_list_solicitacoes_with_filters(self):
        """Testa listagem com filtros"""
        # Filtrar por município
        response = self.client.get(f"{self.api_url}?municipio={self.municipio1.id}")

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["success"])

        # Deve retornar apenas solicitações do município 1
        for sol in result["solicitacoes"]:
            self.assertEqual(sol["municipio"], self.municipio1.nome)

    def test_list_solicitacoes_with_search(self):
        """Testa busca por título"""
        response = self.client.get(f"{self.api_url}?q=Evento 1")

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["success"])

        # Deve encontrar apenas uma solicitação
        self.assertEqual(len(result["solicitacoes"]), 1)
        self.assertEqual(result["solicitacoes"][0]["titulo_evento"], "Evento 1")

    def test_list_solicitacoes_pagination(self):
        """Testa paginação"""
        response = self.client.get(f"{self.api_url}?page=1&page_size=2")

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["success"])

        # Deve retornar apenas 2 resultados
        self.assertEqual(len(result["solicitacoes"]), 2)
        self.assertEqual(result["pagination"]["current_page"], 1)
        self.assertEqual(result["pagination"]["page_size"], 2)
        self.assertTrue(result["pagination"]["has_next"])

    def test_list_solicitacoes_requires_permission(self):
        """Testa se a API exige permissão"""
        self.client.logout()

        response = self.client.get(self.api_url)

        # Deve redirecionar para login ou retornar 403
        self.assertIn(response.status_code, [302, 403])


class SolicitacaoConflictsAPITest(TestCase):

    def setUp(self):
        """Setup inicial para os testes"""
        self.superintendente = Usuario.objects.create_user(
            username="super_conflicts",
            email="super.conflicts@test.com",
            password="testpass123",
        )

        # Criar dados básicos
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
        self.projeto = Projeto.objects.create(nome="Projeto Conflicts", ativo=True)
        self.tipo_evento = TipoEvento.objects.create(nome="Tipo Conflicts", ativo=True)
        self.formador = Formador.objects.create(
            nome="Formador Conflicts", email="formador.conflicts@test.com", ativo=True
        )

        # Criar solicitação de teste
        self.solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.superintendente,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Conflitos",
            data_inicio=timezone.now() + timedelta(days=1, hours=9),
            data_fim=timezone.now() + timedelta(days=1, hours=17),
            status=SolicitacaoStatus.PENDENTE,
        )
        self.solicitacao.formadores.add(self.formador)

        self.client.login(username="super_conflicts", password="testpass123")

    def test_conflicts_analysis_no_conflicts(self):
        """Testa análise sem conflitos"""
        url = reverse(
            "core:solicitacao_conflicts_api",
            kwargs={"solicitacao_id": self.solicitacao.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(result["solicitacao_id"], str(self.solicitacao.id))
        self.assertFalse(result["has_conflicts"])
        self.assertEqual(len(result["conflicts"]), 0)
        self.assertEqual(result["recommendation"]["action"], "approve")

    def test_conflicts_analysis_nonexistent_solicitacao(self):
        """Testa análise de solicitação inexistente"""
        import uuid

        fake_id = uuid.uuid4()
        url = reverse(
            "core:solicitacao_conflicts_api", kwargs={"solicitacao_id": fake_id}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_conflicts_analysis_requires_permission(self):
        """Testa se a API exige permissão"""
        self.client.logout()

        url = reverse(
            "core:solicitacao_conflicts_api",
            kwargs={"solicitacao_id": self.solicitacao.id},
        )
        response = self.client.get(url)

        # Deve redirecionar para login ou retornar 403
        self.assertIn(response.status_code, [302, 403])
