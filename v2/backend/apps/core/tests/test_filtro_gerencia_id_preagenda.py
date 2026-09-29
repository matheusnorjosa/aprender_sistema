"""
PR A — a PreAgenda filtra lista e KPIs pelo mesmo `gerencia_id` (PLANOS_LIBERACAO_2026-09-29 §2).

Antes divergiam: a lista (`/solicitacoes/?sector=`) filtrava por
`projeto__gerencia__nome_setor__iexact` e o resumo (`/gcal/status-summary/?sector=`)
por `projeto__nome__icontains`. Agora os dois aceitam `gerencia_id`
(`projeto__gerencia_id`). O `sector` antigo continua aceito.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Solicitacao
from apps.core.tests.factories import ProjetoFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_SEQ = itertools.count(1)


def _gerencia(nome_setor: str) -> Gerencia:
    return Gerencia.objects.create(nome=f"GERENCIA PA {next(_SEQ)}", nome_setor=nome_setor)


def _aprovada(gerencia: Gerencia, nome_projeto: str | None = None) -> Solicitacao:
    projeto = ProjetoFactory(gerencia=gerencia, **({"nome": nome_projeto} if nome_projeto else {}))
    inicio = timezone.now() + timedelta(days=5)
    return SolicitacaoFactory(projeto=projeto, status="aprovado", inicio=inicio, fim=inicio + timedelta(hours=2))


@pytest.fixture
def client() -> APIClient:
    c = APIClient()
    c.force_authenticate(user=UsuarioFactory(superuser=True))
    return c


def _ids_da_lista(client: APIClient, params: dict) -> set[int]:
    resp = client.get("/api/solicitacoes/", {**params, "status": "aprovado", "page_size": 100})
    assert resp.status_code == 200, resp.data
    rows = resp.data["results"]
    return {r["id"] for r in rows}


def _total_do_resumo(client: APIClient, params: dict) -> int:
    resp = client.get("/api/gcal/status-summary/", params)
    assert resp.status_code == 200, resp.data
    return resp.data["total"]


def test_lista_e_resumo_filtram_pelo_mesmo_gerencia_id(client):
    alvo = _gerencia("ACerta")
    outra = _gerencia("Vidas")
    s1 = _aprovada(alvo)
    s2 = _aprovada(alvo)
    _aprovada(outra)

    params = {"gerencia_id": alvo.id}

    assert _ids_da_lista(client, params) == {s1.id, s2.id}
    assert _total_do_resumo(client, params) == 2


def test_projeto_com_nome_de_outro_setor_nao_vaza_no_resumo(client):
    """O resumo por `sector` casava substring no nome do projeto; `gerencia_id` não."""
    fluir = _gerencia("Fluir")
    vidas = _gerencia("Vidas")
    _aprovada(fluir, nome_projeto="Vidas em Fluir PA")
    s_vidas = _aprovada(vidas)

    params = {"gerencia_id": vidas.id}

    assert _ids_da_lista(client, params) == {s_vidas.id}
    assert _total_do_resumo(client, params) == 1


def test_sector_antigo_continua_aceito_na_lista(client):
    alvo = _gerencia("Setor Legado PA")
    s1 = _aprovada(alvo)
    _aprovada(_gerencia("Outro PA"))

    assert _ids_da_lista(client, {"sector": "setor legado pa"}) == {s1.id}


@pytest.mark.parametrize("valor", ["²", "abc", "-1", ""])
def test_gerencia_id_invalido_e_ignorado_sem_500(client, valor):
    """`'²'.isdigit()` é True mas `int('²')` estoura: o filtro ignora o valor inválido."""
    s1 = _aprovada(_gerencia("Qualquer PA"))

    assert s1.id in _ids_da_lista(client, {"gerencia_id": valor})
    assert _total_do_resumo(client, {"gerencia_id": valor}) >= 1
