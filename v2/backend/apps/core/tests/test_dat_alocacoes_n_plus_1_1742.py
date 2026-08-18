"""
Teste de query-count (N+1) para GET /api/dat/coordenadores/{id}/alocacoes/ (#1742).

Fix sob teste (apps/core/views/dat_module.py — DATCoordenadorViewSet.alocacoes):
as querysets `coordenador.dat_acoes` e `coordenador.dat_formacoes` agora aplicam
`.select_related("municipio", "projeto", "created_by")`.

Prova do RED (por que falharia SEM o fix):
    DATAcaoListSerializer / DATFormacaoListSerializer acessam `obj.municipio.nome`
    e `obj.projeto.nome`. Sem `select_related`, cada linha serializada dispara 2
    queries extra (municipio + projeto), logo o total de queries CRESCE
    linearmente com o nº de linhas. A asserção `q_large == q_small` (contagem
    idêntica com 1 e com 7 linhas) só é verdadeira COM o select_related — sem ele,
    q_large ≈ q_small + 6*2 (ações) + 6*2 (formações).

Nota: `obj.coordenador.nome` também é acessado, mas o manager de FK reverso
(`coordenador.dat_acoes`) injeta a instância do coordenador via
`_known_related_objects`, então o coordenador NÃO gera N+1 e não precisa de
select_related.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, time

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import DATAcao, DATCoordenador, DATFormacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    UsuarioFactory,
)


class DATAlocacoesNPlusOneTests(APITestCase):
    """Garante que o endpoint alocacoes não sofre N+1 nas FKs municipio/projeto."""

    @classmethod
    def setUpTestData(cls):
        # Grupo DAT concede `manage_admin_registries` (via seed RBAC das fixtures),
        # que é o permission requerido pelo @action alocacoes.
        cls.dat_group = GroupFactory(name="DAT")
        cls.dat_user = UsuarioFactory(username="dat_np1_1742", cpf="90000000101", groups=["DAT"])
        cls.coordenador = DATCoordenador.objects.create(
            nome="Coordenador N+1 1742",
            email="coord_np1_1742@test.com",
            area="DAT",
            created_by=cls.dat_user,
        )

    def _add_alocacoes(self, n: int) -> None:
        """Cria n ações + n formações ligadas ao coordenador, cada uma com
        município/projeto DISTINTOS (obriga uma query por FK sem select_related e
        respeita o UniqueConstraint (municipio, projeto) de DATAcao)."""
        for _ in range(n):
            municipio = MunicipioFactory()
            projeto = ProjetoFactory()
            DATAcao.objects.create(
                municipio=municipio,
                projeto=projeto,
                coordenador=self.coordenador,
                created_by=self.dat_user,
            )
            DATFormacao.objects.create(
                municipio=municipio,
                projeto=projeto,
                coordenador=self.coordenador,
                created_by=self.dat_user,
                titulo="Formação N+1 1742",
                data_formacao=date(2026, 1, 1),
                horario_inicio=time(9, 0),
                horario_fim=time(12, 0),
            )

    def test_alocacoes_query_count_is_independent_of_row_count(self):
        """A contagem de queries NÃO cresce com o nº de linhas (N+1 resolvido)."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-coordenador-alocacoes", args=[self.coordenador.id])

        # Baseline: 1 alocação. Warmup para estabilizar caches one-time
        # (content types, permissões) que poderiam poluir a 1ª medição.
        self._add_alocacoes(1)
        self.client.get(url)  # warmup (descartado)

        with CaptureQueriesContext(connection) as ctx_small:
            resp_small = self.client.get(url)
        self.assertEqual(resp_small.status_code, status.HTTP_200_OK)
        q_small = len(ctx_small.captured_queries)

        # +6 alocações → total 7 (ainda dentro do slice [:10] do endpoint).
        self._add_alocacoes(6)

        with CaptureQueriesContext(connection) as ctx_large:
            resp_large = self.client.get(url)
        self.assertEqual(resp_large.status_code, status.HTTP_200_OK)
        q_large = len(ctx_large.captured_queries)

        # Sanidade: as 7 linhas realmente foram serializadas.
        self.assertEqual(len(resp_large.data["acoes"]), 7)
        self.assertEqual(len(resp_large.data["formacoes"]), 7)
        self.assertEqual(resp_large.data["total_acoes"], 7)
        self.assertEqual(resp_large.data["total_formacoes"], 7)

        # Núcleo do teste: com select_related a contagem é constante.
        # Sem o fix, q_large ≈ q_small + 24 (municipio+projeto por linha extra).
        self.assertEqual(
            q_large,
            q_small,
            f"N+1 detectado: {q_small} queries com 1 linha vs {q_large} com 7 linhas "
            f"(diferença de {q_large - q_small} indica FK sem select_related).",
        )
        # Defesa extra: limite absoluto baixo (o baseline constante fica ~6-9).
        self.assertLessEqual(q_large, 12)
