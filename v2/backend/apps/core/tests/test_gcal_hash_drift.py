"""
Testes para bug #573 — Hash drift em eventos online (falsos positivos).

O conferenceData.createRequest.requestId era gerado com uuid4() a cada
chamada, causando hash diferente mesmo sem mudança nos dados do evento.

Refs: Issue #573
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.services.gcal.payload import (
    build_event_payload,
    compute_payload_hash,
)


@pytest.fixture
def online_solicitacao(db):
    """Cria uma solicitação online aprovada para testes de hash."""
    user = Usuario.objects.create_user(username="hash_test_user", password="test123")
    municipio = Municipio.objects.create(nome="HashCity", uf="CE")
    projeto = Projeto.objects.create(nome="HASH TEST", fluxo="NAO_SUPER")
    tipo = TipoEvento.objects.create(nome="Formação Hash")

    now = timezone.now()
    sol = Solicitacao.objects.create(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
        is_online=True,
    )
    return sol


@pytest.fixture
def presencial_solicitacao(db):
    """Cria uma solicitação presencial aprovada para testes de hash."""
    user = Usuario.objects.create_user(username="hash_test_pres", password="test123")
    municipio = Municipio.objects.create(nome="PresCity", uf="SP")
    projeto = Projeto.objects.create(nome="PRES TEST", fluxo="NAO_SUPER")
    tipo = TipoEvento.objects.create(nome="Formação Pres")

    now = timezone.now()
    sol = Solicitacao.objects.create(
        usuario=user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
        is_online=False,
    )
    return sol


class TestHashDriftOnlineEvents:
    """Bug #573: hash de payload muda entre chamadas para eventos online."""

    def test_payload_hash_stable_for_online_event(self, online_solicitacao):
        """Hash deve ser idêntico em chamadas consecutivas para o mesmo evento online."""
        hash1 = compute_payload_hash(online_solicitacao)
        hash2 = compute_payload_hash(online_solicitacao)
        hash3 = compute_payload_hash(online_solicitacao)

        assert hash1 == hash2, f"Bug #573: hash drifted between calls: {hash1} != {hash2}"
        assert hash2 == hash3, f"Bug #573: hash drifted between calls: {hash2} != {hash3}"

    def test_payload_hash_stable_for_presencial_event(self, presencial_solicitacao):
        """Hash deve ser idêntico para eventos presenciais (baseline, não deve falhar)."""
        hash1 = compute_payload_hash(presencial_solicitacao)
        hash2 = compute_payload_hash(presencial_solicitacao)

        assert hash1 == hash2

    def test_build_payload_conference_request_id_deterministic(self, online_solicitacao):
        """requestId do conferenceData deve ser determinístico (baseado no ID da solicitação)."""
        payload1 = build_event_payload(online_solicitacao, enable_meet=True)
        payload2 = build_event_payload(online_solicitacao, enable_meet=True)

        cd1 = payload1.get("conferenceData", {})
        cd2 = payload2.get("conferenceData", {})

        rid1 = cd1.get("createRequest", {}).get("requestId", "")
        rid2 = cd2.get("createRequest", {}).get("requestId", "")

        assert rid1 == rid2, f"Bug #573: requestId must be deterministic. Got '{rid1}' and '{rid2}'"

    def test_hash_excludes_conference_data(self, online_solicitacao):
        """Hash não deve incluir conferenceData (é metadata da API Google, não dados do evento)."""
        payload_with_meet = build_event_payload(online_solicitacao, enable_meet=True)
        payload_without_meet = build_event_payload(online_solicitacao, enable_meet=False)

        # conferenceData é a ÚNICA diferença funcional entre os dois payloads
        assert "conferenceData" in payload_with_meet
        assert "conferenceData" not in payload_without_meet

        from apps.core.services.gcal.utils import _payload_hash

        # Os hashes devem ser iguais (conferenceData não deve afetar hash)
        hash_with = _payload_hash(payload_with_meet)
        hash_without = _payload_hash(payload_without_meet)

        assert hash_with == hash_without, "Bug #573: conferenceData should not affect payload hash"

    def test_data_change_still_detected(self, online_solicitacao):
        """Mudanças reais nos dados do evento devem mudar o hash (não é tudo ignorado)."""
        hash_before = compute_payload_hash(online_solicitacao)

        # Mudar dados reais do evento
        online_solicitacao.observacoes = "Novas observações adicionadas"
        online_solicitacao.save()

        hash_after = compute_payload_hash(online_solicitacao)

        assert hash_before != hash_after, "Real data changes must produce different hashes"
