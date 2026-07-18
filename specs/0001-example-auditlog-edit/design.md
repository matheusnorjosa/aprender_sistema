# Design — reabilitar AuditLog de edição de Solicitação

- **Spec ID**: 0001-example-auditlog-edit

## Abordagem

Investigar a causa do skip antes de "consertar". Descoberta: a lógica de AuditLog em
`SolicitacaoViewSet.perform_update()` **já funciona** desde o PR #332 — registra
`action=UPDATE` com `changed_fields` quando há diff. O skip era **órfão**: o teste nunca
foi reabilitado após a investigação original. Logo, a mudança é test-only: remover o skip
e **reforçar os asserts** para cobrir o critério "campos alterados". Nenhuma mudança de
produção.

Alternativa descartada: alterar `perform_update` — desnecessário, a lógica está correta
(confirmado por `test_owner_can_edit_own_solicitacao`, que já exercita o caminho).

## Camadas e arquivos a tocar

| Camada | Arquivo | Mudança |
|---|---|---|
| teste | `apps/core/tests/test_solicitacao_edit.py` | remover `@pytest.mark.skip`; reforçar asserts |
| view | `apps/core/views_solicitacao.py` | nenhuma (referência: `perform_update`, ~L400-487) |

## Modelo de dados / migrations

- Sem mudança de schema. Sem migration.

## API (se aplicável)

- N/A — exercita `PATCH /api/solicitacoes/{id}/` já existente.

## RBAC / AuditLog

- `AuditLog.action = UPDATE`, `model_name = "Solicitacao"`.
- `details`: `solicitacao_id`, `changed_fields` (old/new por campo), `ip_address`, `user_agent`.

## Estratégia de teste

- Reabilitar `test_edit_creates_audit_log`; asserts: presença de `local` e `observacoes`
  em `changed_fields`, e old/new de `local`.
- Negativo já coberto por `test_no_audit_log_when_no_changes` (não skipado).
- Rodar arquivo inteiro + regressão `-k "audit or Audit"`.

## ADRs / docs relacionados

- PA-05 (`.claude/skills/aprender-domain/`). Origem do código: PR #332.
