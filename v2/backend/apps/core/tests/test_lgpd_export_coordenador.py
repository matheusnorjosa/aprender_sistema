"""Opção A #1837 — paridade acesso↔erasure (LGPD art. 18).

Se a anonimização passa a alcançar o `DATCoordenador` por CPF, o dossiê de
acesso/portabilidade também precisa incluí-lo — senão o sistema apaga dado que se
recusa a divulgar.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

import pytest

from apps.core.models import DATCoordenador
from apps.core.services.lgpd_export_service import build_lgpd_export_data
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF = "11144477735"


def test_dossie_inclui_coordenador_casado_por_cpf():
    user = UsuarioFactory(cpf=_CPF)
    actor = UsuarioFactory()
    DATCoordenador.objects.create(nome="Amanda Arruda", area="DAT", cpf=_CPF, created_by=actor)

    data = build_lgpd_export_data(user, include_audit=False)

    registros = data["dat_coordenador_records"]
    assert len(registros) == 1
    assert registros[0]["nome"] == "Amanda Arruda"


def test_dossie_sem_coordenador_quando_cpf_nao_casa():
    user = UsuarioFactory(cpf=_CPF)
    actor = UsuarioFactory()
    DATCoordenador.objects.create(nome="Outro", area="DAT", cpf="22255588846", created_by=actor)

    data = build_lgpd_export_data(user, include_audit=False)

    assert data["dat_coordenador_records"] == []
