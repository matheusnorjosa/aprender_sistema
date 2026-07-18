# Design — <título da mudança>

> **Como**. Só depois de `requirements.md` aprovado.
> A solução deve caber nas camadas e nas barras de qualidade da `CONSTITUTION.md`.

- **Spec ID**: NNNN-slug

## Abordagem

<2-5 frases: a estratégia escolhida e por quê. Se houve alternativas, registre a descartada
e o motivo.>

## Camadas e arquivos a tocar

Respeite `models → services → views/serializers`. Liste caminhos reais.

| Camada | Arquivo | Mudança |
|---|---|---|
| service | `apps/core/services/____.py` | <…> |
| view | `apps/core/views/____.py` | <…> |
| model | `apps/core/models/____.py` | <…/nenhuma> |

## Modelo de dados / migrations

- <campos/constraints novos; ou "sem mudança de schema">
- Migration: <necessária? reversível? índice CONCURRENTLY?>

## API (se aplicável)

- Rota(s): `/api/...` (canônico; nunca `/api/v1/*`).
- Request/response shape; erros no formato `{ code, detail, field_errors }`.
- `@extend_schema`, paginação, permissão (`HasPerm("...")`).

## RBAC / AuditLog

- Capability exigida: `____`.
- Write crítico → `AuditLog`? Qual `action` e quais `details`?

## Estratégia de teste

- Arquivos de teste e casos (felizes + 403 + edge). Cobertura alvo.
- Fixtures necessárias; `GCAL_CLIENT=fake` se tocar GCal.

## ADRs / docs relacionados

- ADR-____; `v2/docs/...`
