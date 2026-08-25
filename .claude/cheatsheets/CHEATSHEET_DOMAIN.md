# Domain Cheatsheet — Aprender Sistema v2

> índice — full em `.claude/skills/aprender-domain/SKILL.md` + specs vivas `v2/docs/specs/domain/` (SSOT)

Este arquivo é só um **ponteiro/lookup de IDs**. Regras detalhadas, mensagens e validações
ficam nas specs vivas (com `status` + `last_verified`) e na skill `aprender-domain`.

## Onde está a verdade (SSOT)

| Tópico | Fonte |
|--------|-------|
| Regras de negócio completas (RF/RD/PA/CP) | `skills/aprender-domain/SKILL.md` |
| Contratos imutáveis (CP/RD/PA/RF) | `v2/docs/specs/domain/` |
| Disponibilidade (RD-01~08) | `v2/docs/specs/backend/availability.spec.md` |
| Aprovação (PA-01~07) | `v2/docs/specs/backend/solicitacao-approval.spec.md` |
| Índice SDD | `v2/docs/specs/INDEX_SDD.md` |

> Antes de nomear/citar qualquer ID, consultar a skill `aprender-domain` (evita erro de numeração).

## Lookup de IDs (só rótulos — sem o detalhe das regras)

### CP — Cláusulas Pétreas (IMUTÁVEIS)

| CP | Tema |
|----|------|
| CP-01 | v2 roda APENAS em Docker (`cd v2 && make up`) |
| CP-02 | PA-01~07 — aprovação obrigatória para SUPER |
| CP-03 | RD-01~08 — disponibilidade (timezone Fortaleza) |
| CP-04 | Workflow: Entender → Planejar → Implementar → Testar |
| CP-05 | v1 congelado (branch `fix/v1-*` + PR `main-v1`) |
| CP-06 | Conventional commits (`type(scope): message`) |
| CP-07 | Nunca push direto na main (enforced por hook) |
| CP-08 | `INCLUDE_DEV_TOOLS=false` em produção |

### RD — Regras de Disponibilidade

| RD | Tema |
|----|------|
| RD-01 | Não-sobreposição de eventos |
| RD-02 | Bloqueio total |
| RD-03 | Bloqueio parcial |
| RD-04 | Buffer de deslocamento entre municípios |
| RD-05 | Capacidade diária por formador |
| RD-06 | Timezone America/Fortaleza, storage UTC |
| RD-07 | Prioridade de avaliação das regras |
| RD-08 | Formato das mensagens de conflito |

### PA — Política de Aprovação

| PA | Tema |
|----|------|
| PA-01 | Sem auto-aprovação SUPER |
| PA-02 | Quem pode aprovar/reprovar |
| PA-03 | GCal só após aprovação |
| PA-04 | Estado inicial por fluxo |
| PA-05 | Registrar em Aprovacao + AuditLog |
| PA-06 | Esconder ações sem permissão na UI |
| PA-07 | Testes obrigatórios da política |

### RF — Requisitos Funcionais

| RF | Tema |
|----|------|
| RF01 | Import (export-contract) |
| RF02 | Solicitar evento |
| RF03 | Verificar conflitos |
| RF04 | Aprovar/Reprovar |
| RF05 | Publicar no Google Calendar |
| RF06 | Google Meet (eventos online) |
| RF07 | Auditoria |
| RF08 | Mapa Mensal |

> Endpoints, mensagens e regras exatas: ver specs vivas acima. Não duplicar aqui.

## Quick commands

```bash
pytest apps/core/tests/test_availability_service.py -v      # RD
pytest apps/core/tests/test_approval_policy_PA.py -v        # PA
make import-compras-dry FILE=...                            # import (dry-run; ETL legado REMOVIDO)
```
