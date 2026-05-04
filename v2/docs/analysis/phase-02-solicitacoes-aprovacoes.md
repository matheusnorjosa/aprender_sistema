# Phase 02 — Solicitações e Aprovações (PA)

Date: 2026-02-04
Scope: v2 only
Status: Completed

> 📜 **Análise histórica:** produzida antes do hardening RBAC. O diagnóstico
> de "Permissões desalinhadas entre UI e API" foi resolvido nos PRs #1308 e
> #1315: backend e frontend convergiram para a policy
> `access_solicitation_approvals` (composite Setor × Função). DAT, Controle
> puro e Gerente pedagógico não aprovam mais. `can_approve_super` permanece
> em `/api/me/` apenas como contrato legado. Estado atual em
> [`rbac_authorization_matrix.md`](../rbac_authorization_matrix.md) §3 e §6 (D10).

## Explored
- v2/docs/IMPLEMENTACAO_PA.md
- v2/docs/PROJETO_ORIGEM.md
- docs/business-rules/politica-aprovacao.md
- v2/backend/apps/core/models/solicitacao.py
- v2/backend/apps/core/serializers/solicitacao.py
- v2/backend/apps/core/views_solicitacao.py
- v2/backend/apps/core/services/solicitacao_approval.py
- v2/backend/apps/core/services/solicitacao_publish.py
- v2/backend/apps/core/views_validate.py
- v2/backend/apps/core/views/availability.py
- v2/backend/apps/core/tests/test_approval_policy_PA.py
- v2/backend/apps/core/tests/test_solicitacao_fluxo.py
- v2/backend/apps/core/tests/test_pr8_nova_solicitacao.py
- v2/frontend/src/pages/Solicitacoes/NewSolicitacaoWizard.tsx
- v2/frontend/src/pages/Solicitacoes/MySolicitacoesPage.tsx
- v2/frontend/src/pages/Solicitacoes/EditSolicitacaoPage.tsx
- v2/frontend/src/pages/Aprovacoes/ApprovalsPage.tsx
- v2/frontend/src/api/solicitacoes.ts

## What Was Implemented
- Fluxo SUPER e NAO_SUPER com auto-aprovação para NAO_SUPER na criação.
- Approve/reject individuais e batch com AuditLog.
- Publicação no Google Calendar bloqueada para solicitações não aprovadas.
- UI de criação/edição/listagem e aprovação.
- Regras de edição e exclusão (publicado no GCal e reprovado bloqueiam edição).

## Findings (Ordered by Severity)
High
- Criação de solicitação não valida conflitos de disponibilidade no backend. O endpoint de criação não chama check_conflicts e o UI não chama availability/check. Um cliente pode criar eventos conflitantes ao ignorar pré-checagem. Arquivos: v2/backend/apps/core/views_solicitacao.py, v2/backend/apps/core/services/availability_service.py, v2/frontend/src/components/FormadoresPicker.tsx
- Aprovação/reprovação permite transições fora de “pendente”. approve_solicitacao não bloqueia status reprovado e reject_solicitacao não bloqueia status aprovado. Isso permite estados indevidos sem trilha clara de decisão. Arquivo: v2/backend/apps/core/services/solicitacao_approval.py

Medium
- Política de aprovação com inconsistências entre documentos e código. Implementacao_PA.md afirma “sem auto-aprovação”, mas o modelo auto-aprova NAO_SUPER; PA-02 ora exige Gerente+Super, ora permite DAT. Arquivos: v2/docs/IMPLEMENTACAO_PA.md, v2/docs/PROJETO_ORIGEM.md, docs/business-rules/politica-aprovacao.md, v2/backend/apps/core/permissions.py
- Permissões desalinhadas entre UI e API: approve/reject individual aceita DAT (IsSuperintendencia), mas UI usa can_approve_super (Gerente+Super). Batch usa IsGerenteSuperintendencia. Isso cria acesso desigual e inconsistência de operação. Arquivos: v2/backend/apps/core/views_solicitacao.py, v2/backend/apps/core/permissions.py, v2/frontend/src/pages/Aprovacoes/ApprovalsPage.tsx

Low
- AuditLog de approve não registra justificativa e user_agent, embora estejam disponíveis. Arquivo: v2/backend/apps/core/services/solicitacao_approval.py
- Solicitações sem projeto retornam fluxo “NAO_SUPER” no serializer, mesmo que status permaneça pendente, podendo confundir UI. Arquivo: v2/backend/apps/core/serializers/solicitacao.py
- Edição de coordenadores acompanhantes não é suportada no fluxo atual. O update só trata formadores. Arquivos: v2/backend/apps/core/views_solicitacao.py, v2/frontend/src/pages/Solicitacoes/EditSolicitacaoPage.tsx
- Documentação de PA contém paths e comportamento desatualizados. Arquivo: v2/docs/IMPLEMENTACAO_PA.md

## Tests
- Não foi possível executar pytest: ambiente sem pip/pytest.
- Opção: rodar testes via Docker Compose no serviço web (ex.: test_approval_policy_PA.py, test_solicitacao_fluxo.py).

## Notes (Execution Thoughts)
- Foquei nos pontos de transição de estado (pendente → aprovado/reprovado) e nos controles de permissão.
- Verifiquei se a disponibilidade é validada no servidor ou apenas no cliente.
- Cruzei docs com código e testes para identificar divergências.

## Summary
- O fluxo SUPER/NAO_SUPER está implementado, mas falta enforcement server-side de disponibilidade.
- Aprovação/reprovação permite mudanças indevidas de status.
- Existe divergência significativa entre documentação, UI e permissões do backend.

## Next Phase
- Phase 03: Disponibilidade (RD) + Bloqueios + Grade Mensal
