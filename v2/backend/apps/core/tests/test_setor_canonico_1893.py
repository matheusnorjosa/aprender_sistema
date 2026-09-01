"""
#1893 — Gerencia.setor_canonico + Projeto.setor (lados do gate de setor por canônico).

Design com split read/write (guarda anti-M17, #1914): `Projeto.setor` (campo do model,
populado pelo import v15) é GRAVÁVEL e a serialização de `setor` devolve o valor ARMAZENADO.
A derivação com FALLBACK para `gerencia.nome_setor` vive no campo read-only `setor_efetivo`
(exibição), sem contaminar o raw. `setor_canonico`/`Projeto.setor` usam o vocabulário
setor-de-PRODUTO (RELAY 28), não os 13 grupos RBAC.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

import pytest

from apps.core.models import Gerencia
from apps.core.serializers import ProjetoSerializer
from apps.core.tests.factories import ProjetoFactory

pytestmark = pytest.mark.django_db


class TestNewFields:
    def test_gerencia_setor_canonico_defaults_blank(self):
        g = Gerencia.objects.create(nome="G-Teste-1893", nome_setor="Vidas")
        assert g.setor_canonico == ""

    def test_projeto_setor_defaults_blank(self):
        p = ProjetoFactory(nome="P-1893", codigo="P1893", fluxo="NAO_SUPER", ativo=True)
        assert p.setor == ""

    def test_accepts_product_setor_vocabulary_not_in_rbac_groups(self):
        # RELAY 28: setor_canonico fala o vocabulário de setor-de-PRODUTO (11), NÃO os 13 grupos
        # RBAC (SETOR_GROUPS). "GESTÃO ESCOLAR" vem do de-para mas não é grupo — deve ser aceito
        # (sem choices=SETOR_GROUPS, que barraria 5 dos 11 valores reais).
        p = ProjetoFactory(nome="P-1893d", codigo="P1893d", fluxo="NAO_SUPER", ativo=True, setor="GESTÃO ESCOLAR")
        assert ProjetoSerializer(p).data["setor"] == "GESTÃO ESCOLAR"
        g = Gerencia.objects.create(nome="G-1893d", nome_setor="x", setor_canonico="GESTÃO ESCOLAR")
        assert g.setor_canonico == "GESTÃO ESCOLAR"


class TestGetSetorPrefersModelField:
    def test_uses_projeto_setor_when_set(self):
        p = ProjetoFactory(nome="P-1893b", codigo="P1893b", fluxo="NAO_SUPER", ativo=True, setor="Vidas")
        assert ProjetoSerializer(p).data["setor"] == "Vidas", "campo do model é autoritativo quando preenchido"

    def test_falls_back_to_gerencia_when_projeto_setor_empty(self):
        # #1914: split anti-M17 — `setor` (raw) devolve o valor ARMAZENADO (vazio); a derivação
        # (fallback da gerência) vive em `setor_efetivo` (read-only), para o modal editar o raw
        # sem contaminar a derivação.
        g = Gerencia.objects.create(nome="G-1893c", nome_setor="ACerta")
        p = ProjetoFactory(nome="P-1893c", codigo="P1893c", fluxo="NAO_SUPER", ativo=True, gerencia=g, setor="")
        data = ProjetoSerializer(p).data
        assert data["setor"] == "", "read do raw `setor` NÃO deriva (guarda anti-M17)"
        assert data["setor_efetivo"] == "ACerta", "fallback preservado no campo derivado read-only"
