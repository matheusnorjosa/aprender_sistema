# ADR-002: Política de Aprovação Manual (PA-01 a PA-07)

**Status:** Accepted
**Date:** 2025-10-23
**Decider:** Matheus Norjosa

## Context

O sistema gerencia agendamento de formadores para eventos educacionais. Solicitações do fluxo SUPER envolvem a Superintendência e requerem validação humana antes de publicação no Google Calendar. Auto-aprovação criava riscos de eventos sem revisão adequada.

## Decision

Implementar política de aprovação manual obrigatória com 7 regras:

- **PA-01**: Nenhuma solicitação auto-aprovada (fluxo SUPER)
- **PA-02**: Apenas Superintendência/DAT/superuser podem aprovar
- **PA-03**: Integrações externas (GCal) executam somente após aprovação
- **PA-04**: Estado inicial sempre `pendente` (SUPER) ou `aprovado` (NAO_SUPER)
- **PA-05**: Auditoria completa em AuditLog (IP, user_agent, justificativa)
- **PA-06**: Botões de aprovação ocultos para não-autorizados (frontend)
- **PA-07**: 5 testes obrigatórios validam conformidade

## Consequences

- Fluxo SUPER: Coordenador cria → Superintendência aprova → Controle publica
- Fluxo NAO_SUPER: Coordenador cria (auto-aprovado) → Controle publica
- AuditLog registra toda ação com rastreabilidade completa
- Aprovação manual NÃO revalida conflitos (decisão humana com contexto)

## References

- CP-02 (Cláusula Pétrea)
- `v2/backend/apps/core/services/solicitacao_approval.py`
- `v2/backend/apps/core/tests/test_approval_policy_PA.py`
- `v2/docs/IMPLEMENTACAO_PA.md`
