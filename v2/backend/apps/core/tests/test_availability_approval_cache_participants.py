"""
Decisão do dono (2026-09-14): ao APROVAR uma solicitação, o evento passa a OCUPAR a
agenda dos participantes (check_conflicts conta evento aprovado via Participation com
role ocupante — RD-07). O signal de Solicitacao (`signals.py`) só bumpa o cache do
CRIADOR (`instance.usuario_id`); os demais participantes ficariam com
`avail_ver`/`monthly_ver` obsoletos — um preview cacheado diria "livre" para quem
acabou de ser alocado. O enforcement lê sem cache (correto), mas a leitura consultiva
(check_conflicts cacheado / grade mensal) precisa ser invalidada na aprovação.

Complementa o #1556 (que invalida na MUDANÇA de Participation) — aqui a Participation
não muda, só o `Solicitacao.status`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

import pytest

from apps.core.models import Participation, Solicitacao
from apps.core.services.availability_service import check_conflicts
from apps.core.services.solicitacao_approval import approve_solicitacao
from apps.core.tests.factories import (
    MunicipioFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _make_user(prefix: str):
    uid = uuid4().hex[:8]
    return UsuarioFactory(
        username=f"{prefix}_{uid}",
        email=f"{prefix}_{uid}@test.com",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )


def _evento_pendente(*, criador, municipio, inicio, fim):
    return SolicitacaoFactory(
        usuario=criador,
        municipio=municipio,
        tipo_evento=TipoEventoFactory(nome=f"Ev {uuid4().hex[:6]}"),
        projeto=None,
        inicio=inicio,
        fim=fim,
        status=Solicitacao.Status.PENDENTE,
    )


def _req():
    return SimpleNamespace(META={"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "pytest"})


class TestApprovalCacheParticipants:
    def test_aprovar_invalida_cache_avail_do_participante(self):
        """End-to-end: aprovar torna o participante ocupado; o cacheado deve enxergar."""
        coord = _make_user("coord")
        formador = _make_user("form")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=6, hours=9)
        fim = inicio + timedelta(hours=2)

        evento = _evento_pendente(criador=coord, municipio=municipio, inicio=inicio, fim=fim)
        Participation.objects.create(solicitacao=evento, usuario=formador, role=Participation.Role.FORMADOR)

        # Prime: pendente NÃO conta em check_conflicts → formador "livre" (cacheado).
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is True

        approve_solicitacao(solicitacao=evento, user=_make_user("super"), request=_req())

        # Com o fix: cache do participante invalidado → o cacheado enxerga o conflito.
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is False

    def test_aprovar_bumpa_monthly_ver_do_participante(self):
        """A aprovação também invalida a grade mensal (monthly_ver) do participante."""
        coord = _make_user("coord")
        formador = _make_user("form")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=7, hours=9)
        fim = inicio + timedelta(hours=2)

        evento = _evento_pendente(criador=coord, municipio=municipio, inicio=inicio, fim=fim)
        Participation.objects.create(solicitacao=evento, usuario=formador, role=Participation.Role.FORMADOR)

        # Fixa um valor conhecido DEPOIS da criação da Participation (que já bumpou via #1556).
        cache.set(f"monthly_ver:{formador.id}", 5, timeout=3600)

        approve_solicitacao(solicitacao=evento, user=_make_user("super"), request=_req())

        assert cache.get(f"monthly_ver:{formador.id}") == 6

    def test_aprovar_nao_bumpa_convidado_externo(self):
        """Convidado externo (usuario_id None) não tem disponibilidade — não deve quebrar."""
        coord = _make_user("coord")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=8, hours=9)
        fim = inicio + timedelta(hours=2)

        evento = _evento_pendente(criador=coord, municipio=municipio, inicio=inicio, fim=fim)
        Participation.objects.create(
            solicitacao=evento,
            usuario=None,
            guest_email="convidado@externo.com",
            role=Participation.Role.CONVIDADO,
        )

        # Não deve levantar (bump global indevido evitado).
        result = approve_solicitacao(solicitacao=evento, user=_make_user("super"), request=_req())
        assert result.new_status == "aprovado"
