"""
Tests for solicitacao creation status decision service (ASQ-002).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

import pytest

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.services.solicitacao_create import resolve_initial_status

pytestmark = pytest.mark.django_db


def test_resolve_initial_status_nao_super_returns_aprovado():
    projeto = Projeto.objects.create(nome="Projeto NS", fluxo="NAO_SUPER", ativo=True)

    decision = resolve_initial_status(projeto=projeto)

    assert decision.status == "aprovado"
    assert decision.fluxo == "NAO_SUPER"
    assert decision.reason == "projeto_fluxo_nao_super"


def test_resolve_initial_status_super_returns_pendente():
    projeto = Projeto.objects.create(nome="Projeto SUPER", fluxo="SUPER", ativo=True)

    decision = resolve_initial_status(projeto=projeto)

    assert decision.status == "pendente"
    assert decision.fluxo == "SUPER"
    assert decision.reason == "default_or_super_flow"


def test_model_create_without_status_no_longer_auto_approves_nao_super():
    user = Usuario.objects.create_user(
        username="status_model_test",
        password="testpass123",
        cpf="12312312312",
        email="status_model_test@example.com",
    )
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto NS Model", fluxo="NAO_SUPER", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formacao")

    solicitacao = Solicitacao.objects.create(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.now() + timedelta(days=1),
        fim=timezone.now() + timedelta(days=1, hours=2),
    )

    assert solicitacao.status == "pendente"
