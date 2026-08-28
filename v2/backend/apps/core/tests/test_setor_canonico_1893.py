"""
#1893 — Gerencia.setor_canonico + Projeto.setor (lados do gate de setor por canônico).

Design SEM regressão: `ProjetoSerializer.get_setor` passa a preferir o campo do model
`Projeto.setor` (populado pelo import v15), com FALLBACK para o derivado da gerência
(`gerencia.nome_setor`). Enquanto `Projeto.setor` não estiver populado, a saída da API é
idêntica à de hoje. Ambos os campos usam o vocabulário canônico `SETOR_GROUPS`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

import pytest

from apps.core.models import Gerencia, Projeto
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


class TestGetSetorPrefersModelField:
    def test_uses_projeto_setor_when_set(self):
        p = ProjetoFactory(nome="P-1893b", codigo="P1893b", fluxo="NAO_SUPER", ativo=True, setor="Vidas")
        assert ProjetoSerializer(p).data["setor"] == "Vidas", "campo do model é autoritativo quando preenchido"

    def test_falls_back_to_gerencia_when_projeto_setor_empty(self):
        g = Gerencia.objects.create(nome="G-1893c", nome_setor="ACerta")
        p = ProjetoFactory(nome="P-1893c", codigo="P1893c", fluxo="NAO_SUPER", ativo=True, gerencia=g, setor="")
        assert ProjetoSerializer(p).data["setor"] == "ACerta", "fallback preserva o comportamento de hoje"
