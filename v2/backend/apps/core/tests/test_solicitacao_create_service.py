"""
Tests for solicitacao creation status decision service (ASQ-002).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

import pytest

from apps.core.models import Solicitacao
from apps.core.services.solicitacao_create import resolve_initial_status
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def test_resolve_initial_status_nao_super_returns_aprovado():
    projeto = ProjetoFactory(nome="Projeto NS", fluxo="NAO_SUPER", ativo=True)

    decision = resolve_initial_status(projeto=projeto)

    assert decision.status == "aprovado"
    assert decision.fluxo == "NAO_SUPER"
    assert decision.reason == "projeto_fluxo_nao_super"


def test_resolve_initial_status_super_returns_pendente():
    projeto = ProjetoFactory(nome="Projeto SUPER", fluxo="SUPER", ativo=True)

    decision = resolve_initial_status(projeto=projeto)

    assert decision.status == "pendente"
    assert decision.fluxo == "SUPER"
    assert decision.reason == "default_or_super_flow"


def test_model_create_without_status_no_longer_auto_approves_nao_super():
    user = UsuarioFactory(
        username="status_model_test",
        password="testpass123",
        cpf="12312312312",
        email="status_model_test@example.com",
    )
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    projeto = ProjetoFactory(nome="Projeto NS Model", fluxo="NAO_SUPER", ativo=True)
    tipo_evento = TipoEventoFactory(nome="Formacao")

    solicitacao = Solicitacao.objects.create(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.now() + timedelta(days=1),
        fim=timezone.now() + timedelta(days=1, hours=2),
    )

    assert solicitacao.status == "pendente"
