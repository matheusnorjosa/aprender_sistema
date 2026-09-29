"""
PR B1 — comando `relatorio_aprovadores` (somente leitura, sem CPF/e-mail/telefone).

Roda ANTES do deploy do B1: no deploy, todo GERENTE vigente na SUPERINTENDENCIA passa a
aprovar, então o dono confere a lista nome por nome. O relatório traz as 5 informações
da seção "Dado de produção" do plano:
1. quantas `Gerencia(nome="SUPERINTENDENCIA")` existem (esperado 1) e o id;
2. os GERENTEs vigentes nela, com id, nome e os outros papéis de cada um;
3. a comparação com `Gerencia.gerente` dessa gerência;
4. quantas pessoas aprovam só pelo composite de grupos (esperado 0);
5. as pendentes por fluxo (SUPER, NAO_SUPER, sem projeto) e quantas foram criadas
   pelos futuros aprovadores.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import json
from io import StringIO
from typing import Any

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
    assert gerentes[cenario["ana"].id]["nome"] == "Ana Aprovadora"
    assert gerentes[cenario["ana"].id]["outros_papeis"] == ["COORDENADOR em GERENCIA 2 REL"]

    assert dados["gerente_cadastrado"] == {
        "id": cenario["bia"].id,
        "nome": "Bia Gerente",
        "entre_os_gerentes_vigentes": True,
    }

    assert dados["so_composite_de_grupos"]["quantidade"] == 1
    assert dados["so_composite_de_grupos"]["ids"] == [cenario["so_grupo"].id]

    assert dados["pendentes_por_fluxo"] == {"SUPER": 2, "NAO_SUPER": 1, "sem_projeto": 1}
    assert dados["pendentes_criadas_por_futuros_aprovadores"] == {"SUPER": 1, "NAO_SUPER": 0, "sem_projeto": 0}


def test_relatorio_nao_expoe_cpf_email_nem_telefone(cenario):
    for saida in (_relatorio(), _relatorio("--json")):
        assert "52998224725" not in saida
        assert "ana@example.com" not in saida
        assert "85999990000" not in saida
        assert cenario["ana"].username not in saida


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
