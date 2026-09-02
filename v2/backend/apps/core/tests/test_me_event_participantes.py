"""MeEventSerializer.participantes — costura MeusEventos (Desktop escolheu contrato (a)).

Expõe [{role, nome}] de TODAS as participations do evento (não só formadores com usuario),
com `nome` na cascata usuario → guest_nome → guest_email (RELAY: guest que saiu sem guest_nome
não pode virar nome em branco). `role` = valores do enum Participation.Role.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportCallIssue=false, reportArgumentType=false

from __future__ import annotations

import pytest

from apps.core.models.solicitacao import Participation
from apps.core.serializers.me import MeEventSerializer
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def test_participantes_expoe_todos_os_papeis_com_cascata_de_nome():
    sol = SolicitacaoFactory()
    ana = UsuarioFactory(username="ana", first_name="Ana", last_name="Silva")
    Participation.objects.create(solicitacao=sol, usuario=ana, role=Participation.Role.FORMADOR)
    bruno = UsuarioFactory(username="bruno", first_name="Bruno", last_name="Costa")
    Participation.objects.create(solicitacao=sol, usuario=bruno, role=Participation.Role.COORDENADOR)
    # quem saiu: só guest_nome
    Participation.objects.create(solicitacao=sol, guest_nome="Quem Saiu", role=Participation.Role.CONVIDADO)
    # quem saiu sem guest_nome: cai para guest_email (não vira branco)
    Participation.objects.create(solicitacao=sol, guest_email="soemail@x.com", role=Participation.Role.CONVIDADO)

    parts = MeEventSerializer(sol).data["participantes"]

    assert all(set(p.keys()) == {"role", "nome"} for p in parts), "shape slim {role, nome}"
    by = {(p["role"], p["nome"]) for p in parts}
    assert ("FORMADOR", "Ana Silva") in by
    assert ("COORDENADOR", "Bruno Costa") in by
    assert ("CONVIDADO", "Quem Saiu") in by, "guest_nome preservado"
    assert ("CONVIDADO", "soemail@x.com") in by, "cascata usuario→guest_nome→guest_email"
    assert len(parts) == 4


def test_participantes_vazio_quando_sem_participacoes():
    sol = SolicitacaoFactory()
    assert MeEventSerializer(sol).data["participantes"] == []


def test_formadores_legado_intacto_nao_inclui_guests():
    """Guarda de não-regressão: o campo `formadores` (contrato antigo) NÃO passa a incluir guests."""
    sol = SolicitacaoFactory()
    ana = UsuarioFactory(username="ana2", first_name="Ana", last_name="Souza")
    Participation.objects.create(solicitacao=sol, usuario=ana, role=Participation.Role.FORMADOR)
    Participation.objects.create(solicitacao=sol, guest_nome="Formador Que Saiu", role=Participation.Role.FORMADOR)
    formadores = MeEventSerializer(sol).data["formadores"]
    assert formadores == ["Ana Souza"], "formadores legado = só usuario, sem guests"
