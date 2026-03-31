# ADR-011: Polling HTTP sobre WebSocket para Sincronização

**Status:** Accepted
**Date:** 2026-03-31
**Decider:** Matheus Norjosa

## Context

Dois coordenadores podem tentar alocar o mesmo formador simultaneamente. Modificações numa aba/dispositivo não refletem na outra sem refresh manual. Precisamos de sincronização entre abas e entre dispositivos.

Alternativas avaliadas:
- **WebSocket (Django Channels)**: Real-time verdadeiro mas requer ASGI server (Daphne/Uvicorn) + Channel Layer + nova infra
- **Server-Sent Events (SSE)**: Unidirecional, funciona com WSGI mas requer endpoint streaming
- **FastAPI híbrido**: WebSocket nativo mas requer manter 2 frameworks
- **Polling HTTP 5s + BroadcastChannel**: Usa stack existente, delay máximo 5s

## Decision

- **Entre dispositivos**: Polling HTTP a cada 5 segundos nos endpoints REST existentes
- **Mesma sessão (abas)**: BroadcastChannel API (nativa do browser, instantâneo)
- **Não migrar** para WebSocket, SSE, ou FastAPI
- Páginas alvo: Grade mensal, solicitações, aprovações, pré-agenda
- Page Visibility API pausa polling em abas escondidas

## Consequences

- Zero infra nova (sem ASGI, sem Django Channels)
- Zero mudança no backend
- Delay máximo de 5s entre dispositivos (aceitável para o caso de uso)
- Instantâneo entre abas do mesmo browser (BroadcastChannel)
- Carga adicional: ~2 req/s (10 users) a ~10 req/s (50 users) — absorvida pelo cache Redis
- Reavaliar se escala ultrapassar 500 usuários simultâneos

## References

- Epic #1032, Issues #1033-#1036
- `thoughts/shared/plans/PLAN-realtime-sync.md`
- `v2/frontend/src/hooks/usePolling.ts` (existente)
