# core/tests/test_models.py
"""
Testes para os modelos do sistema.
Extraído de core/tests.py para melhor organização.
"""

import json
from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Aprovacao,
    AprovacaoStatus,
    DisponibilidadeFormadores,
    EventoGoogleCalendar,
    Formador,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
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
class SolicitacaoModelTest(TestCase):
    """Testes para o modelo Solicitacao"""

    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username="coord_test",
            email="coord@test.com",
            password="testpass123",
        )

        # Criar setor primeiro (superintendência para testar PENDENTE)
        from core.models import Setor

        self.setor = Setor.objects.create(
            nome="Superintendência Teste",
            sigla="SUPER",
            vinculado_superintendencia=True,
        )

        self.projeto = Projeto.objects.create(
            nome="Projeto Teste",
            descricao="Descrição do projeto teste",
            setor=self.setor,
        )

        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")

        self.tipo_evento = TipoEvento.objects.create(nome="Workshop", online=False)

        # Criar grupo de área de atuação
        from django.contrib.auth.models import Group

        area_matematica = Group.objects.create(name="Matemática")

        self.formador = Formador.objects.create(
            nome="João Silva", email="joao@test.com", area_atuacao=area_matematica
        )

    def test_create_solicitacao(self):
        """Testa a criação de uma solicitação"""
        futuro = timezone.now() + timedelta(days=7)
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento Teste",
            data_inicio=futuro,
            data_fim=futuro + timedelta(hours=2),
            numero_encontro_formativo="1º Encontro",
            coordenador_acompanha=True,
            observacoes="Observação teste",
        )

        self.assertEqual(solicitacao.titulo_evento, "Evento Teste")
        self.assertEqual(solicitacao.status, SolicitacaoStatus.PENDENTE)
        self.assertEqual(str(solicitacao), f"Evento Teste ({futuro:%d/%m/%Y %H:%M})")

    def test_solicitacao_ordering(self):
        """Testa a ordenação das solicitações"""
        futuro1 = timezone.now() + timedelta(days=7)
        futuro2 = timezone.now() + timedelta(days=8)

        sol1 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento 1",
            data_inicio=futuro1,
            data_fim=futuro1 + timedelta(hours=2),
        )

        sol2 = Solicitacao.objects.create(
            usuario_solicitante=self.user,
            projeto=self.projeto,
            municipio=self.municipio,
            tipo_evento=self.tipo_evento,
            titulo_evento="Evento 2",
            data_inicio=futuro2,
            data_fim=futuro2 + timedelta(hours=2),
        )

        # As solicitações devem ser ordenadas por data_solicitacao decrescente
        solicitacoes = list(Solicitacao.objects.all())
        self.assertEqual(solicitacoes[0], sol2)  # Mais recente primeiro
        self.assertEqual(solicitacoes[1], sol1)
