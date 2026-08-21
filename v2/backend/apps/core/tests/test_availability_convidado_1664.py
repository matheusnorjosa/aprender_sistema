"""M08-07 (#1664): participação CONVIDADO não ocupa a agenda da pessoa.

A `events_qs` do motor de disponibilidade casava qualquer participação da pessoa,
sem filtrar por papel ocupante — então uma participação CONVIDADO (audiência)
bloqueava a pessoa para uma alocação real (FORMADOR) no mesmo horário. O filtro
por `role__in=ENFORCED_ROLES` vai na origem da query.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

import pytest

from apps.core.models import Participation, Solicitacao
from apps.core.services.availability_service import check_conflicts_uncached
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _setup():
    tz = timezone.get_current_timezone()
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    projeto = ProjetoFactory(nome="Projeto Conv 1664", ativo=True, fluxo="SUPER")
    tipo = TipoEventoFactory(nome="Formação", cor="#FF0000")
    dono = UsuarioFactory(username="dono_e1_1664", email="dono_e1_1664@x.com", password="p")
    pessoa = UsuarioFactory(username="pessoa_conv_1664", email="pessoa_conv_1664@x.com", password="p")
    inicio = timezone.make_aware(datetime(2026, 5, 10, 9, 0), tz)
    fim = timezone.make_aware(datetime(2026, 5, 10, 11, 0), tz)
    # Evento aprovado E1 pertence ao `dono`; `pessoa` entra como participante.
    e1 = SolicitacaoFactory(
        usuario=dono,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
        inicio=inicio,
        fim=fim,
        status=Solicitacao.Status.APROVADO,
    )
    return municipio, pessoa, e1, inicio, fim


def test_participacao_convidado_nao_bloqueia_a_pessoa():
    municipio, pessoa, e1, inicio, fim = _setup()
    Participation.objects.create(solicitacao=e1, usuario=pessoa, role=Participation.Role.CONVIDADO)

    # Checar `pessoa` no MESMO horário (como se fosse alocá-la de FORMADOR).
    result = check_conflicts_uncached(usuario=pessoa, inicio=inicio, fim=fim, municipio=municipio)

    assert result.ok, [c.code for c in result.conflicts]


def test_participacao_formador_ainda_bloqueia_a_pessoa():
    # Controle positivo: papel OCUPANTE (FORMADOR) continua bloqueando — o fix
    # exclui só os não-ocupantes, não afrouxa a regra.
    municipio, pessoa, e1, inicio, fim = _setup()
    Participation.objects.create(solicitacao=e1, usuario=pessoa, role=Participation.Role.FORMADOR)

    result = check_conflicts_uncached(usuario=pessoa, inicio=inicio, fim=fim, municipio=municipio)

    assert not result.ok
