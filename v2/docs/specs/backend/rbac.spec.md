---
title: RBAC — Controle de Acesso
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/rbac/__init__.py
  - v2/backend/apps/core/rbac/permissions.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/rbac/matrix.py
  - v2/backend/apps/core/rbac/helpers.py
  - v2/backend/apps/core/rbac/constants.py
  - v2/backend/apps/core/constants.py
  - v2/backend/apps/core/services/rbac_permissions.py
  - v2/backend/apps/core/services/functional_permissions_seed.py
  - v2/backend/apps/core/views/me.py
  - v2/backend/apps/core/signals.py
  - v2/backend/scripts/rbac_lint.py
owner: backend
supersedes:
  - v2/docs/RBAC_NAMING.md
  - v2/docs/rbac_authorization_matrix.md
  - v2/docs/GUIA_ADMIN_RBAC.md
related:
  - v2/docs/specs/backend/approvals.spec.md
  - v2/docs/specs/backend/availability.spec.md
---

# RBAC — Controle de Acesso

## Propósito

O módulo `apps.core.rbac` é o SSOT da autorização do Aprender Sistema v2. Implementa o modelo NIST RBAC de 3 camadas — `User → Roles (Groups Django) → Capabilities (PermissaoFuncional) ← Policies (CanXxx) ← Views` — separando **o que** a pessoa pode fazer (capability) de **quem** ela é organizacionalmente (setor/função). A consequência prática: se a organização reestrutura (DAT vira "Operações Administrativas"), só muda `Group.name`; zero linha de código de autorização muda.

Existem três conceitos ortogonais: **capability** (autorização binária por feature), **scope** (filtragem de dados — vê só o próprio setor/gerência/queryset) e **policy** (composição declarativa de capabilities exposta como classe `CanXxx`). Autorização passa SEMPRE por `HasPerm(codename)` / `user.has_perm()` / `user_has_any_perm` — nunca por nome de grupo, padrão banido pelo lint (ver §Contratos).

## Fonte de verdade no código

- [`v2/backend/apps/core/rbac/__init__.py`](../../../backend/apps/core/rbac/__init__.py) — superfície pública do módulo (re-exporta classes, helpers e a matriz de policies).
- [`v2/backend/apps/core/rbac/permissions.py`](../../../backend/apps/core/rbac/permissions.py) — classes DRF: `HasPerm` (paramétrica), `HasFunctionalPermission` (base) e as 3 classes não-reduzíveis + 1 composite (`IsGerenteSuperintendencia`, `IsOwnerOrPrivileged`, `HasSectorAccess`, `IsAssistenteAdministrativoControle`). Aplica o monkey-patch de `permissions.OR/AND/NOT.__call__` que habilita composition em instâncias.
- [`v2/backend/apps/core/rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) — Capability Policy Layer: matriz `ACCESS_POLICIES` (policy key → frozenset de capabilities elegíveis, semântica OR), classes `Can*`, `PUBLIC_POLICY_KEYS`, e os SSOT `user_has_policy` / `resolve_public_policies`.
- [`v2/backend/apps/core/rbac/matrix.py`](../../../backend/apps/core/rbac/matrix.py) — Matriz Viva `ACCESS_MATRIX` (10 atores × recursos discriminantes → status HTTP esperado) para testes parametrizados.
- [`v2/backend/apps/core/rbac/helpers.py`](../../../backend/apps/core/rbac/helpers.py) — `user_has_any_perm`, `user_has_all_perms`, `user_is_assistente_administrativo_controle`.
- [`v2/backend/apps/core/rbac/constants.py`](../../../backend/apps/core/rbac/constants.py) — constantes de **data scope** (`COORDENADOR_ROLE_GROUPS`, `FORMADOR_ROLE_GROUPS`) — usadas para filtrar queryset, não para autorizar.
- [`v2/backend/apps/core/constants.py`](../../../backend/apps/core/constants.py) — `SETOR_GROUPS` (13 setores), `FUNCAO_GROUPS` (5 funções), `ALLOWED_USER_GROUPS`, `RESERVED_GROUPS`.
- [`v2/backend/apps/core/services/rbac_permissions.py`](../../../backend/apps/core/services/rbac_permissions.py) — `get_user_functional_permissions` (resolução cache-aware das capabilities do usuário) + helpers de invalidação por usuário/grupo.
- [`v2/backend/apps/core/services/functional_permissions_seed.py`](../../../backend/apps/core/services/functional_permissions_seed.py) — `FUNCTIONAL_PERMISSIONS_SEED`: SSOT dos codenames, labels, categorias e grupos default de cada capability.
- [`v2/backend/apps/core/views/me.py`](../../../backend/apps/core/views/me.py) — `MePoliciesView` (`GET /api/me/policies/`).
- [`v2/backend/apps/core/signals.py`](../../../backend/apps/core/signals.py) — signal `m2m_changed` em `PermissaoFuncional.groups`: invalida cache + grava `AuditLog GROUP_CAPABILITY_CHANGED`.
- [`v2/backend/scripts/rbac_lint.py`](../../../backend/scripts/rbac_lint.py) — lint AST (V001/V002/V003) que enforça a convenção em CI.

Doc canônico detalhado (não duplicado aqui): convenção de nomes em [`RBAC_NAMING.md`](../../RBAC_NAMING.md), matriz declarativa ator × recurso em [`rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md), e operação via Admin em [`GUIA_ADMIN_RBAC.md`](../../GUIA_ADMIN_RBAC.md).

## Contratos e invariantes

- **Idioma canônico**: `permission_classes = [IsAuthenticated, HasPerm("codename")]`. Composition por instância: `HasPerm("a") | HasPerm("b")` (OR), `& ` (AND), `~` (NOT). Para OR semântico recorrente (≥3 caps ou compartilhado entre views) usa-se uma Policy `Can*`.
- **Grupos diretos são banidos**: `user.groups.filter(name=...)` em `apps/core/views*` ou `apps/core/services/` é violação **V001** do lint. Usos legítimos (composite, block, data-scope) exigem marcador `# noqa: RBAC-<tipo>-allowed` na linha. Classes `class Is<Word>(...)` fora da whitelist (`IsGerenteSuperintendencia`, `IsOwnerOrPrivileged`) são violação **V002**. Mutação de `PermissaoFuncional.groups` / `Group.permissions` em migration de `apps/core/` acima do cutoff D17 (número > 82) é violação **V003**. CI job `[required] backend rbac-lint`.
- **Codename é capacidade, não identidade**: formato `verb_noun[_qualifier]` snake_case inglês. Proibido nome de setor/função/grupo. Exceções bundle conscientes: `manage_admin_registries`, `manage_purchases_and_materials`.
- **Superuser sempre bypassa**: toda classe e helper retorna `True` para `is_superuser` antes de qualquer checagem.
- **Fail-secure**: usuário anônimo/`None` → `False`; policy key ausente da matriz → `False`; capability sem grupos no seed → só superuser passa (feature em incubação).
- **D17 — Admin-driven Group × Capability**: a atribuição grupo↔capability migra para o Django Admin superuser-only (`PermissaoFuncionalAdmin`). Codename/label/category/existência da capability são read-only (SSOT no seed); só `groups` é editável. Toda edição invalida cache (signal `m2m_changed`) e grava `AuditLog GROUP_CAPABILITY_CHANGED`.
- **Policy key = contrato externo estável** (uma vez em `PUBLIC_POLICY_KEYS`): adicionar key é compatível; renomear/remover é breaking (deprecation de 2 releases); mudar capabilities elegíveis (`ACCESS_POLICIES[k]`) é compatível (frontend não depende). O endpoint nunca vaza capability codenames.
- **SSOT da semântica de policy**: `user_has_policy(user, key)` é a fonte única; `_PolicyPermission.has_permission`, os testes e `resolve_public_policies` delegam para ele. Mudar avaliação = mudar num só lugar.
- **Aprovação de solicitações (CP-02, PA-01)**: gate composite `CanAccessSolicitationApprovals` = Gerente da Superintendência (Setor `Superintendência` + Função `Gerente`) **OU** Assistente Administrativo do Controle (Setor `Controle` + Função `Assistente Administrativo`). Superuser nunca auto-aprova evento próprio (regra do importer, fora deste módulo). Detalhe em `approvals.spec.md`.

## API / Interface

**Classes DRF** (import via `from apps.core.rbac import ...`):

- `HasPerm("codename")` — checa uma capability; aceita prefixo `core.` opcional. Suporta `| & ~`.
- `HasSectorAccess` — scope dinâmico por `gerencia_id` (query/kwargs); sem `gerencia_id` exige `EquipeGerencia` ativa. Idiomático: `[IsAuthenticated, CanViewAllAvailability | HasSectorAccess]`.
- `IsGerenteSuperintendencia` — composite funcperm `approve_solicitation_batch` + grupo `Gerente`.
- `IsOwnerOrPrivileged` — object-level: superuser/privilegiado ou `obj.usuario == user`.
- `IsAssistenteAdministrativoControle` — composite Setor `Controle` + Função `Assistente Administrativo`.
- 17 classes `Can*` (`CanAccessAuditLogs`, `CanViewComprasDashboard`, `CanViewAllAvailability`, `CanAccessSolicitationApprovals`, ...) mapeadas em `ACCESS_POLICIES`.

**Helpers** (não-DRF): `user_has_any_perm(user, *codenames)`, `user_has_all_perms(...)`, `user_has_policy(user, key)`, `user_is_assistente_administrativo_controle(user)`, `user_can_delegate_availability_block(user)`.

**Endpoint**: `GET /api/me/policies/` (`IsAuthenticated`) → array JSON ordenado das `PUBLIC_POLICY_KEYS` que o usuário possui (subset de `ACCESS_POLICIES`). Anonymous → 401; superuser → todas as públicas; regular → subset (OR). Consumido pelo frontend para menu condicional/redirects.

**Setores (13)** e **Funções (5)**: SSOT em `SETOR_GROUPS` / `FUNCAO_GROUPS` (`apps/core/constants.py`). Funções: Formador, Coordenador, Apoio de Coordenação, Gerente, Assistente Administrativo.

## Fluxos principais

1. **Checagem em request DRF**: DRF instancia a classe → `has_permission` rejeita não-autenticado, libera superuser, e consulta `get_user_functional_permissions(user)` (cache Redis, TTL) testando `codename in perms`. Composition `A | B` é resolvida pelas classes `OR/AND/NOT` do DRF (habilitadas em instâncias pelo monkey-patch).
2. **Resolução de policy**: `user_has_policy(user, key)` → anônimo `False` → superuser `True` → composite key delega a helper dedicado (ex: `_user_has_solicitation_approvals`) → caso geral `user_has_any_perm(user, *ACCESS_POLICIES[key])`.
3. **Mudança de atribuição (admin)**: superuser edita `PermissaoFuncional.groups` no Admin → signal `m2m_changed` consolida as 6 disparadas (pre/post × add/remove/clear) → invalida cache funcional dos usuários afetados (sem restart) → grava `AuditLog GROUP_CAPABILITY_CHANGED` (added/removed/groups_after).
4. **Erros relevantes**: capability sem grupo no seed → 403 a todos exceto superuser; `gerencia_id` não-inteiro em `HasSectorAccess` → 403 com mensagem "gerencia_id deve ser um número inteiro"; Controle puro tentando aprovar (sem Função `Assistente Administrativo`) → 403.

## Decisões relacionadas (ADRs)

- Princípios de naming, vocabulário de verbos e enforcement: [`RBAC_NAMING.md`](../../RBAC_NAMING.md) (Epic 2; §8/D17 Admin-driven).
- Matriz declarativa ator × recurso e motivo legítimo de acesso: [`rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md).
- Decisões D7–D9 (Grade Mensal / Diretoria / DAT transversal), D17 (Admin-driven), PR 3 (composite aprovações), PR 5/6 (lookup/audit hardening) — registradas como comentários rastreáveis em `policies.py` e `matrix.py`.

## Testes que cobrem

- [`v2/backend/apps/core/tests/test_rbac_matrix_contract.py`](../../../backend/apps/core/tests/test_rbac_matrix_contract.py) — paridade código × `ACCESS_MATRIX`; CI vermelho se um ator ganha/perde acesso.
- [`v2/backend/apps/core/tests/test_rbac_matrix_living.py`](../../../backend/apps/core/tests/test_rbac_matrix_living.py) e [`test_rbac_matrix_endpoint_coverage.py`](../../../backend/apps/core/tests/test_rbac_matrix_endpoint_coverage.py) — Matriz Viva + cobertura de endpoints.
- [`v2/backend/apps/core/tests/test_rbac_policies.py`](../../../backend/apps/core/tests/test_rbac_policies.py) e [`test_rbac_policies_contract.py`](../../../backend/apps/core/tests/test_rbac_policies_contract.py) — semântica de `user_has_policy` + contrato `ACCESS_POLICIES`/`PUBLIC_POLICY_KEYS`.
- [`v2/backend/apps/core/tests/test_me_policies.py`](../../../backend/apps/core/tests/test_me_policies.py) — `GET /api/me/policies/` (incl. test de paridade que obriga registrar `Can*` nova como pública).
- [`v2/backend/apps/core/tests/test_rbac_permissions.py`](../../../backend/apps/core/tests/test_rbac_permissions.py), [`test_rbac_helpers.py`](../../../backend/apps/core/tests/test_rbac_helpers.py) — classes DRF e helpers.
- [`v2/backend/apps/core/tests/test_rbac_lint.py`](../../../backend/apps/core/tests/test_rbac_lint.py) — self-test do lint (aceita baseline, rejeita padrões banidos).
- [`v2/backend/apps/core/tests/test_pr3_approvals_policy.py`](../../../backend/apps/core/tests/test_pr3_approvals_policy.py), [`test_pr6_audit_logs_policy.py`](../../../backend/apps/core/tests/test_pr6_audit_logs_policy.py) — gates compostos endurecidos.
- [`v2/backend/apps/core/tests/test_rbac_labels_capability_oriented.py`](../../../backend/apps/core/tests/test_rbac_labels_capability_oriented.py), [`test_rbac_seed.py`](../../../backend/apps/core/tests/test_rbac_seed.py) — convenção de labels e seed idempotente.

## Pontos de atenção / dívidas conhecidas

- **Divergência doc × código (V003)**: `RBAC_NAMING.md §7` afirma "V003 (import de Group) foi descartado", mas `scripts/rbac_lint.py` **implementa** V003 com sentido diferente (proíbe mutação de `PermissaoFuncional.groups`/`Group.permissions` em migrations de `apps/core/` acima do cutoff D17=82). O texto do §7 está desatualizado; a fonte de verdade é o lint. Corrigir o §7.
- **`GUIA_ADMIN_RBAC.md` lista "Gerência" como setor genérico**; o SSOT `SETOR_GROUPS` não contém "Gerência" (são 13 setores nomeados). Guia precisa alinhar.
- **Cutoff D17 hardcoded** (`D17_LEGACY_MIGRATIONS_MAX = 82`): migrations futuras que precisem backfill legítimo de grupos exigem `# noqa: RBAC-migration-allowed` consciente.
- **Composition OR em instâncias depende de monkey-patch** (`permissions.OR/AND/NOT.__call__ = lambda self: self`) aplicado em `permissions.py`; `policies.py` força o import por side-effect. Remover o patch quebra silenciosamente todo `permission_classes = [A | B]`.
- **`HasSectorAccess` é o único ponto com TOCTOU residual** de scope: a checagem de `EquipeGerencia` ativa e a leitura de dados acontecem em requests separados; mudança de vínculo entre eles não é transacional (aceitável para o caso de uso atual).
- **Schema OpenAPI de `/api/me/policies/`** declara `{policies: [...]}` via `inline_serializer`, mas o código retorna o array bruto. Divergência de documentação de schema (não afeta o contrato real consumido pelo frontend).
