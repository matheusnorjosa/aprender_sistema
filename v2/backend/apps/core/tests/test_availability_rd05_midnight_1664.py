"""M08-09 (#1664): RD-05 recorta pela janela do dia — eventos que cruzam a
meia-noite contribuem a fração certa em D e em D+1.

Antes: o evento NOVO entrava com a duração CHEIA no dia do início (falso M) e o
dia seguinte nunca era checado (M real passava batido).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

import pytest

from apps.core.models import Solicitacao
from apps.core.services.availability_service import check_conflicts_uncached
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _ctx():
    tz = timezone.get_current_timezone()
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    projeto = ProjetoFactory(nome="Projeto RD05", ativo=True, fluxo="SUPER")
    tipo = TipoEventoFactory(nome="Formação", cor="#FF0000")
    pessoa = UsuarioFactory(username="pessoa_rd05", email="pessoa_rd05@x.com", password="p")
    return tz, municipio, projeto, tipo, pessoa


def _evento(pessoa, municipio, projeto, tipo, ini: datetime, fim: datetime):
    return SolicitacaoFactory(
        usuario=pessoa,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
        inicio=ini,
        fim=fim,
        status=Solicitacao.Status.APROVADO,
    )


def test_evento_cruzando_meia_noite_nao_conta_duracao_cheia_no_dia_do_inicio():
    # Limite diário padrão = 8h. Evento existente de 5h (08–13) em D.
    # Novo evento 22h(D)→02h(D+1) = 4h, mas só 2h caem em D.
    # Antigo: D = 5h + 4h(cheia) = 9h > 8h → falso M. Novo: D = 5h + ~2h = ~7h → ok.
    tz, municipio, projeto, tipo, pessoa = _ctx()
    _evento(
        pessoa,
        municipio,
        projeto,
        tipo,
        timezone.make_aware(datetime(2026, 5, 10, 8, 0), tz),
        timezone.make_aware(datetime(2026, 5, 10, 13, 0), tz),
    )
    inicio = timezone.make_aware(datetime(2026, 5, 10, 22, 0), tz)
    fim = timezone.make_aware(datetime(2026, 5, 11, 2, 0), tz)

    result = check_conflicts_uncached(usuario=pessoa, inicio=inicio, fim=fim, municipio=municipio)

    assert result.ok, [(c.code, c.detail) for c in result.conflicts]


def test_evento_cruzando_meia_noite_conta_capacidade_no_dia_seguinte():
    # Evento existente de 6h (05–11) em D+1. Novo 22h(D)→04h(D+1) = 6h; 4h caem em D+1.
    # Antigo: só checa D → 6h < 8h → ok (perde o estouro). Novo: D+1 = 6h + 4h = 10h > 8h → M.
    tz, municipio, projeto, tipo, pessoa = _ctx()
    _evento(
        pessoa,
        municipio,
        projeto,
        tipo,
        timezone.make_aware(datetime(2026, 5, 11, 5, 0), tz),
        timezone.make_aware(datetime(2026, 5, 11, 11, 0), tz),
    )
    inicio = timezone.make_aware(datetime(2026, 5, 10, 22, 0), tz)
    fim = timezone.make_aware(datetime(2026, 5, 11, 4, 0), tz)

    result = check_conflicts_uncached(usuario=pessoa, inicio=inicio, fim=fim, municipio=municipio)

    assert not result.ok
    assert any(c.code == "M" for c in result.conflicts), [(c.code, c.detail) for c in result.conflicts]
