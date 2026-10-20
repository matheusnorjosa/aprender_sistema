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
  (texto de 2025-10-23; quem aprova hoje está na emenda de 2026-10-19 abaixo)
- **PA-03**: Integrações externas (GCal) executam somente após aprovação
- **PA-04**: Estado inicial sempre `pendente` (SUPER) ou `aprovado` (NAO_SUPER)
- **PA-05**: Auditoria completa em AuditLog (IP, user_agent, justificativa)
- **PA-06**: Botões de aprovação ocultos para não-autorizados (frontend)
- **PA-07**: 5 testes obrigatórios validam conformidade

## Consequences

- Fluxo SUPER: Coordenador cria → Superintendência aprova → Controle publica
  (quem aprova mudou; ver emenda de 2026-10-19)
- Fluxo NAO_SUPER: Coordenador cria (auto-aprovado) → Controle publica
- AuditLog registra toda ação com rastreabilidade completa
- ~~Aprovação manual NÃO revalida conflitos (decisão humana com contexto)~~
  — **revogado em 2026-07-16 pelo #1452** (`2a859b5a`; ver emenda abaixo)

### Emenda 2026-07-16 (#1452, `2a859b5a`): a aprovação REVALIDA conflitos

> [!warning] Não remova `enforce_solicitacao_availability` do caminho de aprovação
> Este ADR afirmou até 2026-08-25 que a aprovação manual não revalidava conflitos.
> Deixou de ser verdade no **#1452**. Quem ler a linha antiga, encontrar o guard no
> código e concluir que é resíduo indevido vai reabrir dupla alocação de formador em
> produção.

O que mudou:

- `approve_solicitacao` revalida a disponibilidade de **todos** os participantes dentro
  da mesma `transaction.atomic()`, depois do `select_for_update()` da linha e antes de
  gravar `status="aprovado"`
  (`approve_solicitacao` em `v2/backend/apps/core/services/solicitacao_approval.py`, que
  chama `enforce_solicitacao_availability(..., action="approve")`).
- `batch_approve_solicitacoes` revalida **item a item**, em sequência, dentro da
  transação do lote (`batch_approve_solicitacoes` em `solicitacao_approval.py`, que chama
  `enforce_solicitacao_availability(..., action="batch_approve")` por item). Como as
  aprovações anteriores já estão gravadas quando a próxima é checada, um lote não
  consegue aprovar dois eventos conflitantes do mesmo formador de uma vez. Conflito
  reprova só aquele item (entra em `errors`); o resto do lote segue.
- A exclusão mútua entre solicitações **distintas** do mesmo formador não vem do
  `select_for_update()` — ele tranca só a linha da própria solicitação. Vem do
  **advisory lock por participante** dentro de `enforce_solicitacao_availability`
  (`v2/backend/apps/core/services/solicitacao_availability.py`).
- `reject_solicitacao` e `batch_reject_solicitacoes` **não** revalidam: reprovar não
  ocupa agenda.

Por que a decisão original envelheceu: uma solicitação pode ficar pendente por dias, e o
momento da aprovação é o momento em que o evento passa a ocupar a agenda. O contexto que o
aprovador tinha ao abrir a fila pode não valer mais quando ele clica. O ADR-002 continua
válido no que decidiu — aprovação é humana e obrigatória (PA-01/PA-02); o que mudou é que
o humano decide *sobre um estado revalidado*, não sobre um instantâneo velho.

**Decision e Context acima permanecem como registrados em 2025-10-23.** PA-01 a PA-07 não
foram alterados pelo #1452.

### Emenda 2026-10-19: quem aprova (PA-02)

O texto de PA-02 acima ("Apenas Superintendência/DAT/superuser") envelheceu com o PR 3, o
B1, o PR 10 e o PR 11. A regra hoje é uma só, `solicitation_approval_basis`
(`v2/backend/apps/core/rbac/policies.py`), com três bases em ordem de precedência:

1. `superuser`;
2. `gerente_superintendencia` — vínculo `EquipeGerencia` vigente com papel GERENTE na
   gerência da Superintendência (com escopo: fora dela vale a próxima base);
3. `capacidade_aprovar` — a capacidade `approve_solicitation`, que vem do pacote do perfil
   da gerência: ADMIN_OPERACIONAL (DAT) e CONTROLE. Sem escopo.

**Nenhum grupo Django aprova**: o poder vem só da lotação (`RBAC_FONTE` padrão
`lotacao`). O Controle também aprova, coisa que o texto de 2025-10-23 não previa. Além da
base, `decisoes_impedidas` (em `solicitacao_approval.py`) barra a decisão sobre
solicitação que o próprio ator criou ou editou e, numa janela de 30 dias, quando ator e autor
alteraram a conta um do outro ou a mesma pessoa alterou as duas (segregação de funções; o
superusuário decide tudo, com break-glass registrado).

SSOT da política: `v2/docs/specs/domain/politica-aprovacao.spec.md` (PA-02). PA-01 e
PA-03 a PA-07 seguem valendo como decididos.

## References

- CP-02 (Cláusula Pétrea)
- `v2/docs/specs/domain/politica-aprovacao.spec.md` (PA-02 vivo)
- `v2/backend/apps/core/rbac/policies.py` (`solicitation_approval_basis`)
- `v2/backend/apps/core/services/solicitacao_approval.py`
- `v2/backend/apps/core/services/solicitacao_availability.py` (guard + advisory lock, #1452)
- `v2/backend/apps/core/tests/test_approval_policy_PA.py`
- `v2/docs/specs/backend/solicitacao-approval.spec.md` (spec viva)
- `v2/docs/IMPLEMENTACAO_PA.md`
