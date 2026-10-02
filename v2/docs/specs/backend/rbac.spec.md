---
title: RBAC — Controle de Acesso
status: canonical
last_verified: 2026-09-30
verified_at_commit: 0dd1dcb630fdc1cf9b2b488121553e89488dde3c
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
  - v2/backend/apps/core/services/solicitacao_scope.py
  - v2/backend/apps/core/views/me.py
  - v2/backend/apps/core/signals.py
  - v2/backend/scripts/rbac_lint.py
owner: backend
supersedes:
  - v2/docs/RBAC_NAMING.md
  - v2/docs/rbac_authorization_matrix.md
  - v2/docs/GUIA_ADMIN_RBAC.md
related:
  - v2/docs/specs/backend/solicitacao-approval.spec.md
  - v2/docs/specs/backend/availability.spec.md
  - v2/docs/audits/ACHADOS_REAIS.md
---

# RBAC — Controle de Acesso

> ⚠️ **Estado dos gaps de segurança — reverificado em 2026-07-24.** A fila de trabalho viva é
> [`v2/docs/audits/ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md); as severidades daquele documento são as que valem.
> O relatório longo `2026-07-17-system-module-audit.md` acerta os mecanismos e erra as consequências — **não citar
> severidade dele**.
>
> **Já fechados e presentes no SHA de produção (`94f27651`):**
>
> - **Takeover de superuser** (antigo P0-0) — `86afdef3` / #1558. `UsuarioAdminViewSet.get_queryset` faz
>   `exclude(is_superuser=True)` para não-superuser (`UsuarioAdminViewSet.get_queryset` em `views/admin.py`), há anti-lockout (`perform_destroy`) e
>   `assign_groups` é `SuperuserOnly` (decorator `@action` em `views/admin.py`). Teste: `tests/test_rbac_superuser_target_protection.py`.
>   (A branch `fix/rbac-superuser-target-protection` citada aqui antes **não existe mais** — foi mergeada.)
> - **Escalada via `GroupViewSet`** (antigo P0-1) — #1567. `get_permissions` devolve `SuperuserOnly` para tudo que não
>   seja `list`/`retrieve` (`GroupViewSet.get_permissions` em `views/admin.py`). Registrado como `M05-01`/`M05-02` em `ACHADOS_REAIS.md`
>   (§"Já corrigidos").
> - **Auto-escalação via import de usuários** (antigo `M03-01`, **P0**) — `ccbe1e05` / #1610. A concessão de grupos
>   no import passou a ser **gated por superuser**: `_actor_pode_atribuir_grupos` (em `services/usuarios_import.py`)
>   só é `True` p/ `actor.is_superuser`; a decisão (`aplicar_grupos` em `_process_row`) e `_assign_groups` aplicam o gate, e um ator
>   não-superuser recebe `grupos_ignorados`. O importer export-contract concede só a allowlist `ALLOWED_USER_GROUPS`
>   (`_apply_usuario` em `services/export_contract_importer.py`). O residual ator×alvo em **outros** writers segue no épico #1656
>   (`M07-02`). Ver [imports.spec](./imports.spec.md).
> - **Auditoria de Grupo×Capability não-invariante + PII** (antigo `M05-05`, épico #1657) — #1672. O buffer de módulo
>   `_PENDING_GROUP_CAP_DELTAS` / `flush_group_capability_audit` **não existe mais**; a escrita via REST audita em
>   `GroupSerializer.create` e `GroupSerializer.update` (`serializers/usuario.py`) via `auditar_group_capabilities_set`, o Admin em
>   `PermissaoFuncionalAdmin.save_related` (`admin.py`), e o signal `_on_permissao_funcional_groups_changed` (`signals.py`) só faz cache-bust. PII redigida em `_PII_KEYS_TO_MASK`
>   e `_redact_details` (`redact_cpf`), em `serializers/auditoria.py`.
>
> **Ainda abertos e reconfirmados vivos** (ver a tabela de `ACHADOS_REAIS.md` para severidade e issue):
> escopo ator×alvo ausente em vários writers (épico #1656, inclui `M10-01` solicitações cross-gerência —
> fechado para o Gerente pedagógico e, pela regra do dono de 30/09, para a aprovadora por vínculo (§Contratos) —,
> `M07-02` takeover de conta aprovadora pelo DAT e `M14-01` `HasSectorAccess`). O cache de revogação ao
> excluir um Group (`M05-03`, épico #1667) foi **RESOLVIDO no #1791** — ver §Contratos abaixo. As seções
> abaixo descrevem o código **como ele é**; onde a intenção diverge do real, isso está marcado explicitamente.
>
> **Bus factor de 1.** Há **1 superuser ativo** em produção (censo de 2026-07-20, `ACHADOS_REAIS.md` §F3), e o #1567
> tornou a administração de Grupo×Capability superuser-only. Se essa conta cair, ninguém administra RBAC. A decisão
> "superuser primário + backup" segue pendente.

## Propósito

O módulo `apps.core.rbac` é o SSOT da autorização do Aprender Sistema v2. Implementa o modelo NIST RBAC de 3 camadas — `User → Roles (Groups Django) → Capabilities (PermissaoFuncional) ← Policies (CanXxx) ← Views` — separando **o que** a pessoa pode fazer (capability) de **quem** ela é organizacionalmente (setor/função). A consequência prática: se a organização reestrutura (DAT vira "Operações Administrativas"), só muda `Group.name`; zero linha de código de autorização muda.

Existem três conceitos ortogonais: **capability** (autorização binária por feature), **scope** (filtragem de dados — vê só o próprio setor/gerência/queryset) e **policy** (composição declarativa de capabilities exposta como classe `CanXxx`). Autorização passa SEMPRE por `HasPerm(codename)` / `user.has_perm()` / `user_has_any_perm` — nunca por nome de grupo, padrão banido pelo lint (ver §Contratos).

## Fonte de verdade no código

- [`v2/backend/apps/core/rbac/__init__.py`](../../../backend/apps/core/rbac/__init__.py) — superfície pública do módulo (re-exporta classes, helpers e a matriz de policies).
- [`v2/backend/apps/core/rbac/permissions.py`](../../../backend/apps/core/rbac/permissions.py) — **7 classes DRF**: `HasPerm` (paramétrica), `HasFunctionalPermission` (base), `SuperuserOnly` e as 4 não-reduzíveis/composite `IsGerenteSuperintendencia`, `IsAssistenteAdministrativoControle`, `IsOwnerOrPrivileged`, `HasSectorAccess`. Aplica o monkey-patch de `permissions.OR/AND/NOT.__call__` que habilita composition em instâncias. **`SuperuserOnly` é a classe Tier-0** que sustenta o gate de escrita do `GroupViewSet` e do `assign_groups` (#1567/#1558) — ela **não** é re-exportada por `rbac/__init__.py`; as views a importam pelo shim `apps/core/permissions.py`.
- [`v2/backend/apps/core/rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) — Capability Policy Layer: matriz `ACCESS_POLICIES` (policy key → frozenset de capabilities elegíveis, semântica OR), **22 classes `Can*`**, `PUBLIC_POLICY_KEYS`, e os SSOT `user_has_policy` / `resolve_public_policies`. Também hospeda os helpers de delegação `user_can_delegate_availability_block` e `user_can_delegate_deslocamento`.
- [`v2/backend/apps/core/rbac/matrix.py`](../../../backend/apps/core/rbac/matrix.py) — Matriz Viva `ACCESS_MATRIX` (10 atores × recursos discriminantes → status HTTP esperado) para testes parametrizados.
- [`v2/backend/apps/core/rbac/helpers.py`](../../../backend/apps/core/rbac/helpers.py) — `user_has_any_perm`, `user_is_assistente_administrativo_controle`, `user_has_all_perms`. Os helpers de **delegação** vivem em `policies.py`, não aqui.
- [`v2/backend/apps/core/rbac/constants.py`](../../../backend/apps/core/rbac/constants.py) — constantes de **data scope** (`COORDENADOR_ROLE_GROUPS`, `FORMADOR_ROLE_GROUPS`) — usadas para filtrar queryset, não para autorizar.
- [`v2/backend/apps/core/constants.py`](../../../backend/apps/core/constants.py) — `SETOR_GROUPS` (13 setores), `FUNCAO_GROUPS` (5 funções), `ALLOWED_USER_GROUPS`, `RESERVED_GROUPS`.
- [`v2/backend/apps/core/services/rbac_permissions.py`](../../../backend/apps/core/services/rbac_permissions.py) — `get_user_functional_permissions` (resolução cache-aware das capabilities do usuário) + helpers de invalidação por usuário/grupo.
- [`v2/backend/apps/core/services/functional_permissions_seed.py`](../../../backend/apps/core/services/functional_permissions_seed.py) — `FUNCTIONAL_PERMISSIONS_SEED`: SSOT dos codenames, labels, categorias e grupos default de cada capability.
- [`v2/backend/apps/core/views/me.py`](../../../backend/apps/core/views/me.py) — `MePoliciesView` (`GET /api/me/policies/`).
- [`v2/backend/apps/core/signals.py`](../../../backend/apps/core/signals.py) — signal `m2m_changed` em `PermissaoFuncional.groups`: faz **cache-bust** dos usuários afetados. A auditoria de Grupo×Capability **não** passa mais por este signal — o buffer de módulo `_PENDING_GROUP_CAP_DELTAS` / `flush_group_capability_audit` foi removido no #1672 e o `AuditLog GROUP_CAPABILITY_CHANGED` agora é gravado no ponto de escrita — ver D17 abaixo.
- [`v2/backend/scripts/rbac_lint.py`](../../../backend/scripts/rbac_lint.py) — lint AST (V001/V002/V003) que enforça a convenção em CI.

Doc canônico detalhado (não duplicado aqui): convenção de nomes em [`RBAC_NAMING.md`](../../RBAC_NAMING.md), matriz declarativa ator × recurso em [`rbac_authorization_matrix.md`](../../rbac_authorization_matrix.md), e operação via Admin em [`GUIA_ADMIN_RBAC.md`](../../GUIA_ADMIN_RBAC.md).

## Contratos e invariantes

- **Idioma canônico**: `permission_classes = [IsAuthenticated, HasPerm("codename")]`. Composition por instância: `HasPerm("a") | HasPerm("b")` (OR), `&` (AND), `~` (NOT). Para OR semântico recorrente (≥3 caps ou compartilhado entre views) usa-se uma Policy `Can*`.
- **Grupos diretos são banidos**: `user.groups.filter(name=...)` em `apps/core/views*` ou `apps/core/services/` é violação **V001** do lint. Usos legítimos (composite, block, data-scope) exigem marcador `# noqa: RBAC-<tipo>-allowed` na linha. Classes `class Is<Word>(...)` fora da whitelist (`IsGerenteSuperintendencia`, `IsOwnerOrPrivileged`) são violação **V002**. Mutação de `PermissaoFuncional.groups` / `Group.permissions` em migration de `apps/core/` acima do cutoff D17 (número > 82) é violação **V003**. CI job `[required] backend rbac-lint`.
- **Codename é capacidade, não identidade**: formato `verb_noun[_qualifier]` snake_case inglês. Proibido nome de setor/função/grupo. Exceções bundle conscientes: `manage_admin_registries`, `manage_purchases_and_materials`.
- **Superuser sempre bypassa**: toda classe e helper retorna `True` para `is_superuser` antes de qualquer checagem.
- **Fail-secure**: usuário anônimo/`None` → `False`; policy key ausente da matriz → `False`; capability sem grupos no seed → só superuser passa (feature em incubação).
- **D17 — Admin-driven Group × Capability**: a atribuição grupo↔capability migra para o Django Admin superuser-only (`PermissaoFuncionalAdmin`). Codename/label/category/existência da capability são read-only (SSOT no seed); só `groups` é editável. Toda edição invalida cache (signal `m2m_changed`).
  - ✅ **Auditoria de Grupo×Capability invariante — RESOLVIDO no #1672** (antigo achado `M05-05`, épico #1657, CLOSED). Antes do #1672, o único chamador de `flush_group_capability_audit()` era `PermissaoFuncionalAdmin.save_related()` (em `admin.py`): **nenhuma view DRF drenava o buffer**, então um `PATCH /api/grupos/{id}/` alterava a matriz Grupo×Capability, disparava o signal e invalidava o cache, mas o delta ficava no buffer de módulo `_PENDING_GROUP_CAP_DELTAS` (então em `signals.py`) **sem nunca ser gravado** (zero AuditLog) — e, por ser um `dict` de módulo e não um thread-local, o lixo era drenado pelo **próximo** `save_related` do Admin e **atribuído ao ator errado**. O #1672 removeu o buffer e o flush: a auditoria agora é gravada **no ponto de escrita** — Admin em `PermissaoFuncionalAdmin.save_related` (`admin.py`), REST em `GroupSerializer.create` / `GroupSerializer.update` (`serializers/usuario.py`) via `auditar_group_capabilities_set` — com PII redigida em `_PII_KEYS_TO_MASK` / `_redact_details` (`redact_cpf`) em `serializers/auditoria.py`. Ambos os caminhos auditam.
- **Policy key = contrato externo estável** (uma vez em `PUBLIC_POLICY_KEYS`): adicionar key é compatível; renomear/remover é breaking (deprecation de 2 releases); mudar capabilities elegíveis (`ACCESS_POLICIES[k]`) é compatível (frontend não depende). O endpoint nunca vaza capability codenames.
- **SSOT da semântica de policy**: `user_has_policy(user, key)` é a fonte única; `_PolicyPermission.has_permission`, os testes e `resolve_public_policies` delegam para ele. Mudar avaliação = mudar num só lugar.
- ✅ **Revogação imediata ao excluir um Group — RESOLVIDO no #1791** (antigo achado `M05-03`, épico #1667, CLOSED). Antes do #1791, o cache funcional (TTL de **300 s**, `CACHE_TTL_SECONDS` em `services/rbac_permissions.py`) mantinha as capabilities revogadas por até 5 minutos após `DELETE /api/grupos/{id}/`: o único invalidador era o `post_delete` em `Group` (`_invalidate_funcperm_on_group_change` em `rbac_signals.py`), que resolve os usuários impactados **consultando o M2M** — mas em `post_delete` as linhas de `auth_user_groups` já foram removidas em cascata, a query volta vazia e nenhuma chave por-usuário é apagada. O #1791 (`01ddb4cd`) adicionou `_invalidate_funcperm_on_group_delete_members` (`@receiver(pre_delete, sender=Group)` em `rbac_signals.py`), que faz o **snapshot dos membros ANTES do cascade** (mesmo padrão do `pre_clear` de `_invalidate_funcperm_on_user_groups_change`) e invalida o cache por-usuário de forma **síncrona** via `invalidate_users_functional_permissions_cache` — os ex-membros perdem as capabilities revogadas na hora, sem esperar o TTL. Prova comportamental em `test_cache_invalidated_when_group_deleted` (`test_rbac_functional_permissions.py`).
- **Aprovação de solicitações (CP-02, PA-02)**: gate composite `CanAccessSolicitationApprovals`, SSOT `solicitation_approval_basis(user)` em `policies.py` (`_user_has_solicitation_approvals` = `basis is not None`). Bases, em ordem: `superuser`; `gerente_superintendencia` — vínculo `EquipeGerencia` **vigente** com papel `GERENTE` na gerência `Gerencia.nome == GERENCIA_APROVADORA_NOME` (`"SUPERINTENDENCIA"`, `helpers.user_is_gerente_superintendencia`; sem grupo, sem checar `Gerencia.ativo`; PR B1); `asst_admin_controle` — Setor `Controle` + Função `Assistente Administrativo`; `grupo_superintendencia_gerente` — composite legado Setor `Superintendência` + Função `Gerente` (sai no B2). Autoridade que não é capability: `is_superintendencia` (`/api/me/`) **não** muda com o vínculo (abriria todos os setores para quem é só COORDENADOR/FORMADOR de g1). A chave `nome` é protegida por `GerenciaSerializer.validate_nome`; os importers de equipe não criam nem reativam o vínculo aprovador; o formulário de usuário audita a concessão/revogação (`details.autoridade_aprovacao`). A policy também libera o `preview-gcal` (leitura), não o `publish`. **Escopo por objeto** (regra do dono, 30/09): a base `gerente_superintendencia` vê tudo, mas decide, edita, exclui e cria só solicitação de projeto do fluxo SUPER da `SUPERINTENDENCIA` — predicado `projeto_no_escopo_da_superintendencia` (fail-closed) e `ESCOPO_SUPERINTENDENCIA_Q`/`ESCOPO_SUPERINTENDENCIA_PROJETO_Q` (o mesmo em SQL); `aprovadora_restrita_a_superintendencia(user)` = a única base de aprovação é o vínculo (superuser, par Controle e par legado não são restringidos); `solicitation_approval_basis_for(user, solicitacao)` = a base que vale para aquela solicitação (vai para o AuditLog). Para editar/excluir/criar, `restrita_ao_escopo_da_superintendencia` (em `services/solicitacao_scope.py`) também solta quem é global por capability (`operate_preagenda`, `manage_admin_registries`, `approve_solicitation`); e um 2º vínculo vigente de `GERENTE` dela em outra gerência (`_PAPEIS_DE_GESTAO`; `COORDENADOR`, `APOIO` e `FORMADOR` não) abre criar/editar/excluir/mover naquela gerência, não decidir. Detalhe em [`solicitacao-approval.spec.md`](./solicitacao-approval.spec.md) e [`politica-aprovacao.spec.md`](../domain/politica-aprovacao.spec.md).
- **Formulário de Usuários (superuser): o salvar mexe só no que o formulário mudou (#2071, 2026-09-29)**. O form edita as FUNÇÕES e UMA gerência (a primeira vigente por id, `_vinculo_exibido` em `serializers/usuario.py`). `group_ids` substitui só os grupos de função (`nomes_grupos_funcao()` em `services/rbac_service.py`: `FUNCAO_GROUPS` + os classificados como função, a mesma lista do `/api/rbac/meta/`); grupos de setor e de permissão funcional ficam (antes, `groups.set` apagava o Controle da pessoa que aprova pela base `asst_admin_controle`). O grupo de setor derivado da gerência (`setor_group_for`) entra e sai só quando a gerência muda ou na primeira lotação, e **setor que compõe par aprovador (`APPROVER_COMPOSITES`: Superintendência, Controle) não é derivado** — antes, salvar qualquer pessoa de g1 dava o grupo `Superintendência` (todos os setores). A lotação só é re-sincronizada quando a gerência ou os **papéis** mudam; aí o form é a fonte (`sync_user_lotacao` encerra os outros vínculos). Tirar todas as funções com papel (com ou sem gerência) chama `encerrar_lotacao`; e o vínculo GERENTE na gerência aprovadora exige a função Gerente (`encerrar_gerente_aprovador` quando ela não está no salvar) — ambos revogam a aprovação. **Trava:** se o salvar formar o par LEGADO `Superintendência` + `Gerente` (ou fizer dele a base efetiva) com o grupo `Superintendência` preservado e oculto (não veio no pedido), o `update` (atômico) responde 400 e nada é gravado; o par Controle + Assistente Administrativo é base legítima e fica fora da trava. Limites conhecidos: uma mudança deliberada de lotação encerra vínculos de outras gerências que o form não mostra; quem não tem função com papel e troca de gerência acumula o grupo de setor antigo; tirar Gerente pela tela de Grupos (`sync-members`) ou por `assign_groups` só revoga no próximo salvar do form. A action `assign_groups` continua substituindo todos os grupos.

## API / Interface

**Classes DRF** (import via `from apps.core.rbac import ...`):

- `HasPerm("codename")` — checa uma capability; aceita prefixo `core.` opcional. Suporta `| & ~`.
- `HasSectorAccess` — scope dinâmico por `gerencia_id` (query/kwargs); sem `gerencia_id` exige vínculo **vigente** em `EquipeGerencia`. Vigência = kill-switch `ativo` **E** hoje dentro da janela `[valid_from, valid_to]` (Fortaleza, RD-06), via a SSOT `EquipeGerencia.vigentes_em()` (classmethod → `QuerySet`) — reaplicada nos ~14 read-sites de scope (permissions/availability/options/deslocamento/stats/solicitacao_scope); fecha o gap onde um ex-membro expirado ainda passava o gate (`HasSectorAccess.has_permission` em `permissions.py`). Idiomático: `[IsAuthenticated, CanViewAllAvailability | HasSectorAccess]`.
- `IsGerenteSuperintendencia` — composite funcperm `approve_solicitation_batch` + grupo `Gerente`.
- `IsOwnerOrPrivileged` — object-level: superuser, dono (`obj.usuario == user`) ou quem tem a cap de edição **dentro do escopo** (`user_can_access_solicitacao`: global, ou gestor da gerência). A aprovadora por vínculo é global para ver, mas só edita/exclui o fluxo SUPER da `SUPERINTENDENCIA`, as gerências de um 2º vínculo de `GERENTE` dela e as próprias; fora disso o 403 diz "A gerência da Superintendência só edita ou exclui solicitações do fluxo SUPER da Superintendência.".
- `IsAssistenteAdministrativoControle` — composite Setor `Controle` + Função `Assistente Administrativo`.
- `SuperuserOnly` — só `is_superuser`. Gate de escrita do `GroupViewSet` e do `assign_groups` e, desde 02/10/2026 (decisão do dono), das 13 rotas de importação pela tela (12 endpoints + 1 alias): nenhuma capability importa planilha (ver [imports.spec](./imports.spec.md)).
- 22 classes `Can*` (`CanAccessAuditLogs`, `CanViewComprasDashboard`, `CanViewAllAvailability`, `CanAccessSolicitationApprovals`, `CanUseGcal`, `CanManageInternalActions`, ...) mapeadas em `ACCESS_POLICIES` — lista completa em `policies.py` (de `CanAccessAuditLogs` a `CanAccessSolicitationApprovals`). `CanPublishSetorSolicitacao` (policy `publish_setor_solicitacao`, grupo Apoio de Coordenação, #2043) entra em OR com `CanUseGcal` nas 4 ações GCal por solicitação e nos 4 endpoints OAuth da própria credencial (`start`, `callback`, `status`, `disconnect`; #1656) — 8 sites com o mesmo OR, cuja consolidação numa policy nomeada é follow-up. `calendars`, `select-calendar` e `events` seguem só `CanUseGcal`. O recorte real é por objeto em `can_publish_solicitacao` (`services/solicitacao_scope.py`): global = `use_gcal`, senão `Projeto.setor` ∈ `user_setores`; a lista `?publishable=true` usa a mesma regra (`_publish_tier`).

**Helpers** (não-DRF): `user_has_any_perm(user, *codenames)`, `user_has_all_perms(...)`, `user_has_policy(user, key)`, `user_is_assistente_administrativo_controle(user)`, `user_can_delegate_availability_block(user)`.

**Endpoint**: `GET /api/me/policies/` (`IsAuthenticated`) → array JSON ordenado das `PUBLIC_POLICY_KEYS` que o usuário possui (subset de `ACCESS_POLICIES`). Anonymous → 401; superuser → todas as públicas; regular → subset (OR). Consumido pelo frontend para menu condicional/redirects.

**Setores (13)** e **Funções (5)**: SSOT em `SETOR_GROUPS` / `FUNCAO_GROUPS` (`apps/core/constants.py`). Funções: Formador, Coordenador, Apoio de Coordenação, Gerente, Assistente Administrativo.

## Fluxos principais

1. **Checagem em request DRF**: DRF instancia a classe → `has_permission` rejeita não-autenticado, libera superuser, e consulta `get_user_functional_permissions(user)` (cache Redis, TTL) testando `codename in perms`. Composition `A | B` é resolvida pelas classes `OR/AND/NOT` do DRF (habilitadas em instâncias pelo monkey-patch).
2. **Resolução de policy**: `user_has_policy(user, key)` → anônimo `False` → superuser `True` → composite key delega a helper dedicado (ex: `_user_has_solicitation_approvals`, que lê `solicitation_approval_basis` — inclui uma query EXISTS de vínculo) → caso geral `user_has_any_perm(user, *ACCESS_POLICIES[key])`.
3. **Mudança de atribuição**: editar `PermissaoFuncional.groups` → signal `m2m_changed` consolida as 6 disparadas (pre/post × add/remove/clear) → invalida cache funcional dos usuários afetados (sem restart). A auditoria `GROUP_CAPABILITY_CHANGED` (added/removed/groups_after) é gravada **no ponto de escrita**, não pelo signal: via Admin em `PermissaoFuncionalAdmin.save_related` (`admin.py`), via REST (`PATCH /api/grupos/{id}/`) em `GroupSerializer.create` e `GroupSerializer.update` (`serializers/usuario.py`), ambos chamando `auditar_group_capabilities_set` (#1672). Os dois caminhos auditam — o gap antigo (AuditLog só pelo Admin) foi fechado.
4. **Erros relevantes**: capability sem grupo no seed → 403 a todos exceto superuser; `gerencia_id` não-inteiro em `HasSectorAccess` → 403 com a mensagem `"gerencia_id deve ser um número inteiro."` (`HasSectorAccess.has_permission` em `permissions.py`); Controle puro tentando aprovar (sem Função `Assistente Administrativo`) → 403.

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

- **Cutoff D17 hardcoded** (`D17_LEGACY_MIGRATIONS_MAX = 82`): migrations futuras que precisem backfill legítimo de grupos exigem `# noqa: RBAC-migration-allowed` consciente.
- **Composition OR em instâncias depende de monkey-patch** (`permissions.OR/AND/NOT.__call__ = lambda self: self`) aplicado em `permissions.py`; `policies.py` força o import por side-effect. Remover o patch quebra silenciosamente todo `permission_classes = [A | B]`.
- **`HasSectorAccess` é o único ponto com TOCTOU residual** de scope: a checagem de vínculo **vigente** em `EquipeGerencia` (`vigentes_em()`) e a leitura de dados acontecem em requests separados; mudança de vínculo entre eles não é transacional (aceitável para o caso de uso atual).
- ✅ **Schema OpenAPI de `/api/me/policies/` — RESOLVIDO no #1463**. A `MePoliciesView` (`views/me.py`) declara `responses={200: ListSerializer(child=CharField())}` — um array de strings — que bate com o retorno real (`MePoliciesView.get` devolve o array bruto via `resolve_public_policies`). A divergência antiga de schema (declarava `{policies: [...]}` via `inline_serializer` mas retornava array bruto) foi fechada.
- **Escopo ator×alvo é a dívida estrutural do módulo** (épico #1656). O idioma `HasPerm(codename)` responde "esta pessoa pode executar esta ação?", nunca "sobre QUEM ela pode executar". Onde o alvo importa — administração de usuários (`M07-02`), solicitações de outra gerência (`M10-01`), `HasSectorAccess` na Grade Mensal (`M14-01`) — a checagem de alvo precisa ser feita no queryset/serializer da view, e hoje falta em vários pontos. Ao criar uma capability nova, decidir explicitamente se ela precisa de escopo e onde ele é aplicado.
- **`SuperuserOnly` fora da superfície pública**: não está em `rbac/__init__.py`; importar via `apps.core.permissions`. Se for promovida ao `__init__`, atualizar esta spec e o `__all__` juntos.
