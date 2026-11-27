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

from django.db import connection
from django.test.utils import CaptureQueriesContext
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

        # Details para D1: o evento e o deslocamento (27/11/2026)
        detail_key_day10 = "0:9"
        assert detail_key_day10 in result["details_index"]
        assert [item["tipo_item"] for item in result["details_index"][detail_key_day10]] == ["evento", "deslocamento"]

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

    def test_evento_com_dois_participantes_nao_multiplica(self):
        """M14-02 (#1630): evento com 2+ participantes não pode multiplicar CH,
        código nem detalhes por participante.

        O JOIN Solicitacao × Participation materializa o mesmo evento uma vez
        por participante; sem `.distinct()` cada cópia era distribuída de novo,
        inflando CH (×N), virando o código "2" em vez de "E" e duplicando os
        detalhes. Invariante: um evento conta UMA vez para cada participante.
        """
        u2 = UsuarioFactory(
            username="formador2",
            email="formador2@example.com",
            password="password123",
        )

        # 1 evento de 4h no dia 15, com DOIS formadores participantes.
        sol = SolicitacaoFactory(
            usuario=self.user_formador,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, 15, 8, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 15, 12, 0), self.tz),
            status="aprovado",
        )
        for u in (self.user_formador, u2):
            Participation.objects.create(solicitacao=sol, usuario=u, role="FORMADOR")

        result = build_monthly_grid(year=2025, month=10, role="FORMADOR")

        assert len(result["people"]) == 2
        row_of = {p["id"]: idx for idx, p in enumerate(result["people"])}

        for uid in (self.user_formador.id, u2.id):
            row = row_of[uid]
            # Dia 15 (índice 14): UM evento → "E", nunca "2".
            assert result["cells"][row][14] == "E"
            # CH contada uma vez (4h), não 8h.
            assert result["people"][row]["ch_month"] == 4.0
            # Detalhes com uma entrada, não duplicada.
            assert len(result["details_index"][f"{row}:14"]) == 1


@pytest.mark.django_db
class TestDetalheDeTodaCelula:
    """Grade enxuta (27/11/2026): todo quadradinho com código abre detalhe.

    Cada item tem `tipo_item` ("evento", "deslocamento" ou "bloqueio"); na célula vêm os eventos,
    depois os deslocamentos, depois os bloqueios. O motivo do bloqueio e a observação do
    deslocamento podem ser pessoais: nunca saem na grade.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tz = timezone.get_current_timezone()
        self.pessoa = UsuarioFactory(first_name="Pessoa", last_name="Ficticia")
        self.municipio = MunicipioFactory(nome="Sobral", uf="CE", ativo=True)
        self.projeto = ProjetoFactory(nome="Projeto Detalhe", ativo=True, fluxo="SUPER")
        self.tipo_evento = TipoEventoFactory(nome="Formação")
        # Evento no dia 20 só para a pessoa entrar na grade (fluxo SUPER).
        self.evento_20 = self._evento(20)

    def _evento(self, dia: int):
        sol = SolicitacaoFactory(
            usuario=self.pessoa,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio=timezone.make_aware(datetime(2025, 10, dia, 8, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, dia, 12, 0), self.tz),
            status="aprovado",
        )
        Participation.objects.create(solicitacao=sol, usuario=self.pessoa, role="FORMADOR")
        return sol

    def _bloqueio(self, dia: int, tipo: str):
        return AvailabilityBlock.objects.create(
            usuario=self.pessoa,
            tipo=tipo,
            inicio=timezone.make_aware(datetime(2025, 10, dia, 14, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, dia, 18, 0), self.tz),
            motivo="Consulta médica",
            status="aprovado",
        )

    def _deslocamento(self, dia: int):
        return Deslocamento.objects.create(
            usuario=self.pessoa,
            origem="Fortaleza",
            destino="Sobral",
            start_date=date(2025, 10, dia),
            end_date=date(2025, 10, dia + 1),
            meio_transporte=Deslocamento.MeioTransporte.ONIBUS,
            observacao="Volta mais cedo por assunto de família",
        )

    def _celula(self, dia: int):
        grade = build_monthly_grid(year=2025, month=10, role="FORMADOR")
        return grade["cells"][0][dia - 1], grade["details_index"].get(f"0:{dia - 1}")

    def test_D_traz_o_deslocamento_sem_observacao(self):
        desloc = self._deslocamento(10)

        codigo, detalhe = self._celula(10)

        assert codigo == "D"
        assert detalhe == [
            {
                "tipo_item": "deslocamento",
                "id": desloc.pk,
                "origem": "Fortaleza",
                "destino": "Sobral",
                "inicio": "2025-10-10",
                "fim": "2025-10-11",
                "meio_transporte": "Ônibus",
            }
        ]
        assert "observacao" not in str(detalhe)
        assert "família" not in str(detalhe)

    @pytest.mark.parametrize(("tipo", "rotulo"), [("P", "Parcial"), ("T", "Total")])
    def test_P_e_T_trazem_o_bloqueio_sem_motivo(self, tipo, rotulo):
        bloqueio = self._bloqueio(5, tipo)

        codigo, detalhe = self._celula(5)

        assert codigo == tipo
        assert detalhe == [
            {
                "tipo_item": "bloqueio",
                "id": bloqueio.pk,
                "tipo": rotulo,
                "data_inicio": "2025-10-05",
                "data_fim": "2025-10-05",
                "inicio": "14:00",
                "fim": "18:00",
            }
        ]
        assert "motivo" not in str(detalhe)
        assert "Consulta" not in str(detalhe)

    def test_bloqueio_de_varios_dias_traz_as_datas_no_dia_do_meio(self):
        """Bloqueio de 10/10 08:00 a 12/10 17:00: no dia 11, só HH:MM diria "08:00 a 17:00"."""
        bloqueio = AvailabilityBlock.objects.create(
            usuario=self.pessoa,
            tipo="T",
            inicio=timezone.make_aware(datetime(2025, 10, 10, 8, 0), self.tz),
            fim=timezone.make_aware(datetime(2025, 10, 12, 17, 0), self.tz),
            motivo="Consulta médica",
            status="aprovado",
        )

        codigo, detalhe = self._celula(11)

        assert codigo == "T"
        assert detalhe == [
            {
                "tipo_item": "bloqueio",
                "id": bloqueio.pk,
                "tipo": "Total",
                "data_inicio": "2025-10-10",
                "data_fim": "2025-10-12",
                "inicio": "08:00",
                "fim": "17:00",
            }
        ]
        assert "Consulta" not in str(detalhe)

    def test_X_traz_evento_e_depois_bloqueio(self):
        evento = self._evento(15)
        bloqueio = self._bloqueio(15, "T")

        codigo, detalhe = self._celula(15)

        assert codigo == "X"
        assert [(item["tipo_item"], item["id"]) for item in detalhe] == [
            ("evento", evento.pk),
            ("bloqueio", bloqueio.pk),
        ]

    def test_D1_traz_evento_e_depois_deslocamento(self):
        evento = self._evento(12)
        desloc = self._deslocamento(12)

        codigo, detalhe = self._celula(12)

        assert codigo == "D1"
        assert [(item["tipo_item"], item["id"]) for item in detalhe] == [
            ("evento", evento.pk),
            ("deslocamento", desloc.pk),
        ]

    def test_evento_mantem_os_campos_de_antes_e_ganha_tipo_item(self):
        codigo, detalhe = self._celula(20)

        assert codigo == "E"
        assert detalhe == [
            {
                "tipo_item": "evento",
                "id": self.evento_20.pk,
                "municipio": "Sobral",
                "data": "2025-10-20",
                "inicio": "08:00",
                "fim": "12:00",
                "tipo": "Formação",
            }
        ]


@pytest.mark.django_db
class TestPosicaoNoMesComBusca:
    """A posição no mês é sobre as pessoas da grade, antes da busca por nome (2ª revisão do PR 8).

    Antes, o ranking era feito depois do `q`: quem a busca achava ficava sempre em 1º.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        tz = timezone.get_current_timezone()
        municipio = MunicipioFactory(nome="Iguatu", uf="CE", ativo=True)
        projeto = ProjetoFactory(nome="Projeto Ranking", ativo=True, fluxo="SUPER")
        tipo_evento = TipoEventoFactory(nome="Formação")
        # Horas no mês: Alfa 6h, Beta 4h, Gama 2h.
        for nome, horas in (("Alfa", 6), ("Beta", 4), ("Gama", 2)):
            pessoa = UsuarioFactory(first_name=nome, last_name="Ranking")
            sol = SolicitacaoFactory(
                usuario=pessoa,
                municipio=municipio,
                projeto=projeto,
                tipo_evento=tipo_evento,
                inicio=timezone.make_aware(datetime(2025, 10, 7, 8, 0), tz),
                fim=timezone.make_aware(datetime(2025, 10, 7, 8 + horas, 0), tz),
                status="aprovado",
            )
            Participation.objects.create(solicitacao=sol, usuario=pessoa, role="FORMADOR")

    def test_busca_nao_muda_a_posicao(self):
        sem_busca = build_monthly_grid(year=2025, month=10, role="FORMADOR")
        posicao = {p["name"]: p["position_month"] for p in sem_busca["people"]}
        assert posicao == {"Alfa Ranking": 1, "Beta Ranking": 2, "Gama Ranking": 3}

        com_busca = build_monthly_grid(year=2025, month=10, role="FORMADOR", q="gama")

        assert [(p["name"], p["ch_month"], p["position_month"]) for p in com_busca["people"]] == [
            ("Gama Ranking", 2.0, 3)
        ]

    def test_busca_acrescenta_no_maximo_uma_consulta(self, django_assert_max_num_queries):
        with CaptureQueriesContext(connection) as sem_busca:
            build_monthly_grid(year=2025, month=10, role="FORMADOR")

        # A busca só acrescenta a consulta que filtra os nomes.
        with django_assert_max_num_queries(len(sem_busca) + 1):
            build_monthly_grid(year=2025, month=10, role="FORMADOR", q="gama")
