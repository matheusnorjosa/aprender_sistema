# core/tests/test_forms.py
"""
Testes para os formulários do sistema.
Extraído de core/tests.py para melhor organização.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from core.forms import SolicitacaoForm
from core.models import (
    DisponibilidadeFormadores,
    Formador,
    Municipio,
    Projeto,
    Setor,
    TipoEvento,
)

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class SolicitacaoFormTest(TestCase):
    """Testes para o formulário SolicitacaoForm"""

    def setUp(self):
        """Configuração inicial para os testes"""
        # Criar setor primeiro
        self.setor = Setor.objects.create(
            nome="Setor Teste", sigla="TEST", vinculado_superintendencia=False
        )

        self.projeto = Projeto.objects.create(nome="Projeto Teste", setor=self.setor)
        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop")

        # Criar grupo de área de atuação
        from django.contrib.auth.models import Group

        area_matematica = Group.objects.create(name="Matemática")

        self.formador = Formador.objects.create(
            nome="João Silva", email="joao@test.com", area_atuacao=area_matematica
        )

        # Create a user that acts as formador
        self.user_formador = User.objects.create_user(
            username="formador_test",
            email="formador@test.com",
            password="test123",
            formador_ativo=True,
        )

        self.valid_data = {
            "projeto": self.projeto.id,
            "municipio": self.municipio.id,
            "tipo_evento": self.tipo_evento.id,
            "titulo_evento": "Evento Teste",
            "data_inicio": (timezone.now() + timedelta(days=7)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "data_fim": (timezone.now() + timedelta(days=7, hours=2)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "numero_encontro_formativo": "1º Encontro",
            "coordenador_acompanha": True,
            "observacoes": "Observação teste",
            "formadores": [self.user_formador.id],
        }

    def test_valid_form(self):
        """Testa formulário válido"""
        form = SolicitacaoForm(data=self.valid_data)
        self.assertTrue(
            form.is_valid(), f"Formulário deveria ser válido. Erros: {form.errors}"
        )

    def test_data_fim_before_inicio(self):
        """Testa validação quando data fim é antes da data início"""
        data = self.valid_data.copy()
        data["data_inicio"] = (timezone.now() + timedelta(days=7, hours=2)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        data["data_fim"] = (timezone.now() + timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M"
        )

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "A data/hora de término deve ser maior que a de início", str(form.errors)
        )

    def test_minimum_duration(self):
        """Testa validação de duração mínima"""
        data = self.valid_data.copy()
        futuro = timezone.now() + timedelta(days=7)
        data["data_inicio"] = futuro.strftime("%Y-%m-%dT%H:%M")
        data["data_fim"] = (futuro + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "O evento deve ter duração mínima de 30 minutos", str(form.errors)
        )

    def test_past_date_validation(self):
        """Testa validação de data no passado"""
        data = self.valid_data.copy()
        passado = timezone.now() - timedelta(days=1)
        data["data_inicio"] = passado.strftime("%Y-%m-%dT%H:%M")
        data["data_fim"] = (passado + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("A data de início deve ser no futuro", str(form.errors))

    def test_titulo_too_short(self):
        """Testa validação de título muito curto"""
        data = self.valid_data.copy()
        data["titulo_evento"] = "AB"  # Menos de 3 caracteres

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "O título do evento deve ter pelo menos 3 caracteres", str(form.errors)
        )

    def test_formadores_required(self):
        """Testa que formadores são obrigatórios"""
        data = self.valid_data.copy()
        data["formadores"] = []

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("formadores", form.errors)

    def test_conflict_with_availability(self):
        """Testa detecção de conflito com disponibilidade de formadores"""
        # Criar bloqueio de disponibilidade
        futuro = timezone.now() + timedelta(days=7)
        DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=futuro.date(),
            hora_inicio=futuro.time(),
            hora_fim=(futuro + timedelta(hours=1)).time(),
            tipo_bloqueio="Total",
            motivo="Indisponível",
        )

        data = self.valid_data.copy()
        data["data_inicio"] = futuro.strftime("%Y-%m-%dT%H:%M")
        data["data_fim"] = (futuro + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        form = SolicitacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("Conflitos de disponibilidade", str(form.errors))
