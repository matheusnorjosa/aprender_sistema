"""#1914 (BE) — duas costuras de setor canônico no serializer de organização.

1. `Gerencia.setor_canonico_confianca` — sinal de confiança do de-para v15 (RELAY 50, item 8:
   ÚNICO sinal, SEM entrada-direta). É populado por IMPORT e apenas EXIBIDO na conferência; o
   usuário não digita → deve ser READ-ONLY no serializer (companheiro de `setor_canonico`).

2. `Projeto.setor` GRAVÁVEL com split read/write (guarda anti-M17). Hoje `setor` é
   `SerializerMethodField` read-only que DERIVA (`obj.setor or gerencia.nome_setor`). Se ficasse
   derivado E gravável, um round-trip do modal de edição escreveria o valor DERIVADO no campo raw
   (contaminação M17). O contrato correto: `setor` = campo raw gravável (read devolve o valor
   ARMAZENADO, não o derivado → round-trip seguro); a derivação vira `setor_efetivo` (read-only),
   preservando o fallback #1893 sem contaminar.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportCallIssue=false, reportArgumentType=false, reportOperatorIssue=false

from __future__ import annotations

import pytest

from apps.core.models.organizacao import Gerencia
from apps.core.serializers.organizacao import GerenciaSerializer, ProjetoSerializer
from apps.core.tests.factories import ProjetoFactory


@pytest.mark.django_db
def test_gerencia_setor_canonico_confianca_present_and_read_only() -> None:
    g = Gerencia.objects.create(nome="G-CONF-1", nome_setor="Vidas")
    data = GerenciaSerializer(g).data
    assert "setor_canonico_confianca" in data, "campo ausente do GerenciaSerializer"
    assert data["setor_canonico_confianca"] == "", "default deve ser string vazia"
    # sinal importado, sem entrada-direta → não aceita write pela API
    assert GerenciaSerializer().fields["setor_canonico_confianca"].read_only is True


@pytest.mark.django_db
def test_projeto_setor_read_is_raw_not_derived() -> None:
    """Anti-M17: `setor` read devolve o valor ARMAZENADO (vazio), NÃO o derivado."""
    g = Gerencia.objects.create(nome="G-CONF-2", nome_setor="Vidas")
    p = ProjetoFactory(gerencia=g, setor="")
    data = ProjetoSerializer(p).data
    assert data["setor"] == "", "read de `setor` deve ser o raw ('' ), não o derivado"
    assert data["setor_efetivo"] == "Vidas", "derivação preservada em campo read-only separado"


@pytest.mark.django_db
def test_projeto_setor_read_returns_stored_when_set() -> None:
    g = Gerencia.objects.create(nome="G-CONF-3", nome_setor="Vidas")
    p = ProjetoFactory(gerencia=g, setor="ACerta")
    data = ProjetoSerializer(p).data
    assert data["setor"] == "ACerta"
    assert data["setor_efetivo"] == "ACerta"


def test_projeto_setor_is_writable_and_efetivo_is_read_only() -> None:
    fields = ProjetoSerializer().fields
    assert "setor" in fields and fields["setor"].read_only is False, "`setor` deve ser gravável"
    assert (
        "setor_efetivo" in fields and fields["setor_efetivo"].read_only is True
    ), "`setor_efetivo` deve ser read-only (derivação, não contamina o raw)"
