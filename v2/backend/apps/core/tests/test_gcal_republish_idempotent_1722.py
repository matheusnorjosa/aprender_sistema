"""
Regressao #1722: re-publish de um evento aprovado INALTERADO deve PULAR o UPDATE.

Sem isto, todo re-publish chama client.update() e, com GCAL_SEND_UPDATES=all
(valor de producao), reenvia e-mail a todos os convidados sem nenhuma mudanca real.
A idempotencia vem de comparar o gcal_payload_hash armazenado com o do payload novo.

100% fake/mocked (GCAL_CLIENT=fake), sem rede real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

import pytest

from apps.core.models import Solicitacao
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)


@pytest.fixture
def solicitacao_aprovada(db):
    """Solicitacao aprovada, ainda nao publicada no GCal."""
    user = UsuarioFactory(username="republish_1722", email="republish_1722@test.com", cpf="98765432100")
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    projeto = ProjetoFactory(nome="Projeto 1722", codigo="R1722", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEventoFactory(nome="Formacao 1722")

    now = timezone.now()
    return SolicitacaoFactory(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        tipo="evento",
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=3),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.NONE,
    )


@pytest.mark.django_db
@patch("django.conf.settings.GCAL_CLIENT", "fake")
def test_republish_unchanged_event_skips_update(solicitacao_aprovada):
    """Publicar e re-publicar sem mudanca: a 2a passada deve retornar SKIP e NAO chamar update()."""
    from apps.core.services.gcal_sync_service import apply_one_solicitacao

    # Cliente fake COMPARTILHADO para o evento persistir entre as duas passadas.
    client = FakeCalendarClient()

    first = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True, client=client)
    assert first.action == "CREATE"
    solicitacao_aprovada.refresh_from_db()
    assert solicitacao_aprovada.gcal_payload_hash  # hash foi armazenado no publish

    with patch.object(client, "update", wraps=client.update) as spy_update:
        second = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True, client=client)

    assert second.action == "SKIP"
    spy_update.assert_not_called()  # nenhum UPDATE => nenhum e-mail reenviado aos convidados


@pytest.mark.django_db
@patch("django.conf.settings.GCAL_CLIENT", "fake")
def test_resync_clears_hash_and_forces_update(solicitacao_aprovada):
    """O resync zera gcal_payload_hash de proposito: a re-publicacao entao DEVE fazer UPDATE."""
    from apps.core.services.gcal_sync_service import apply_one_solicitacao

    client = FakeCalendarClient()

    apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True, client=client)
    solicitacao_aprovada.refresh_from_db()

    # Simula o resync (endpoint/servico zeram o hash para forcar o reenvio).
    solicitacao_aprovada.gcal_payload_hash = None
    solicitacao_aprovada.save(update_fields=["gcal_payload_hash"])

    with patch.object(client, "update", wraps=client.update) as spy_update:
        outcome = apply_one_solicitacao(solicitacao_aprovada, dry_run=False, apply_blocked=True, client=client)

    assert outcome.action == "UPDATE"
    spy_update.assert_called_once()
