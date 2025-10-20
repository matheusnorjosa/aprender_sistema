"""
Testes para as APIs de verificação de disponibilidade em tempo real.
SEMANA 3 - DIA 1: Interface de solicitação aprimorada
"""

import json
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    DisponibilidadeFormadores,
    Formador,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)

Usuario = get_user_model()


class CheckAvailabilityAPITest(TestCase):

    def setUp(self):
        """Setup inicial para os testes"""
        # Criar usuário de teste
        self.user = Usuario.objects.create_user(
            username="coordenador_test",
            email="coordenador@test.com",
            password="testpass123",
        )

        # Criar dados básicos
        self.municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)

        self.projeto = Projeto.objects.create(
            nome="Projeto Teste API", descricao="Projeto para testar API", ativo=True
        )

        self.tipo_evento = TipoEvento.objects.create(
            nome="Capacitação Online API", online=True, ativo=True
        )

        # Criar formadores
        self.formador1 = Formador.objects.create(
            nome="João Silva API", email="joao.api@test.com", ativo=True
        )

        self.formador2 = Formador.objects.create(
            nome="Maria Santos API", email="maria.api@test.com", ativo=True
        )

        # URL da API
        self.api_url = reverse("core:check_availability_api")

        # Login do usuário
        self.client.login(username="coordenador_test", password="testpass123")

        # Data/hora base para testes (timezone-aware)
        self.base_datetime = timezone.now().replace(
            hour=9, minute=0, second=0, microsecond=0
        ) + timedelta(
            days=1
        )  # Amanhã às 9h

    def test_api_requires_authentication(self):
        """Testa se a API exige autenticação"""
        self.client.logout()

        response = self.client.post(self.api_url, {}, content_type="application/json")

        # Deve redirecionar para login ou retornar 403
        self.assertIn(response.status_code, [302, 403])

    def test_availability_check_success_no_conflicts(self):
        """Testa verificação de disponibilidade sem conflitos"""
        data = {
            "formadores": [str(self.formador1.id), str(self.formador2.id)],
            "data_inicio": self.base_datetime.isoformat(),
            "data_fim": (self.base_datetime + timedelta(hours=2)).isoformat(),
            "municipio": str(self.municipio.id),
        }

        response = self.client.post(
            self.api_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertTrue(result["available"])
        self.assertEqual(len(result["conflicts"]), 0)
        self.assertEqual(len(result["formadores_verificados"]), 2)
        self.assertIn("João Silva API", result["formadores_verificados"])
        self.assertIn("Maria Santos API", result["formadores_verificados"])

    def test_availability_check_with_total_block(self):
        """Testa verificação com bloqueio total (T)"""
        # Criar bloqueio total
        DisponibilidadeFormadores.objects.create(
            formador=self.formador1,
            data_bloqueio=self.base_datetime.date(),
            hora_inicio=self.base_datetime.time(),
            hora_fim=(self.base_datetime + timedelta(hours=8)).time(),
            tipo_bloqueio="Total",
            motivo="Bloqueio total para teste API",
        )

        data = {
            "formadores": [str(self.formador1.id)],
            "data_inicio": self.base_datetime.isoformat(),
            "data_fim": (self.base_datetime + timedelta(hours=2)).isoformat(),
            "municipio": str(self.municipio.id),
        }

        response = self.client.post(
            self.api_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertFalse(result["available"])
        self.assertEqual(len(result["conflicts"]), 1)

        conflict = result["conflicts"][0]
        self.assertEqual(conflict["type"], "bloqueio")
        self.assertEqual(conflict["code"], "T")
        self.assertEqual(conflict["severity"], "error")
        self.assertIn("João Silva API", conflict["message"])

    def test_availability_check_with_event_conflict(self):
        """Testa verificação com conflito de evento (E)"""
        # Criar solicitação aprovada
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Conflitante API",
            data_inicio=self.base_datetime,
            data_fim=self.base_datetime + timedelta(hours=3),
            status=SolicitacaoStatus.APROVADO,
        )
        solicitacao.formadores.add(self.formador1)

        data = {
            "formadores": [str(self.formador1.id)],
            "data_inicio": (self.base_datetime + timedelta(hours=1)).isoformat(),
            "data_fim": (self.base_datetime + timedelta(hours=2)).isoformat(),
            "municipio": str(self.municipio.id),
        }

        response = self.client.post(
            self.api_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertFalse(result["available"])
        self.assertEqual(len(result["conflicts"]), 1)

        conflict = result["conflicts"][0]
        self.assertEqual(conflict["type"], "evento")
        self.assertEqual(conflict["code"], "E")
        self.assertEqual(conflict["severity"], "error")
        self.assertIn("Evento Conflitante API", conflict["message"])

    def test_availability_check_invalid_data(self):
        """Testa API com dados inválidos"""
        test_cases = [
            # Sem formadores
            {
                "data": {
                    "formadores": [],
                    "data_inicio": self.base_datetime.isoformat(),
                    "data_fim": (self.base_datetime + timedelta(hours=2)).isoformat(),
                },
                "expected_error": "Formadores devem ser selecionados",
            },
            # Sem data de início
            {
                "data": {
                    "formadores": [str(self.formador1.id)],
                    "data_inicio": "",
                    "data_fim": (self.base_datetime + timedelta(hours=2)).isoformat(),
                },
                "expected_error": "Datas de início e fim são obrigatórias",
            },
            # Data de fim anterior à de início
            {
                "data": {
                    "formadores": [str(self.formador1.id)],
                    "data_inicio": self.base_datetime.isoformat(),
                    "data_fim": (self.base_datetime - timedelta(hours=1)).isoformat(),
                },
                "expected_error": "Data de fim deve ser posterior à data de início",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["expected_error"]):
                response = self.client.post(
                    self.api_url,
                    json.dumps(case["data"]),
                    content_type="application/json",
                )

                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertFalse(result["success"])
                self.assertIn(case["expected_error"], result["error"])

    def test_availability_check_invalid_json(self):
        """Testa API com JSON inválido"""
        response = self.client.post(
            self.api_url, "invalid json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])
        self.assertIn("JSON inválidos", result["error"])

    def test_availability_check_nonexistent_formador(self):
        """Testa API com formador inexistente"""
        data = {
            "formadores": ["99999"],  # ID inexistente
            "data_inicio": self.base_datetime.isoformat(),
            "data_fim": (self.base_datetime + timedelta(hours=2)).isoformat(),
        }

        response = self.client.post(
            self.api_url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])
        self.assertIn("formadores não foram encontrados", result["error"])


class FormadorDetailsAPITest(TestCase):

    def setUp(self):
        """Setup inicial para os testes"""
        self.user = Usuario.objects.create_user(
            username="test_user_details",
            email="details@test.com",
            password="testpass123",
        )

        self.formador = Formador.objects.create(
            nome="Formador Detalhes", email="detalhes@test.com", ativo=True
        )

        self.api_url = reverse("core:formador_details_api")
        self.client.login(username="test_user_details", password="testpass123")

    def test_formador_details_success(self):
        """Testa obtenção de detalhes dos formadores"""
        response = self.client.get(f"{self.api_url}?ids[]={self.formador.id}")

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(len(result["formadores"]), 1)

        formador_data = result["formadores"][0]
        self.assertEqual(formador_data["nome"], "Formador Detalhes")
        self.assertEqual(formador_data["email"], "detalhes@test.com")

    def test_formador_details_no_ids(self):
        """Testa API sem fornecer IDs"""
        response = self.client.get(self.api_url)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])
        self.assertIn("IDs de formadores não fornecidos", result["error"])

    def test_formador_details_requires_authentication(self):
        """Testa se a API exige autenticação"""
        self.client.logout()

        response = self.client.get(f"{self.api_url}?ids[]={self.formador.id}")

        # Deve redirecionar para login ou retornar 403
        self.assertIn(response.status_code, [302, 403])
