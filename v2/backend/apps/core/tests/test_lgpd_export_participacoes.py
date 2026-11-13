"""SEG-10 / ART-17 — o dossiê do titular (LGPD art. 18, II e V) traz os eventos em que ele participa.

A participação mora em `Participation` (papéis COORDENADOR, FORMADOR, COORD_ACOMPANHA e CONVIDADO). O
dossiê lia o M2M `Solicitacao.formadores`, que ninguém grava: em 13/11/2026 ele tinha 0 linhas em produção,
contra cerca de 16 mil participações de 137 pessoas. Quem baixava os próprios dados recebia a lista de
eventos vazia.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportIndexIssue=false

from __future__ import annotations

import json
from decimal import Decimal

from django.core.management import call_command
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Participation
from apps.core.services.lgpd_export_service import build_lgpd_export_data, export_counts
from apps.core.tests.factories import ProjetoFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _participa(sol, usuario, role, **extra):
    return Participation.objects.create(solicitacao=sol, usuario=usuario, role=role, **extra)


def test_dossie_traz_as_participacoes_do_titular_em_todos_os_papeis():
    titular = UsuarioFactory()
    eventos = {role: SolicitacaoFactory() for role in Participation.Role.values}
    for role, sol in eventos.items():
        _participa(sol, titular, role)

    linhas = build_lgpd_export_data(titular, include_audit=False)["event_participations"]

    assert sorted((linha["solicitacao_id"], linha["role"]) for linha in linhas) == sorted(
        (sol.pk, role) for role, sol in eventos.items()
    )


def test_dossie_traz_os_dados_do_evento_e_da_participacao():
    titular = UsuarioFactory()
    sol = SolicitacaoFactory(projeto_2=ProjetoFactory())
    _participa(sol, titular, Participation.Role.FORMADOR, ch_horas=Decimal("4.50"), observacao="levou o material")

    [linha] = build_lgpd_export_data(titular, include_audit=False)["event_participations"]

    assert linha["solicitacao__status"] == sol.status
    assert linha["solicitacao__inicio"] == sol.inicio.isoformat()
    assert linha["solicitacao__fim"] == sol.fim.isoformat()
    assert linha["solicitacao__municipio__nome"] == sol.municipio.nome
    assert linha["solicitacao__projeto__nome"] == sol.projeto.nome
    assert linha["solicitacao__projeto_2__nome"] == sol.projeto_2.nome
    assert linha["solicitacao__tipo_evento__nome"] == sol.tipo_evento.nome
    assert linha["ch_horas"] == 4.5
    assert linha["observacao"] == "levou o material"


def test_dossie_nao_traz_participacao_de_outra_pessoa():
    titular, colega = UsuarioFactory(), UsuarioFactory()
    sol = SolicitacaoFactory()
    _participa(sol, titular, Participation.Role.COORDENADOR)
    _participa(sol, colega, Participation.Role.FORMADOR, observacao="nota sobre a colega")
    _participa(SolicitacaoFactory(), colega, Participation.Role.CONVIDADO)

    data = build_lgpd_export_data(titular, include_audit=False)

    assert [(linha["solicitacao_id"], linha["role"]) for linha in data["event_participations"]] == [
        (sol.pk, Participation.Role.COORDENADOR)
    ]
    assert "nota sobre a colega" not in json.dumps(data)


def test_trilha_conta_as_participacoes():
    titular = UsuarioFactory()
    for _ in range(3):
        _participa(SolicitacaoFactory(), titular, Participation.Role.CONVIDADO)

    data = build_lgpd_export_data(titular, include_audit=False)

    assert export_counts(data)["event_participations"] == 3


def test_download_do_proprio_titular_traz_as_participacoes():
    titular = UsuarioFactory()
    sol = SolicitacaoFactory()
    _participa(sol, titular, Participation.Role.FORMADOR)
    client = APIClient()
    client.force_authenticate(user=titular)

    body = json.loads(client.get("/api/me/export/").content)

    assert [linha["solicitacao_id"] for linha in body["event_participations"]] == [sol.pk]
    log = AuditLog.objects.filter(usuario=titular, action=AuditLog.Action.EXPORT).latest("created_at")
    assert log.details["counts"]["event_participations"] == 1


def test_comando_do_admin_conta_as_participacoes(tmp_path):
    titular = UsuarioFactory(cpf="11144477735")  # o mesmo CPF de exemplo de test_me_export.py
    _participa(SolicitacaoFactory(), titular, Participation.Role.COORDENADOR)
    out = tmp_path / "export.json"

    call_command("lgpd_export", cpf="11144477735", output=str(out))

    assert [linha["role"] for linha in json.loads(out.read_text(encoding="utf-8"))["event_participations"]] == [
        Participation.Role.COORDENADOR
    ]
