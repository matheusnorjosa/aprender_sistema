"""
#1556 — Invalidação de cache de disponibilidade em Participation.

Contexto (descoberto no #1452 / PR #1555): a invalidação de cache só cobria
`Solicitacao.usuario_id` (o CRIADOR) e `AvailabilityBlock.usuario_id`. Não havia
receiver em `Participation`. Consequência: um formador alocado apenas como
participante (role FORMADOR/COORD_ACOMPANHA) tinha o cache cacheado (`check_conflicts`
com TTL 5 min e a grade mensal) preso em "livre" até o TTL expirar.

Estes testes provam que, após o fix:
- criar/remover Participation por instância (get_or_create, admin, shell) invalida
  o cache do participante (via signal);
- o caminho de UPDATE que usa `bulk_create` (que NÃO dispara post_save) também
  invalida, via invalidação explícita em `_update_formadores`;
- convidados externos (usuario_id None) não quebram o receiver;
- a versão da grade mensal (`monthly_ver:<id>`) é bumpada para o participante.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

import pytest

from apps.core.models import Participation, Solicitacao
from apps.core.services.availability_service import check_conflicts
from apps.core.tests.factories import (
    MunicipioFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)
from apps.core.views_solicitacao import SolicitacaoViewSet

pytestmark = pytest.mark.django_db


def _make_user(prefix: str):
    """Usuário único (cpf/username distintos) para não colidir cache entre testes."""
    uid = uuid4().hex[:8]
    return UsuarioFactory(
        username=f"{prefix}_{uid}",
        email=f"{prefix}_{uid}@test.com",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )


def _evento_aprovado(*, criador, municipio, inicio, fim):
    return SolicitacaoFactory(
        usuario=criador,
        municipio=municipio,
        tipo_evento=TipoEventoFactory(nome=f"Ev {uuid4().hex[:6]}"),
        projeto=None,
        inicio=inicio,
        fim=fim,
        status=Solicitacao.Status.APROVADO,
    )


class TestParticipationCacheInvalidation:
    def test_criar_participation_invalida_cache_do_formador(self):
        """Signal (create path): criar Participation invalida o cache cacheado do formador."""
        formador = _make_user("form")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=4, hours=9)
        fim = inicio + timedelta(hours=2)

        # Prima o cache: sem eventos, o caminho cacheado registra "livre".
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is True

        # Coordenador cria o evento; o formador entra apenas como PARTICIPANTE.
        coord = _make_user("coord")
        evento = _evento_aprovado(criador=coord, municipio=municipio, inicio=inicio, fim=fim)
        Participation.objects.create(solicitacao=evento, usuario=formador, role=Participation.Role.FORMADOR)

        # Com o fix, o cache do formador foi invalidado → o cacheado enxerga o conflito.
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is False

    def test_remover_participation_invalida_cache_do_formador(self):
        """Signal (delete path): remover Participation reabre a agenda do formador no cache."""
        formador = _make_user("form")
        coord = _make_user("coord")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=4, hours=14)
        fim = inicio + timedelta(hours=2)

        evento = _evento_aprovado(criador=coord, municipio=municipio, inicio=inicio, fim=fim)
        part = Participation.objects.create(solicitacao=evento, usuario=formador, role=Participation.Role.FORMADOR)

        # Alocado → o cacheado vê o conflito (e cacheia esse resultado).
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is False

        # Remover a participação invalida o cache → volta a "livre".
        part.delete()
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is True

    def test_update_formadores_via_bulk_create_invalida_cache(self):
        """Update path: `_update_formadores` usa bulk_create (não dispara post_save);
        a invalidação explícita fecha o furo."""
        coord = _make_user("coord")
        formador = _make_user("form")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=5, hours=9)
        fim = inicio + timedelta(hours=2)

        evento = _evento_aprovado(criador=coord, municipio=municipio, inicio=inicio, fim=fim)

        # Formador ainda NÃO alocado → prime "livre".
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is True

        # Adiciona via caminho de update (bulk_create). Sem a invalidação explícita,
        # o cacheado ficaria obsoleto (post_save não dispara em bulk_create).
        SolicitacaoViewSet()._update_formadores(evento, {"formador_ids": [formador.id]})

        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is False

    def test_update_formadores_remocao_reabre_cache(self):
        """Update path: remover formador via `_update_formadores` reabre o cache."""
        coord = _make_user("coord")
        formador = _make_user("form")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=5, hours=14)
        fim = inicio + timedelta(hours=2)

        evento = _evento_aprovado(criador=coord, municipio=municipio, inicio=inicio, fim=fim)
        Participation.objects.create(solicitacao=evento, usuario=formador, role=Participation.Role.FORMADOR)

        # Alocado → cacheado vê conflito.
        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is False

        # Remove via update (lista vazia) → deve invalidar e reabrir.
        SolicitacaoViewSet()._update_formadores(evento, {"formador_ids": []})

        assert check_conflicts(usuario=formador, inicio=inicio, fim=fim, municipio=municipio).ok is True

    def test_convidado_sem_usuario_nao_quebra_receiver(self):
        """Convidado externo (usuario_id None) não deve quebrar o receiver."""
        coord = _make_user("coord")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=6, hours=9)
        fim = inicio + timedelta(hours=2)

        evento = _evento_aprovado(criador=coord, municipio=municipio, inicio=inicio, fim=fim)

        part = Participation.objects.create(
            solicitacao=evento,
            guest_email="convidado@externo.com",
            role=Participation.Role.CONVIDADO,
        )
        assert part.pk is not None  # save não quebrou
        part.delete()  # delete também não quebra

    def test_criar_participation_bumpa_monthly_ver_do_formador(self):
        """A grade mensal (monthly_ver:<id>) é bumpada para o participante afetado."""
        formador = _make_user("form")
        coord = _make_user("coord")
        municipio = MunicipioFactory()
        inicio = timezone.now() + timedelta(days=7, hours=9)
        fim = inicio + timedelta(hours=2)

        # Estado conhecido da versão mensal do formador.
        cache.set(f"monthly_ver:{formador.id}", 5, timeout=3600)

        evento = _evento_aprovado(criador=coord, municipio=municipio, inicio=inicio, fim=fim)
        Participation.objects.create(solicitacao=evento, usuario=formador, role=Participation.Role.FORMADOR)

        # A invalidação bumpa a versão mensal do formador (não do criador).
        assert cache.get(f"monthly_ver:{formador.id}") == 6
