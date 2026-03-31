# ADR-008: RequestId Determinístico para Google Calendar

**Status:** Accepted
**Date:** 2026-03-31
**Decider:** Matheus Norjosa

## Context

O `conferenceData.createRequest.requestId` era gerado com `uuid4()` a cada build de payload. Isso causava hash SHA1 diferente mesmo sem mudança nos dados do evento, produzindo falsos positivos de drift em todos os eventos online. O requestId é usado pelo Google para idempotência (mesmo ID = mesmo Meet link).

## Decision

- RequestId determinístico: `f"meet-asv2-{solicitacao.id}"` (estável por solicitação)
- Excluir `conferenceData` do cálculo de `_payload_hash()` (é metadata da API Google, não dados do evento)

Alternativas rejeitadas:
- **Manter uuid4 e ignorar drift**: Mascararia drift real
- **Incluir conferenceData no hash com requestId fixo**: Hash ainda mudaria se Google alterasse a estrutura do conferenceData

## Consequences

- Zero falsos positivos de drift para eventos online
- Hash reflete apenas mudanças reais nos dados do evento
- Google Meet idempotência preservada (mesmo requestId = mesmo link)

## References

- Issue #573
- PR #1004
- `v2/backend/apps/core/services/gcal/payload.py:228-240`
- `v2/backend/apps/core/services/gcal/utils.py:_payload_hash()`
