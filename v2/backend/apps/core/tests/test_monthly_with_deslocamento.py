"""
Testes para códigos D e D1 na grade mensal.

Valida precedência:
- X: evento + bloqueio (com ou sem deslocamento)
- D1: evento + deslocamento (sem bloqueio)
- D: deslocamento apenas (sem evento, sem bloqueio)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.utils import timezone

import pytest

from apps.core.models import (
    AvailabilityBlock,
    Deslocamento,
    Participation,
)
from apps.core.services.monthly_grid_service import build_monthly_grid
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)


@pytest.mark.django_db
class TestMonthlyWithDeslocamento:
    """
    Testes para códigos D e D1 na grade mensal.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup inicial: criar dados básicos."""
        self.tz = timezone.get_current_timezone()

        # Criar usuários
        self.user_formador = UsuarioFactory(
            username="formador1",
            email="formador1@example.com",
            password="password123",
        )

        # Criar municipio, projeto, tipo_evento
        self.municipio = MunicipioFactory(
            nome="Fortaleza",
            uf="CE",
            ativo=True,
        )

        self.projeto = ProjetoFactory(
            nome="Projeto Teste",
            ativo=True,
            fluxo="SUPER",  # Required for monthly_grid_service.py filter
        )

        self.tipo_evento = TipoEventoFactory(
            nome="Formação",
            cor="#FF0000",
        )

    def test_code_D_deslocamento_only(self):
        """
        D: deslocamento apenas (sem evento, sem bloqueio)

        Cenário:
        - Dia 10: deslocamento apenas
        - Dia 15: vazio

        Expectativa:
        - Dia 10: código "D"
        - Dia 15: código ""
        """
        # Criar deslocamento dia 10
        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="Fortaleza",
            destino="São Paulo",
            start_date=date(2025, 10, 10),
            end_date=date(2025, 10, 10),
        )

        # Criar participation em OUTUBRO para incluir usuário na grade
        solicitacao = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 20, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 20, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=solicitacao,
            usuario=self.user_formador,
            role="FORMADOR",
        )

        # Build grid
        result = build_monthly_grid(year=2025, month=10, role="FORMADOR")

        # Validar
        assert len(result["people"]) == 1
        assert result["people"][0]["id"] == self.user_formador.id

        # Código dia 10 (índice 9) deve ser "D"
        cells = result["cells"][0]
        assert cells[9] == "D"

        # Código dia 15 (índice 14) deve ser ""
        assert cells[14] == ""

        # Legend deve incluir D
        assert "D" in result["legend"]
        assert result["legend"]["D"] == "Deslocamento"

    def test_code_D1_event_plus_deslocamento(self):
        """
        D1: evento + deslocamento (sem bloqueio)

        Cenário:
        - Dia 10: evento + deslocamento (sem bloqueio)
        - Dia 15: evento apenas (sem deslocamento)

        Expectativa:
        - Dia 10: código "D1"
        - Dia 15: código "E"
        """
        # Criar evento aprovado dia 10
        solicitacao_day10 = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 10, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 10, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=solicitacao_day10,
            usuario=self.user_formador,
            role="FORMADOR",
        )

        # Criar deslocamento dia 10
        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="Fortaleza",
            destino="São Paulo",
            start_date=date(2025, 10, 10),
            end_date=date(2025, 10, 10),
        )

        # Criar evento aprovado dia 15 (sem deslocamento)
        solicitacao_day15 = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 15, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 15, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=solicitacao_day15,
            usuario=self.user_formador,
            role="FORMADOR",
        )

        # Build grid
        result = build_monthly_grid(year=2025, month=10, role="FORMADOR")

        # Validar
        cells = result["cells"][0]

        # Dia 10 (índice 9) deve ser "D1"
        assert cells[9] == "D1"

        # Dia 15 (índice 14) deve ser "E"
        assert cells[14] == "E"

        # Legend deve incluir D1
        assert "D1" in result["legend"]
        assert result["legend"]["D1"] == "Evento + deslocamento"

        # Details para D1 devem conter o evento
        detail_key_day10 = "0:9"
        assert detail_key_day10 in result["details_index"]
        assert len(result["details_index"][detail_key_day10]) == 1

    def test_code_X_event_block_deslocamento(self):
        """
        X: evento + bloqueio + deslocamento (precedência máxima)

        Cenário:
        - Dia 10: evento + bloqueio + deslocamento → X
        - Dia 15: evento + bloqueio (sem deslocamento) → X

        Expectativa:
        - Dia 10: código "X"
        - Dia 15: código "X"
        """
        # Dia 10: evento + bloqueio + deslocamento
        solicitacao_day10 = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 10, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 10, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=solicitacao_day10,
            usuario=self.user_formador,
            role="FORMADOR",
        )

        AvailabilityBlock.objects.create(
            usuario=self.user_formador,
            tipo="P",
            inicio=timezone.make_aware(datetime(2025, 10, 10, 14, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 10, 16, 0), self.tz),
            status="aprovado",
        )

        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="Fortaleza",
            destino="São Paulo",
            start_date=date(2025, 10, 10),
            end_date=date(2025, 10, 10),
        )

        # Dia 15: evento + bloqueio (sem deslocamento)
        solicitacao_day15 = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 15, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 15, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=solicitacao_day15,
            usuario=self.user_formador,
            role="FORMADOR",
        )

        AvailabilityBlock.objects.create(
            usuario=self.user_formador,
            tipo="T",
            inicio=timezone.make_aware(datetime(2025, 10, 15, 14, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 15, 16, 0), self.tz),
            status="aprovado",
        )

        # Build grid
        result = build_monthly_grid(year=2025, month=10, role="FORMADOR")

        # Validar
        cells = result["cells"][0]

        # Dia 10 (índice 9) deve ser "X"
        assert cells[9] == "X"

        # Dia 15 (índice 14) deve ser "X"
        assert cells[14] == "X"

    def test_precedence_order_comprehensive(self):
        """
        Valida ordem de precedência completa: X > D1 > 2 > E > T/P > D

        Cenário:
        - Dia 1: evento + bloqueio + deslocamento → X
        - Dia 2: evento + deslocamento (sem bloqueio) → D1
        - Dia 3: 2 eventos (sem bloqueio, sem deslocamento) → 2
        - Dia 4: 1 evento (sem bloqueio, sem deslocamento) → E
        - Dia 5: bloqueio total (sem evento, sem deslocamento) → T
        - Dia 6: deslocamento (sem evento, sem bloqueio) → D
        - Dia 7: vazio → ""
        """
        # Dia 1: X
        s1 = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 1, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 1, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(solicitacao=s1, usuario=self.user_formador, role="FORMADOR")
        AvailabilityBlock.objects.create(
            usuario=self.user_formador,
            tipo="P",
            inicio=timezone.make_aware(datetime(2025, 10, 1, 14, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 1, 16, 0), self.tz),
            status="aprovado",
        )
        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="A",
            destino="B",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 1),
        )

        # Dia 2: D1
        s2 = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 2, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 2, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(solicitacao=s2, usuario=self.user_formador, role="FORMADOR")
        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="C",
            destino="D",
            start_date=date(2025, 10, 2),
            end_date=date(2025, 10, 2),
        )

        # Dia 3: 2
        s3a = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 3, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 3, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(solicitacao=s3a, usuario=self.user_formador, role="FORMADOR")
        s3b = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 3, 14, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 3, 16, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(solicitacao=s3b, usuario=self.user_formador, role="FORMADOR")

        # Dia 4: E
        s4 = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 4, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 4, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(solicitacao=s4, usuario=self.user_formador, role="FORMADOR")

        # Dia 5: T
        AvailabilityBlock.objects.create(
            usuario=self.user_formador,
            tipo="T",
            inicio=timezone.make_aware(datetime(2025, 10, 5, 0, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 5, 23, 59), self.tz),
            status="aprovado",
        )

        # Dia 6: D
        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="E",
            destino="F",
            start_date=date(2025, 10, 6),
            end_date=date(2025, 10, 6),
        )

        # Build grid
        result = build_monthly_grid(year=2025, month=10, role="FORMADOR")

        # Validar
        cells = result["cells"][0]

        assert cells[0] == "X"  # Dia 1
        assert cells[1] == "D1"  # Dia 2
        assert cells[2] == "2"  # Dia 3
        assert cells[3] == "E"  # Dia 4
        assert cells[4] == "T"  # Dia 5
        assert cells[5] == "D"  # Dia 6
        assert cells[6] == ""  # Dia 7

    def test_deslocamento_multi_day(self):
        """
        Deslocamento de múltiplos dias (start_date != end_date)

        Cenário:
        - Deslocamento de 3 dias (dia 10-12)
        - Sem eventos, sem bloqueios

        Expectativa:
        - Dia 10, 11, 12: código "D"
        - Dia 9, 13: código ""
        """
        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="Fortaleza",
            destino="São Paulo",
            start_date=date(2025, 10, 10),
            end_date=date(2025, 10, 12),
        )

        # Criar participation em OUTUBRO para incluir usuário na grade
        solicitacao = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 20, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 20, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=solicitacao,
            usuario=self.user_formador,
            role="FORMADOR",
        )

        # Build grid
        result = build_monthly_grid(year=2025, month=10, role="FORMADOR")

        # Validar
        cells = result["cells"][0]

        # Dias 10, 11, 12 devem ser "D"
        assert cells[9] == "D"  # Dia 10
        assert cells[10] == "D"  # Dia 11
        assert cells[11] == "D"  # Dia 12

        # Dias 9 e 13 devem ser ""
        assert cells[8] == ""  # Dia 9
        assert cells[12] == ""  # Dia 13

    def test_deslocamento_only_in_month_range(self):
        """
        Deslocamento que ultrapassa limites do mês (start antes, end depois)

        Cenário:
        - Deslocamento: 28/set → 5/out
        - Grade: outubro/2025

        Expectativa:
        - Apenas dias 1-5 de outubro devem ter "D"
        """
        Deslocamento.objects.create(
            usuario=self.user_formador,
            origem="Fortaleza",
            destino="São Paulo",
            start_date=date(2025, 9, 28),
            end_date=date(2025, 10, 5),
        )

        # Criar participation em OUTUBRO para incluir usuário na grade
        solicitacao = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 20, 10, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 20, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=solicitacao,
            usuario=self.user_formador,
            role="FORMADOR",
        )

        # Build grid
        result = build_monthly_grid(year=2025, month=10, role="FORMADOR")

        # Validar
        cells = result["cells"][0]

        # Dias 1-5 devem ser "D"
        for day_idx in range(0, 5):
            assert cells[day_idx] == "D", f"Dia {day_idx + 1} deveria ser D"

        # Dia 6 deve ser ""
        assert cells[5] == ""
