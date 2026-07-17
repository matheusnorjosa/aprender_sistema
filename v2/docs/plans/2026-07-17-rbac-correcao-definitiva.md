# Plano de Correção Definitiva RBAC — 2026-07-17

Objetivo: **cura de raiz**, não paliativo. Cada onda elimina uma classe de vetor
(privilégio Tier-0, escopo por ação×gerência, revogação, cache, integridade da
matriz) de forma permanente — nenhuma é band-aid. O sequenciamento é por
*deployabilidade e risco vivo*, não por "fatiar o conserto".

Status:
- **Wave 1 (P0-0) — ✅ IMPLEMENTADO** na branch `fix/rbac-superuser-target-protection`
  (28 testes RED→GREEN; suíte `apps/core` 2855 passed sem regressão). Aguarda
  revisão + `make staging-full` + commit.
- Demais ondas: **propostas**; Wave 5 (aprovação) depende da ratificação A-01/A-02 (Wave 0).

Auditoria de origem: `v2/docs/audits/2026-07-17-rbac-security-audit.md`
Princípio: TDD (RED prova o comportamento **seguro** ausente, nunca documenta o exploit como sucesso).

**Ordem de execução:** P0-0 (fronteira Tier-0, backend-only) → contenção operacional → P0-A Tier-0 → P0-B solicitações → P1 scope/revogação → aprovação ratificada → cliente/config → governança.

---

## Contrato de autorização (o que deve valer)
```
capability/policy  → QUAL ação o usuário pode executar
EquipeGerencia(ativo=True) → sobre QUAIS gerências/linhas a ação incide
superuser          → bypass global explícito, auditado, Tier-0
frontend           → UX; nunca fronteira de segurança
Grupo × Capability → Tier-0; administrado só no Django Admin superuser-only (D17)
```
Regras: capability de editar/aprovar/criar não concede visão global; setor/função não concede acesso por inferência; objeto fora do escopo de leitura → 404 (indistinguível de inexistente); vínculo inativo revoga imediatamente; projeto/gerência nulos falham fechado para não-owner.

---

## Wave 0 — Evidência + decisões (paralelo; não bloqueia P0-0/P0-1)
- **Exportar matriz efetiva de prod read-only** (capability→grupos, grupo→caps, ausentes/inesperadas, migrations aplicadas, memberships privilegiadas em relatório restrito). ✅ **Feito nesta rodada** — ver auditoria §2 (PF_COUNT=16, matriz confirmada).
- **Ratificar (decisões de negócio):**
  - **A-01**: Gerente da Superintendência aprova global ou só gerências vinculadas?
  - **A-02**: Assistente Administrativo do Controle é transversal/global ou escopado por gerência?
  - criação/transferência de solicitação por gerência;
  - reset/delete de conta comum pelo DAT (G2);
  - operador de configuração do sistema.
- **Continuidade operacional (G3)**: designar superuser operacional primário + backup; runbook de onboarding/revogação; SLA de revogação; teste de break-glass e prevenção de lockout.
- Preservar logs antes dos hotfixes.

## Wave 1 — P0-0 isolado (hotfix backend-only, deployável já)
Arquivos prováveis: `apps/core/views/admin.py`, `apps/core/serializers/usuario.py`, `apps/core/services/usuarios_import.py`, `apps/core/rbac/permissions.py` (classe `SuperuserOnly`).
- `SuperuserOnly` real (`is_superuser`, **não** `IsAdminUser`/`is_staff`).
- não-superuser: queryset exclui `is_superuser=True`; retrieve/update/delete/`assign_groups` contra superuser → **404**; serializer repete a proteção; importação por CPF rejeita alterar conta superuser; delete do último superuser ativo impedido.
- DAT **continua** administrando contas comuns; reset de senha de comum permanece até decisão G2.
- Cobrir `/api/` **e** `/api/v1/`.
- **RED**: DAT `PATCH` contra superuser com senha válida → esperado 404 + senha/campos inalterados (hoje: 200 + senha alterada). Cobertura: senha, `is_active`, cadastrais, `group_ids`, delete, `assign_groups`, import por CPF, listagem/filtro, ambos aliases, superuser continua autorizado, DAT continua administrando comum.
- **Pós-deploy**: revisar access logs; **rotacionar senha de todos os superusers**; invalidar sessões; validar primário+backup. (Rotação = precaução responsável, não afirmação de exploração.)

## Wave 2 — P0-A Tier-0 (co-deploy backend+frontend)
Pré-requisito: continuidade operacional (Wave 0) definida.
- Grupo × Capability **só no Django Admin superuser-only**; memberships **só superuser**.
- remover `permissao_funcional_ids` da escrita REST; proteger `assign_groups`, `sync_members`, rename/delete de grupo reservado (remover bypass `confirm_reserved`).
- frontend DAT: memberships read-only; payload omite `group_ids` (`usuario_form_helpers.ts:50` sempre envia hoje → co-deploy obrigatório); backend rejeita mutação de membership por não-superuser.
- corrigir invalidação reversa de cache (P1-3) + serviço transacional de auditoria (P2-2) neste PR.
- **Não criar `manage_rbac`** (circular). Delegação futura = RFC separado com separação de funções, **nunca** editando Grupo×Capability.

## Wave 3 — P0-B solicitações por ação × gerência
Independe da decisão de aprovação. Novo `apps/core/services/solicitacao_scope.py`:
```
scope_for_list(user) · scope_for_edit(user) · scope_for_approval(user) · can_use_project(user, project)
```
- superuser global; owner vê o próprio; Gerente escreve só em gerências com `EquipeGerencia(papel="GERENTE", ativo=True)`; Coord/Apoio owner-only até decisão.
- leitura global nunca amplia escrita; `mine=true` owner-only; objeto fora do scope == inexistente (404); `projeto`/`projeto.gerencia` nulos fail-closed para não-owner; POST valida gerência do projeto; PATCH/PUT validam origem **e** destino; vínculo inativo revoga imediato.
- queryset, serializer e service reutilizam os mesmos predicados. Cobrir `/api/` e `/api/v1/`.

## Wave 4 — P1 scope ativo + revogação
- helper central de vínculos ativos; corrigir Grade Mensal + caso misto (predicado `ativo=True AND papel∈{GERENTE,COORDENADOR,APOIO}` na permission, no queryset das gerências e na composição dos usuários; global só superuser/`view_all_availability`).
- corrigir bloqueios (`views_availability.py`), deslocamentos (`views_deslocamento.py`), stats (`stats.py`).
- escopar `check`/`check-many` de disponibilidade por gerência ativa compartilhada (lote: ID fora do scope → 403 total, sem parcial).
- corrigir cache reverse/delete de grupo; provar revogação imediata com cache pré-populado.

## Wave 5 — Aprovação (após A-01/A-02)
- **Global**: registrar explicitamente na spec (para os dois composites) + testes cross-gerência positivos.
- **Escopado**: Gerente Sup por vínculos ativos de Gerente; Assistente Controle exige migration/modelo de delegação próprio (usuário×gerência×tipo×ativo), dry-run, backfill revisado; services recebem queryset autorizado; inacessível == inexistente; lote preserva parcial só para itens autorizados; nenhuma linha inacessível é lida/bloqueada/alterada.

## Wave 6 — Cliente e configuração
- retirar **toda** `/api/` do CacheStorage (network-only; offline 503; bump de versão; apagar caches `aprender-v2-api-*` na ativação; purge no logout). Teste: sessão A → logout → sessão B/offline sem retorno de A.
- `manage_system_config` em duas fases (metadata sem grupo → atribuição manual verificada no Admin → troca do gate); `view_system_config` separado se leitura/escrita tiverem atores diferentes.
- backend publica policy keys estáveis + contrato TypeScript verificável; um mapa único controla rota/menu/ação; remover `LegacyAccessFlags`; menu oculto e deep-link negado concordam.

## Wave 7 — Governança
- seed preservadora por padrão (reset destrutivo = comando dev-only separado, dry-run+confirmação); capability nova nasce sem grupo.
- serviço único de auditoria (ator + before/after, on-commit); remover buffer global `_PENDING_GROUP_CAP_DELTAS`; auditar senha/delete/assign_groups/import/CRUD REST de grupos/caps; tentativa negada contra alvo privilegiado gera evento de segurança.
- redirecionar facades para `views_availability.py`, migrar testes, remover `views/availability.py` e `IsGerenteSuperintendencia`; reconciliar specs com o código.
- **Fora deste plano** até RFC + inventário de consumidores: `manage_org_structure`, `operate_gcal`, delegação ampla de RBAC.

---

## Gates de verificação (por PR)
```bash
# Backend
docker exec aprender_dev-web-1 pytest <testes-alvo> -v --no-migrations
docker exec aprender_dev-web-1 python scripts/rbac_lint.py apps/
docker exec aprender_dev-web-1 pytest apps/core/tests/ -q --no-migrations
cd v2/backend && pyright apps/core config
# PR com migration:
docker exec aprender_dev-web-1 python manage.py makemigrations --check --dry-run
# Frontend (host):
cd v2/frontend && npm test -- --run <alvo> && npm run typecheck && npm run lint && npm run build && npm run test:checklist
# Antes de Ready:
cd v2 && make staging-full           # 8/8 + 3 marcadores no PR body
# Pós-código:
graphify update .
```

## Critérios finais de aceite
1. DAT não descobre nem muta superusers. 2. Nenhum não-superuser altera Grupo×Capability ou memberships. 3. Gerente não lê/escreve fora da gerência autorizada. 4. Leitura global nunca amplia escrita. 5. Vínculo inativo revoga imediato. 6. Formador/Diretoria não entram na Grade por vínculo acidental (nem caso misto). 7. APIs nunca cacheadas pelo service worker. 8. Inacessível == inexistente onde há scope. 9. Auditoria identifica ator/alvo/delta. 10. Seed normal nunca modifica a matriz administrada. 11. `/api/` e `/api/v1/` idênticos. 12. Matriz efetiva de prod exportada e confrontada com a intenção aprovada. 13. Specs de deploy/aprovação/disponibilidade/RBAC refletem o código.

## Riscos de implementação
DAT depende hoje de editar grupos no fluxo cadastral (P0-A muda o processo — G3). Frontend sempre envia `group_ids` (co-deploy). Usuários podem depender de acessos cross-gerência indevidos (403 pós-fix não é regressão). Assistente Administrativo não cabe em `PAPEL_CHOICES` (enforcement prematuro = lockout). Objetos com projeto/gerência nulos precisam de relatório antes do enforcement. `views_availability.py` tem trabalho concorrente do #1452 — PRs que o tocam entram após merge/rebase. Cache/auditoria exigem testes concorrentes.