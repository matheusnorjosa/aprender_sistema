"""
PR A — o dashboard "por gerência" mostra o rótulo da gerência (PLANOS_LIBERACAO_2026-09-29 §2).

Antes agrupava por `projeto__gerencia__nome` e a tela mostrava "GERENCIA 4" /
"INDIVIDUAL - X". Agora agrupa por gerência (id) e devolve `gerencia = rotulo`
(`nome_exibicao or nome_setor`). O contrato do endpoint não muda.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
import re
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia
from apps.core.tests.factories import ProjetoFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_SEQ = itertools.count(1)


def _gerencia(**kwargs) -> Gerencia:
    kwargs.setdefault("nome", f"GERENCIA {90 + next(_SEQ)}")
    return Gerencia.objects.create(**kwargs)


def _aprovadas(gerencia: Gerencia, quantidade: int) -> None:
    projeto = ProjetoFactory(gerencia=gerencia)
    inicio = timezone.now() - timedelta(days=2)
    for _ in range(quantidade):
        SolicitacaoFactory(projeto=projeto, status="aprovado", inicio=inicio, fim=inicio + timedelta(hours=2))


def test_por_gerencia_usa_rotulo_e_nao_funde_mesmo_nome_setor():
    individual_a = _gerencia(nome_setor="Individual")
    individual_b = _gerencia(nome_setor="Individual")
    acerta = _gerencia(nome_setor="ACerta", nome_exibicao="Superativar")
    _aprovadas(individual_a, 3)
    _aprovadas(individual_b, 2)
    _aprovadas(acerta, 1)

    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    resp = client.get("/api/dashboard/overview/")

    assert resp.status_code == 200, resp.data
    linhas = [(item["gerencia"], item["quantidade"]) for item in resp.data["por_gerencia"]]
    assert linhas == [("Individual", 3), ("Individual", 2), ("Superativar", 1)]
    assert not any(re.match(r"^GERENCIA \d", rotulo) for rotulo, _ in linhas)
