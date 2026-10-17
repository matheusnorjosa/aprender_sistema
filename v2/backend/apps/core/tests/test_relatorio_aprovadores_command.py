"""
PR B1 / PR 11 — comando `relatorio_aprovadores` (somente leitura, só u<id>, sem cache).

O relatório é o retrato de `solicitation_approval_basis` e traz 5 informações:
1. quantas `Gerencia(nome="SUPERINTENDENCIA")` existem (esperado 1) e o id;
2. os GERENTEs vigentes nela, com id e os outros papéis de cada um;
3. a comparação com `Gerencia.gerente` dessa gerência;
4. os aprovadores por base (PR 11) e as contas inativas que aprovariam se reativadas;
5. as pendentes por fluxo (SUPER, NAO_SUPER, sem projeto) e quantas foram criadas
   pelos aprovadores.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import json
from io import StringIO
from typing import Any
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao
from apps.core.tests.factories import ProjetoFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _relatorio(*args: str) -> str:
    out = StringIO()
    call_command("relatorio_aprovadores", *args, stdout=out)
    return out.getvalue()


@pytest.fixture
def cenario() -> dict[str, Any]:
    g1, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    vidas = Gerencia.objects.create(nome="GERENCIA 2 REL", nome_setor="Vidas")
    ana = UsuarioFactory(first_name="Ana", last_name="Aprovadora", cpf="52998224725", email="ana@example.com")
    bia = UsuarioFactory(first_name="Bia", last_name="Gerente", telefone="85999990000")
    EquipeGerencia.objects.create(usuario=ana, gerencia=g1, papel="GERENTE")
    EquipeGerencia.objects.create(usuario=ana, gerencia=vidas, papel="COORDENADOR")
    EquipeGerencia.objects.create(usuario=bia, gerencia=g1, papel="GERENTE")
    g1.gerente = bia
    g1.save(update_fields=["gerente"])
    so_grupo = UsuarioFactory(first_name="Caio", groups=["Superintendência", "Gerente"])

    SolicitacaoFactory(usuario=ana, projeto=ProjetoFactory(fluxo="SUPER"))
    SolicitacaoFactory(projeto=ProjetoFactory(fluxo="SUPER"))
    SolicitacaoFactory(projeto=ProjetoFactory(fluxo="NAO_SUPER"))
    SolicitacaoFactory(projeto=None)
    SolicitacaoFactory(projeto=ProjetoFactory(fluxo="SUPER"), status="aprovado")
    return {"g1": g1, "ana": ana, "bia": bia, "so_grupo": so_grupo}


def test_relatorio_traz_as_cinco_informacoes(cenario):
    dados = json.loads(_relatorio("--json"))

    assert dados["gerencia_aprovadora"] == {"nome": "SUPERINTENDENCIA", "quantidade": 1, "ids": [cenario["g1"].id]}

    gerentes = {g["id"]: g for g in dados["gerentes_vigentes"]}
    assert set(gerentes) == {cenario["ana"].id, cenario["bia"].id}
    assert "nome" not in gerentes[cenario["ana"].id]
    assert gerentes[cenario["ana"].id]["outros_papeis"] == ["COORDENADOR em GERENCIA 2 REL"]

    assert dados["gerente_cadastrado"] == {"id": cenario["bia"].id, "entre_os_gerentes_vigentes": True}

    # PR 11: o par de grupos (Superintendência + Gerente) não aprova; o `so_grupo` não aparece.
    assert dados["aprovadores_por_base"] == {
        "superuser": [],
        "gerente_superintendencia": sorted([cenario["ana"].id, cenario["bia"].id]),
        "capacidade_aprovar": [],
    }
    assert dados["inativas_que_aprovariam_se_reativadas"] == []

    assert dados["pendentes_por_fluxo"] == {"SUPER": 2, "NAO_SUPER": 1, "sem_projeto": 1}
    assert dados["pendentes_criadas_por_aprovadores"] == {"SUPER": 1, "NAO_SUPER": 0, "sem_projeto": 0}


def test_relatorio_nao_expoe_nome_cpf_email_nem_telefone(cenario):
    for saida in (_relatorio(), _relatorio("--json")):
        assert "52998224725" not in saida
        assert "ana@example.com" not in saida
        assert "85999990000" not in saida
        assert cenario["ana"].username not in saida
        for nome in ("Ana", "Aprovadora", "Bia", "Caio"):
            assert nome not in saida


def test_relatorio_nao_le_nem_grava_o_cache(cenario):
    """PR 11 (M6): a base `capacidade_aprovar` vem de `capacidades_sem_cache`; nada passa pelo cache."""
    with patch("django.core.cache.cache.get") as get, patch("django.core.cache.cache.set") as set_:
        _relatorio("--json")
    assert not set_.called
    assert not get.called


def test_relatorio_e_somente_leitura(cenario):
    antes = Solicitacao.objects.count(), EquipeGerencia.objects.count()

    with CaptureQueriesContext(connection) as ctx:
        _relatorio()
        _relatorio("--json")

    escritas = [
        q["sql"] for q in ctx.captured_queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert escritas == []
    assert (Solicitacao.objects.count(), EquipeGerencia.objects.count()) == antes


def test_sem_gerencia_aprovadora_avisa_que_ninguem_novo_aprova():
    dados = json.loads(_relatorio("--json"))

    assert dados["gerencia_aprovadora"]["quantidade"] == 0
    assert dados["gerentes_vigentes"] == []
    assert "Nenhuma gerência" in _relatorio()
