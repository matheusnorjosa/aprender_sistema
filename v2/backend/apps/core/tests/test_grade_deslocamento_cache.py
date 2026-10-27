"""Grade mensal: criar, mudar ou apagar um Deslocamento atualiza a grade na hora.

A grade mostra "D"/"D1" a partir de `Deslocamento` (monthly_grid_service), mas só Solicitacao,
AvailabilityBlock e Participation sobem a versão `monthly_ver` (item 38). Sem isso, quem registra
um deslocamento via a grade antiga por até 5 min (TTL do cache).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from apps.core.models import Deslocamento
from apps.core.tests.factories import UsuarioFactory
from apps.core.utils.cache_utils import get_monthly_cache_version

pytestmark = pytest.mark.django_db


def _usuario():
    uid = uuid4().hex[:8]
    return UsuarioFactory(username=f"desl_{uid}", email=f"desl_{uid}@test.com", cpf=str(uuid4().int % 10**11).zfill(11))


def _deslocamento(usuario):
    return Deslocamento.objects.create(
        usuario=usuario, origem="Crato", destino="Sobral", start_date=date(2026, 11, 3), end_date=date(2026, 11, 4)
    )


def test_criar_deslocamento_sobe_a_versao_da_grade():
    antes = get_monthly_cache_version()
    _deslocamento(_usuario())
    assert get_monthly_cache_version() > antes


def test_mudar_deslocamento_sobe_a_versao_da_grade():
    d = _deslocamento(_usuario())
    antes = get_monthly_cache_version()
    d.end_date = date(2026, 11, 5)
    d.save()
    assert get_monthly_cache_version() > antes


def test_apagar_deslocamento_sobe_a_versao_da_grade():
    d = _deslocamento(_usuario())
    antes = get_monthly_cache_version()
    d.delete()
    assert get_monthly_cache_version() > antes
