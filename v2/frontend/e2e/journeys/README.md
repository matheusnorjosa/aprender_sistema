# Matriz de Jornadas E2E

Fase 3 do plano QA 2026-04-22. Cada jornada testa um fluxo ponta a ponta
em três camadas de asserção:

1. **Canônica** — regra do domínio, caminho feliz.
2. **Borda** — valor limite / idempotência / conflito.
3. **Operação** — reflexo observável em outra tela/endpoint (triangulação).

## Convenções

- Um arquivo por jornada: `j{NN}-{slug}.spec.ts`.
- Tags `@critical`, `@rbac`, `@rd-XX`, `@pa-XX`, etc. em `test(...)`.
- Seed via API (fixture `seedSolicitacao`), nunca via wizard — wizard é o
  objeto de teste em jornadas específicas (ex: J02).
- `test.fail()` quando a jornada está bloqueada por issue conhecida. Retirar
  a marca quando a issue for resolvida.

## Matriz atual

**Observação sobre 2 fluxos de aprovação**: projetos têm `fluxo` SUPER ou NAO_SUPER
([`solicitacao_create.py`](../../../backend/apps/core/services/solicitacao_create.py)).
SUPER requer aprovação manual (PA-02); NAO_SUPER é auto-aprovado na criação.
Jornadas que dependem de aprovação têm duas variantes (J01a/J01b).

| ID | Jornada | Tags | Status | Depende de |
|----|---------|------|--------|-----------|
| J01a | SUPER happy path: coord cria → super aprova | `@critical @rf01 @pa-02 @fluxo-super` | ✅ | — |
| J01b | NAO_SUPER happy path: coord cria → auto-aprovado | `@critical @rf01 @fluxo-nao-super` | ✅ | — |
| J02 | Wizard bloqueia submit com campo obrigatório vazio | `@ux @rf01` | ⏳ | — |
| J03 | Conflito RD-06 (deslocamento inviável) | `@critical @rd-06` | ⏳ | time-freeze |
| J04 | Reprovação com motivo obrigatório (PA-04) | `@pa-04` | ⏳ | — |
| J05 | Visão individual vs setor (/solicitacoes vs /disponibilidade) | `@critical @rbac` | ✅ | — |
| J06 | Formador fora de janela → RD-01 | `@critical @rd-01` | ⏳ | time-freeze |
| J07 | Bloqueio pontual impede RD-04 | `@rd-04` | ⏳ | — |
| J08 | Aprovação concorrente (dois super) | `@race @pa-07` | ⏳ | — |
| J09 | Cancelamento pós-publicação re-sincroniza GCal | `@rf07` | ⏳ | GCal client |
| J10 | Coord tenta aprovar própria solicitação → 403 | `@critical @rbac @pa-02` | ✅ | — |
| J11 | E-mail ao formador após aprovação | `@rf-email` | ⏳ | SMTP mock |
| J12 | Dashboard Compras reflete criação em <3s | `@perf @dashboards` | ⏳ | — |
| J13 | Formador escalado vê em "Minhas Formações" | `@rf-minhas` | 🚫 `test.fail` | #1163 |
| J14 | Gerente cria solicitação com setor auto | `@rbac @gerente` | 🚫 `test.fail` | #1165 |
| J15 | Formador chama `/api/metrics/team/*` → 403 | `@rbac @dashboards` | 🚫 `test.fail` | #1166 |
| J16 | Formador chama `/api/gcal/dashboard/*` → 403 | `@rbac @dashboards` | 🚫 `test.fail` | #1166 |
| J17 | Formador digita `/bloqueios` → rota bloqueia antes de render | `@rbac` | 🚫 `test.fail` | #1168 |
| J18 | DAT puro navega em todos os menus sem 403 | `@critical @rbac @dat` | ✅ | — |
| J19 | HomeStats `upcoming_events` não vaza entre setores | `@rbac @home` | 🚫 `test.fail` | #1167 |
