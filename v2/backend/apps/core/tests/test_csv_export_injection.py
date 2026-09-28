"""Testes de injeção de fórmula nos exports CSV de DAT e GCal (SEC-007).

Os dois endpoints passam o texto livre por `sanitize_csv_value` antes de
escrever o CSV. Sem estes testes, tirar o helper de um deles não deixa nada
vermelho. Cada caso usa a permissão real do endpoint e grava a fórmula em
Municipio.nome e Projeto.nome, que saem no CSV.

Molde: `test_admin_csv_export.py` (export do admin).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import DATRegistro, ProjetoGeral
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, SolicitacaoFactory, UsuarioFactory

FORMULA = "=HYPERLINK(1)"


def _assert_formula_neutralizada(content: bytes) -> None:
    # A fórmula sai com prefixo ' (o Excel lê como texto).
    assert b"'=HYPERLINK(1)" in content
    # Nenhuma célula começa com '=': nem depois de vírgula, nem no início da linha.
    assert b",=HYPERLINK" not in content
    assert b"\n=HYPERLINK" not in content


@pytest.mark.django_db
def test_export_dat_registros_neutraliza_formula() -> None:
    usuario_dat = UsuarioFactory(groups=["DAT"])  # HasPerm("manage_admin_registries")
    projeto_geral = ProjetoGeral.objects.create(nome="PG CSV injection")
    DATRegistro.objects.create(
        municipio=MunicipioFactory(nome=FORMULA),
        projeto_geral=projeto_geral,
        projeto=ProjetoFactory(nome=FORMULA, projeto_geral=projeto_geral),
        created_by=usuario_dat,
    )

    client = APIClient()
    client.force_authenticate(user=usuario_dat)
    response = client.get(reverse("core:dat-registro-export"))

    assert response.status_code == 200
    _assert_formula_neutralizada(response.content)


@pytest.mark.django_db
def test_export_gcal_dashboard_events_neutraliza_formula() -> None:
    usuario_controle = UsuarioFactory(groups=["Controle"])  # CanUseGcal
    # O export só lista solicitações aprovadas.
    SolicitacaoFactory(
        status="aprovado",
        municipio=MunicipioFactory(nome=FORMULA),
        projeto=ProjetoFactory(nome=FORMULA),
        usuario=usuario_controle,
    )

    client = APIClient()
    client.force_authenticate(user=usuario_controle)
    response = client.get(reverse("core:gcal-dashboard-events-export"), {"export_format": "csv"})

    assert response.status_code == 200
    _assert_formula_neutralizada(response.content)
