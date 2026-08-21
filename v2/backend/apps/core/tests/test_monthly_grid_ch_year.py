"""M14-03 (#1663): CH Ano da grade mensal deve somar o ANO inteiro.

O queryset `events` do serviço só intersecta o mês consultado, então acumular
`ch_year` sobre ele contava um único mês (CH Ano ≈ CH Mês). Este teste fixa o
contrato: CH Ano soma todos os eventos do ano; CH Mês, só os do mês.
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportIndexIssue=false, reportArgumentType=false

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

import pytest

from apps.core.models import Participation
from apps.core.services.monthly_grid_service import build_monthly_grid
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)


@pytest.mark.django_db
class TestMonthlyGridChYear:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tz = timezone.get_current_timezone()
        self.user_formador = UsuarioFactory(
            username="formador_chyear",
            email="formador_chyear@example.com",
            password="password123",
        )
        self.municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
        # fluxo=SUPER é obrigatório: o fallback de população da grade só considera
        # participações em eventos SUPER (senão a grade volta vazia — falso verde).
        self.projeto = ProjetoFactory(nome="Projeto ChYear", ativo=True, fluxo="SUPER")
        self.tipo_evento = TipoEventoFactory(nome="Formação", cor="#FF0000")

    def _evento_4h(self, mes: int, dia: int):
        sol = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2026, mes, dia, 8, 0), self.tz),
            fim=timezone.make_aware(datetime(2026, mes, dia, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(
            solicitacao=sol,
            usuario=self.user_formador,
            role="FORMADOR",
        )
        return sol

    def test_ch_year_soma_o_ano_inteiro_nao_so_o_mes(self):
        # Mesmo formador, 2 eventos de 4h: um em março (mês consultado) e outro
        # em janeiro (fora do mês, dentro do ano).
        self._evento_4h(mes=3, dia=10)
        self._evento_4h(mes=1, dia=15)

        result = build_monthly_grid(year=2026, month=3, role="FORMADOR")
        person = next(p for p in result["people"] if p["id"] == self.user_formador.id)

        # CH Mês = só março (4h). CH Ano = março + janeiro (8h).
        assert person["ch_month"] == 4.0
        assert person["ch_year"] == 8.0
        assert person["ch_year"] > person["ch_month"]
