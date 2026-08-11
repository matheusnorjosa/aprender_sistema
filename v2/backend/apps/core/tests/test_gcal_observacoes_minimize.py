"""LGPD arts. 6-III/33 — minimização de PII incidental em `observacoes` no payload GCal.

O texto livre `observacoes` (autoria do coordenador) vai verbatim para a descrição do
evento transferida ao Google. Nomes da equipe e attendees são NECESSÁRIOS (visibilidade
na agenda + notificação) e permanecem. Mas CPF/e-mail digitados incidentalmente nas notas
NÃO são necessários ao agendamento — este teste TRAVA a redação desses padrões antes da
transferência, preservando o restante da nota.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import pytest

from apps.core.services.gcal.minimize import minimize_free_text
from apps.core.services.gcal.payload import build_event_payload
from apps.core.tests.factories import SolicitacaoFactory

# ------------------------- unidade: minimize_free_text -------------------------


def test_minimize_redige_cpf_raw_11_digitos():
    out = minimize_free_text("Responsavel CPF 11144477735 confirmar presenca")
    assert "11144477735" not in out
    assert "Responsavel CPF" in out and "confirmar presenca" in out


def test_minimize_redige_cpf_formatado():
    out = minimize_free_text("doc 111.444.777-35 do participante")
    assert "111.444.777-35" not in out
    assert "do participante" in out


def test_minimize_redige_email():
    out = minimize_free_text("contato joao@gmail.com para ajustes")
    assert "joao@gmail.com" not in out
    assert "para ajustes" in out


def test_minimize_preserva_texto_sem_pii():
    txt = "Trazer materiais de apoio e chegar 30 min antes"
    assert minimize_free_text(txt) == txt


def test_minimize_trata_none_e_vazio():
    assert minimize_free_text("") == ""
    assert minimize_free_text(None) == ""


# ------------------------- integração: payload GCal -------------------------


@pytest.mark.django_db
def test_payload_description_nao_vaza_cpf_nem_email_de_observacoes():
    sol = SolicitacaoFactory(
        status="aprovado",
        observacoes="Substituto joao.pessoal@gmail.com, CPF 11144477735. Levar material.",
    )
    payload = build_event_payload(sol)
    desc = payload["description"]

    assert "11144477735" not in desc, "CPF vazou na descrição transferida ao Google"
    assert "joao.pessoal@gmail.com" not in desc, "e-mail vazou na descrição transferida ao Google"
    # O conteúdo operacional legítimo permanece.
    assert "Levar material" in desc


@pytest.mark.django_db
def test_payload_preserva_observacoes_sem_pii():
    sol = SolicitacaoFactory(status="aprovado", observacoes="Reuniao de alinhamento previa")
    payload = build_event_payload(sol)
    assert "Reuniao de alinhamento previa" in payload["description"]
