"""
Testes para Ingestão de CSVs ETL (dat_ingest)

App: dat_ingest
Stack: Python 3.13 | Django 5.2 | DRF | PostgreSQL 15

Testes cobrem:
  - Upsert idempotente (mesma linha 2x não duplica)
  - Pessoas por evento com row_hash estável
  - Bloqueios/Deslocamentos row_hash estável
  - Permissões (admin pode POST, user comum não)
  - Parsers de data/hora
"""

from datetime import date, time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    StgControleUnificado,
    StgDispBloqueio,
    StgDispDeslocamento,
    StgEvento,
    StgEventoPessoa,
)
from .utils import (
    normalize_string,
    parse_date,
    parse_time,
    safe_bool,
    safe_int,
    sha1_join,
)

User = get_user_model()


# =============================================================================
# TESTES DE UTILITÁRIOS
# =============================================================================


class UtilsTestCase(TestCase):
    """Testes para funções utilitárias"""

    def test_normalize_string(self):
        """Testa normalização de strings"""
        self.assertEqual(normalize_string("José Maria"), "jose maria")
        self.assertEqual(normalize_string("  FORTALEZA-CE  "), "fortaleza-ce")
        self.assertEqual(normalize_string("São Paulo"), "sao paulo")
        self.assertEqual(normalize_string(""), "")

    def test_sha1_join(self):
        """Testa geração de SHA1 hash"""
        hash1 = sha1_join("Fortaleza", "2025-01-15", "08:00")
        self.assertEqual(len(hash1), 40)  # SHA1 tem 40 caracteres hex

        # Normalização deve tornar hashes iguais
        hash2 = sha1_join("  FORTALEZA  ", "2025-01-15", "08:00")
        self.assertEqual(hash1, hash2)

        # Hashes diferentes para dados diferentes
        hash3 = sha1_join("Sobral", "2025-01-15", "08:00")
        self.assertNotEqual(hash1, hash3)

    def test_parse_date_valid(self):
        """Testa parsing de datas válidas"""
        self.assertEqual(parse_date("2025-01-15"), date(2025, 1, 15))
        self.assertEqual(parse_date("2024-12-31"), date(2024, 12, 31))

    def test_parse_date_invalid(self):
        """Testa parsing de datas inválidas"""
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date("invalid"))
        self.assertIsNone(parse_date("15-01-2025"))  # Formato errado

    def test_parse_time_valid(self):
        """Testa parsing de horas válidas"""
        self.assertEqual(parse_time("08:30"), time(8, 30, 0))
        self.assertEqual(parse_time("14:45:30"), time(14, 45, 30))
        self.assertEqual(parse_time("23:59:59"), time(23, 59, 59))

    def test_parse_time_invalid(self):
        """Testa parsing de horas inválidas"""
        self.assertIsNone(parse_time(""))
        self.assertIsNone(parse_time("invalid"))
        self.assertIsNone(parse_time("25:00"))  # Hora inválida

    def test_safe_int(self):
        """Testa conversão segura para int"""
        self.assertEqual(safe_int("123"), 123)
        self.assertEqual(safe_int(""), 0)
        self.assertEqual(safe_int("invalid"), 0)
        self.assertEqual(safe_int("invalid", -1), -1)

    def test_safe_bool(self):
        """Testa conversão segura para bool"""
        self.assertTrue(safe_bool("1"))
        self.assertTrue(safe_bool("true"))
        self.assertTrue(safe_bool("TRUE"))
        self.assertTrue(safe_bool("yes"))
        self.assertTrue(safe_bool("sim"))
        self.assertFalse(safe_bool("0"))
        self.assertFalse(safe_bool("false"))
        self.assertFalse(safe_bool(""))


# =============================================================================
# TESTES DE MODELOS
# =============================================================================


class StgEventoModelTestCase(TestCase):
    """Testes para modelo StgEvento"""

    def test_create_evento(self):
        """Testa criação de evento"""
        evento = StgEvento.objects.create(
            external_hash="abc123",
            municipio="Fortaleza",
            data=date(2025, 1, 15),
            hora_inicio=time(8, 0),
            hora_fim=time(12, 0),
            projeto="ACerta",
            tipo="Formação",
        )

        self.assertEqual(evento.external_hash, "abc123")
        self.assertEqual(evento.municipio, "Fortaleza")
        self.assertEqual(str(evento.data), "2025-01-15")

    def test_upsert_idempotente(self):
        """Testa que upsert não duplica registros"""
        # Primeira inserção
        evento1, created1 = StgEvento.objects.update_or_create(
            external_hash="abc123",
            defaults={
                "municipio": "Fortaleza",
                "projeto": "ACerta",
            },
        )
        self.assertTrue(created1)
        self.assertEqual(StgEvento.objects.count(), 1)

        # Segunda inserção (deve fazer update)
        evento2, created2 = StgEvento.objects.update_or_create(
            external_hash="abc123",
            defaults={
                "municipio": "Sobral",  # Alterado
                "projeto": "ACerta",
            },
        )
        self.assertFalse(created2)
        self.assertEqual(StgEvento.objects.count(), 1)  # Não duplicou
        self.assertEqual(evento2.municipio, "Sobral")  # Foi atualizado


class StgEventoPessoaModelTestCase(TestCase):
    """Testes para modelo StgEventoPessoa"""

    def setUp(self):
        """Cria evento para testes"""
        self.evento = StgEvento.objects.create(
            external_hash="evt123",
            municipio="Fortaleza",
        )

    def test_create_pessoa(self):
        """Testa criação de pessoa"""
        pessoa = StgEventoPessoa.objects.create(
            row_hash="person123",
            event_external_hash=self.evento,
            role="FORMADOR",
            name="José Silva",
            email="jose@example.com",
        )

        self.assertEqual(pessoa.row_hash, "person123")
        self.assertEqual(pessoa.name, "José Silva")
        self.assertEqual(pessoa.role, "FORMADOR")

    def test_row_hash_estavel(self):
        """Testa que row_hash é estável e idempotente"""
        hash1 = sha1_join("evt123", "FORMADOR", "José Silva")
        hash2 = sha1_join("evt123", "FORMADOR", "José Silva")
        self.assertEqual(hash1, hash2)

        # Criar pessoa com este hash
        pessoa1, created1 = StgEventoPessoa.objects.update_or_create(
            row_hash=hash1,
            defaults={
                "event_external_hash": self.evento,
                "role": "FORMADOR",
                "name": "José Silva",
                "email": "jose@example.com",
            },
        )
        self.assertTrue(created1)

        # Tentar criar novamente (deve fazer update)
        pessoa2, created2 = StgEventoPessoa.objects.update_or_create(
            row_hash=hash1,
            defaults={
                "event_external_hash": self.evento,
                "role": "FORMADOR",
                "name": "José Silva",
                "email": "jose.novo@example.com",  # Email alterado
            },
        )
        self.assertFalse(created2)
        self.assertEqual(StgEventoPessoa.objects.count(), 1)  # Não duplicou
        self.assertEqual(pessoa2.email, "jose.novo@example.com")  # Atualizado


class StgDispBloqueioModelTestCase(TestCase):
    """Testes para modelo StgDispBloqueio"""

    def test_bloqueio_row_hash_estavel(self):
        """Testa que row_hash de bloqueio é estável"""
        hash1 = sha1_join("2025-01-15", "2025-01-17", "Férias", "José Silva")
        hash2 = sha1_join("2025-01-15", "2025-01-17", "Férias", "José Silva")
        self.assertEqual(hash1, hash2)

        # Upsert
        bloqueio1, created1 = StgDispBloqueio.objects.update_or_create(
            row_hash=hash1,
            defaults={
                "data_inicial": date(2025, 1, 15),
                "data_final": date(2025, 1, 17),
                "tipo": "Férias",
                "responsavel": "José Silva",
            },
        )
        self.assertTrue(created1)

        # Upsert novamente (não deve duplicar)
        bloqueio2, created2 = StgDispBloqueio.objects.update_or_create(
            row_hash=hash1,
            defaults={
                "data_inicial": date(2025, 1, 15),
                "data_final": date(2025, 1, 17),
                "tipo": "Férias",
                "responsavel": "José Silva",
            },
        )
        self.assertFalse(created2)
        self.assertEqual(StgDispBloqueio.objects.count(), 1)


class StgDispDeslocamentoModelTestCase(TestCase):
    """Testes para modelo StgDispDeslocamento"""

    def test_deslocamento_row_hash_estavel(self):
        """Testa que row_hash de deslocamento é estável"""
        hash1 = sha1_join("Fortaleza", "2025-01-15", "Sobral", "José Silva")
        hash2 = sha1_join("Fortaleza", "2025-01-15", "Sobral", "José Silva")
        self.assertEqual(hash1, hash2)

        # Upsert
        desl1, created1 = StgDispDeslocamento.objects.update_or_create(
            row_hash=hash1,
            defaults={
                "origem": "Fortaleza",
                "data": date(2025, 1, 15),
                "destino": "Sobral",
                "responsavel": "José Silva",
            },
        )
        self.assertTrue(created1)

        # Upsert novamente (não deve duplicar)
        desl2, created2 = StgDispDeslocamento.objects.update_or_create(
            row_hash=hash1,
            defaults={
                "origem": "Fortaleza",
                "data": date(2025, 1, 15),
                "destino": "Sobral",
                "responsavel": "José Silva",
            },
        )
        self.assertFalse(created2)
        self.assertEqual(StgDispDeslocamento.objects.count(), 1)


# =============================================================================
# TESTES DE API (Endpoints REST)
# =============================================================================


class IngestAgendaAPITestCase(APITestCase):
    """Testes para endpoint POST /api/ingest/agenda/"""

    def setUp(self):
        """Cria usuários para testes de permissão"""
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
        )
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="user123",
        )

    def create_csv_file(self, content):
        """Cria arquivo CSV em memória"""
        return BytesIO(content.encode("utf-8"))

    def test_admin_can_post(self):
        """Testa que admin pode fazer POST"""
        self.client.force_authenticate(user=self.admin_user)

        events_csv = (
            "external_hash,municipio,data,projeto\nabc123,Fortaleza,2025-01-15,ACerta\n"
        )
        people_csv = "row_hash,event_external_hash,role,name\nperson123,abc123,FORMADOR,José Silva\n"

        response = self.client.post(
            "/api/ingest/agenda/",
            {
                "events": self.create_csv_file(events_csv),
                "people": self.create_csv_file(people_csv),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("events_upserted", response.data)
        self.assertIn("people_upserted", response.data)
        self.assertEqual(response.data["events_upserted"], 1)
        self.assertEqual(response.data["people_upserted"], 1)

    def test_regular_user_cannot_post(self):
        """Testa que usuário comum não pode fazer POST"""
        self.client.force_authenticate(user=self.regular_user)

        events_csv = (
            "external_hash,municipio,data,projeto\nabc123,Fortaleza,2025-01-15,ACerta\n"
        )
        people_csv = "row_hash,event_external_hash,role,name\nperson123,abc123,FORMADOR,José Silva\n"

        response = self.client.post(
            "/api/ingest/agenda/",
            {
                "events": self.create_csv_file(events_csv),
                "people": self.create_csv_file(people_csv),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_post(self):
        """Testa que usuário não autenticado não pode fazer POST"""
        events_csv = (
            "external_hash,municipio,data,projeto\nabc123,Fortaleza,2025-01-15,ACerta\n"
        )
        people_csv = "row_hash,event_external_hash,role,name\nperson123,abc123,FORMADOR,José Silva\n"

        response = self.client.post(
            "/api/ingest/agenda/",
            {
                "events": self.create_csv_file(events_csv),
                "people": self.create_csv_file(people_csv),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HealthCheckAPITestCase(APITestCase):
    """Testes para endpoint GET /api/ingest/health/"""

    def setUp(self):
        """Cria usuários e dados para teste"""
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
        )
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="user123",
        )

        # Cria alguns dados de teste
        StgEvento.objects.create(
            external_hash="evt1",
            municipio="Fortaleza",
        )
        StgEvento.objects.create(
            external_hash="evt2",
            municipio="Sobral",
        )

    def test_authenticated_can_get_health(self):
        """Testa que usuário autenticado pode acessar /health/"""
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get("/api/ingest/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("eventos", response.data)
        self.assertIn("pessoas", response.data)
        self.assertEqual(response.data["eventos"]["count"], 2)

    def test_admin_can_get_health(self):
        """Testa que admin pode acessar /health/"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/ingest/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("eventos", response.data)

    def test_unauthenticated_cannot_get_health(self):
        """Testa que usuário não autenticado não pode acessar /health/"""
        response = self.client.get("/api/ingest/health/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
