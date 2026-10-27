"""Evento que está no Google Agenda pela planilha (`publicado_fora_do_sistema`) não se edita pela API.

Decisão do dono de 19/10/2026 (item 36): ele segue a regra do evento publicado pelo sistema. A tela já
escondia o Editar (Minhas Solicitações); a API ainda aceitava o PATCH, e mudar aqui não muda a agenda.
A marca só é gravada pela carga da virada; em 27/10 havia 0 eventos assim em produção.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Solicitacao
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def gerencia():
    return Gerencia.objects.create(nome="GERENCIA PLANILHA EDITA", nome_setor="Fluir", ativo=True)


@pytest.fixture
def formador(gerencia):
    user = UsuarioFactory(username="formador_planilha_edita", cpf="64100000001")
    com_papel(user, "FORMADOR", gerencia)
    return user


def _evento(dono, gerencia, *, planilha: bool) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=5)
    return SolicitacaoFactory(
        usuario=dono,
        municipio=MunicipioFactory(),
        projeto=ProjetoFactory(nome="Projeto Planilha Edita", fluxo="NAO_SUPER", gerencia=gerencia),
        tipo_evento=TipoEventoFactory(nome="Formacao Planilha Edita"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="aprovado",
        gcal_status="NONE",
        external_event_id=None,
        publicado_fora_do_sistema=planilha,
    )


def _patch(user, sol):
    client = APIClient()
    client.force_authenticate(user=user)
    return client.patch(f"/api/solicitacoes/{sol.pk}/", {"observacoes": "mudou"}, format="json")


def test_sem_a_marca_o_dono_edita(formador, gerencia):
    """Controle positivo: o mesmo evento, sem a marca da planilha, se edita."""
    sol = _evento(formador, gerencia, planilha=False)
    assert _patch(formador, sol).status_code == 200


@pytest.mark.parametrize("quem", ["dono", "superuser"])
def test_evento_da_planilha_nao_se_edita(quem, formador, gerencia):
    """Nem quem pediu nem o superusuário: como no publicado pelo sistema (a Apoio já não edita o de outro)."""
    sol = _evento(formador, gerencia, planilha=True)
    user = (
        formador
        if quem == "dono"
        else UsuarioFactory(username="super_planilha_edita", cpf="64100000003", is_superuser=True, is_staff=True)
    )
    response = _patch(user, sol)
    assert response.status_code == 400, response.data
    assert "planilha" in str(response.data)
    sol.refresh_from_db()
    assert sol.observacoes != "mudou"
