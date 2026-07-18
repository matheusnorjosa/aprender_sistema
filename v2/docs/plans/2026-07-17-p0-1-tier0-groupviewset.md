# P0-1 — Erradicação Tier-0 do GroupViewSet (matriz Grupo×Capability + memberships)

Status: **Planejado — D-1 ratificada (2a)**. Parte 2 da correção definitiva Tier-0 (após P0-0, no ar em prod `v2026.07.17-86afdef`).
Origem: auditoria `v2/docs/audits/2026-07-17-rbac-security-audit.md` (§4.2) + investigação fan-out (5 agentes, 2026-07-17).
Plano-mãe: `v2/docs/plans/2026-07-17-rbac-correcao-definitiva.md` (Wave 2).
Princípio: TDD (RED prova o comportamento **seguro** ausente). Não é paliativo — a fronteira é permanente.

---

## 1. Vetor P0-1 — superfícies de escalada (não-superuser: DAT/Controle)

Mecanismo-raiz: `HasPerm` resolve caps via `PermissaoFuncional.objects.filter(groups__user__id=...)` (`services/rbac_permissions.py:81-83`) — **ligar uma PermissaoFuncional a um grupo concede o codename a TODOS os membros**.

| # | Superfície | file:linha | Escalada |
|---|---|---|---|
| A | Editar matriz via `permissao_funcional_ids` | campo `serializers/usuario.py:347-354`; write `usuario.py:428-429`; gate `views/admin.py:487` (`manage_purchases_and_materials`) | PATCH no próprio grupo + `manage_admin_registries`/`approve_solicitation` → superuser-equivalente por capability |
| B1 | `sync_members` | `views/admin.py:503-574` (**sem** self/privileged/whitelist) | adiciona a própria conta em `Superintendência`+`Gerente` → autoridade de aprovação (fura o self-block do assign_groups) |
| B2 | `assign_groups` | `views/admin.py:399-469` (whitelist inclui grupos privilegiados) | atribui outra conta a grupo privilegiado → cunha aprovador |
| B3 | `group_ids` (create/update usuário) | `serializers/usuario.py:94-101`, set em `:258/:275`; gate `admin.py:363` | mesma whitelist ampla no fluxo cadastral |
| C | Criar/renomear/excluir grupo | create `usuario.py:341-354,412-420`; rename `:399-410`; delete `admin.py:494-501` | `?confirm_reserved=true` é **UX, não autorização**; editar caps de grupo reservado sem guard |
| D | Reset de senha de não-superuser | `serializers/usuario.py:253/270` (`set_password`) | resetar senha de aprovador (Super+Gerente) → login como ele |

Fronteira residual pós-P0-0: só o bit `is_superuser` (404 em alvos superuser). **Não** contém alcance de capability/aprovação/takeover — por isso o P0-1.

Gap de gate CI: a Living Matrix (`rbac/matrix.py`) é GET-only e não cobre `/api/grupos/`, `assign_groups`, `sync-members` → regressão que amplie a write-surface não dispara o gate da matriz.

---

## 2. Decisões

- **D-1 — escopo (RATIFICADA: 2a, bloqueio total).** Memberships (User→Group) e matriz (Grupo×Capability) → **superuser-only**. DAT mantém CRUD de conta comum (criar, senha, cadastral, ativar/desativar); **não atribui mais grupos**. Fronteira sem classificação para errar. Corrobora o histórico (§audit 2.5): os 13 `SYNC_GROUP_MEMBERS` foram todos do superuser `admin`.
- **D-2 — matriz (decidida por D17).** Grupo×Capability só no Django Admin superuser-only (`admin_site.py:42`). Remover `permissao_funcional_ids` do REST = ganho puro. *Nuance:* D17 fala só de Grupo×Capability; puxar memberships p/ superuser-only é restrição NOVA da Wave 2 (agora ratificada em D-1).
- **D-3 — continuidade operacional (OPEN, operacional).** Runbook: superuser primário+backup faz o group-assign no cadastro; SLA de revogação; break-glass/anti-lockout. Delegação futura = RFC com separação de deveres. **Proibido** criar `manage_rbac` (circular).

---

## 3. Sequência de co-deploy

**Frontend ANTES do backend** (`usuario_form_helpers.ts:68` injeta `group_ids` em TODO save; `GruposPage.tsx:291-324` chama `syncGroupMembers` após create/update → escrita parcial). Se o backend 403-ar primeiro, DAT editando só telefone trava a tela inteira.

### PR-A — frontend read-only para não-superuser (primeiro)
Condicionar por `is_superuser` (`UsuariosPage` já tem `currentIsSuperuser`; `GruposPage` busca via `usePermissions`/checkAuth):
1. `usuario_form_helpers.ts:68` — **omitir `group_ids`** quando editor não-superuser (destrava edição trivial).
2. `UsuariosPage.tsx` — Selects `setor_ids`/`funcao_ids` read-only + remover `required` p/ não-superuser (mantém criar/senha/cadastral/ativar).
3. `GruposPage.tsx` — desabilitar Salvar do modal (matriz `permissao_funcional_ids` + `member_ids`) e Novo/Editar/Excluir p/ não-superuser. Principal superfície.
4. `SetoresPage.tsx`/`FuncoesPage.tsx` — herdam de GruposPage → read-only.
5. `adminDAT.ts::assignGroups` — **código morto** (só o teste chama) → remover.
Manter leitura: `getRBACMeta`, `listPermissoesFuncionais`, `listGroups/getGroup/listUsers` (populam Selects/labels no modo read-only).

### PR-B — backend gate (2a) + bundlados (segundo)
- remover `permissao_funcional_ids` do write REST (`serializers/usuario.py:347-354`);
- `assign_groups`/`sync_members`/`group_ids` → **superuser-only** (não-superuser: 403 nas ações de membership; `group_ids` ignorado/rejeitado no serializer);
- rename/delete de grupo reservado + GroupViewSet CRUD → superuser-only (não confiar em `?confirm_reserved`);
- **P1-3** (cache reverse) + **P2-2** (serviço de auditoria) no mesmo PR (§5).

---

## 4. Risco G3 — o que o DAT perde (2a) e mitigação

**Perde:** o passo de group-assignment do onboarding (colocar novo usuário em setor+função). **Mantém:** criar conta, senha, cadastral, ativar/desativar (a conta é criada; só o link a grupo se move ao superuser).
**Mitigação:** runbook D-3 (superuser faz o group-assign no cadastro, Django Admin ou endpoint superuser-gated). Baixo atrito real — membership já é atividade de superuser na prática (audit §2.5).

---

## 5. Itens bundlados no PR-B

**(A) P1-3 — cache reverse.** `rbac_signals.py:26-36` assume `instance=User`; `sync_members` (`admin.py:550` `group.user_set.set`) dispara `m2m_changed` com `instance=Group, reverse=True, pk_set={user_ids}` → invalida a chave errada (`as2:funcperms:{v}:{group_id}`), chaves reais dos usuários persistem → revogação stale ≤300s. **Fix:** ramificar por `reverse` (forward→`instance.id`; reverse→`pk_set` em post_add/remove + snapshot pre_clear→post_clear) via helper existente `invalidate_users_functional_permissions_cache`.

**(B) P2-2 — auditoria.** Buffer global `_PENDING_GROUP_CAP_DELTAS` (`signals.py:46`, cross-thread sem lock) mal-atribui/perde deltas em ops concorrentes. Lacunas (grep=zero AuditLog): DELETE de usuário, `assign_groups`, CRUD REST de grupos, reset de senha admin (janela de takeover invisível), import de usuários. **Fix:** serviço ÚNICO de auditoria transacional (ator + before/after, `transaction.on_commit`) — elimina o buffer de módulo; modelo = o `SYNC_GROUP_MEMBERS` que já emite dentro de atomic (`admin.py:552`).

---

## 6. Testes que travam o comportamento inseguro (reescrever RED→GREEN)

Backend (ficam RED após o fix — reescrever com o alvo seguro = não-superuser 403 / campo removido):
- `test_admin_api.py::test_dat_can_patch_group_permissoes_funcionais:732` (A) · `..._create_group_as_funcao:698`/`..._rejects_invalid_group_type:719` (C) · `..._rename/delete_reserved_group_requires_confirmation:761/771` (C→guard real).
- `test_group_sync_members.py::test_dat_can_sync_group_members:69` + `..._replaces_existing:83` + `..._requires_dat_permission:127` (B1) — **+ casos negativos novos**.
- `test_assign_groups.py::*` (B2 — a whitelist inclui privilegiados; ator DAT vira RED).
- `test_rbac_service_whitelist.py` (semântica da whitelist).
- `test_rbac_superuser_target_protection.py::TestDatStillManagesCommonUsers::test_dat_can_still_reset_common_user_password` — **mantém** o reset, mas agora **assertar AuditLog** (P2-2).

Frontend (forma do payload): `UsuariosPage.cpf.test.tsx:48,133-141` (group_ids condicional a superuser) · `adminDAT.test.ts:107,...` (remover assert de `assignGroups` morto; demais seguem a nova write-surface).

Bundlados: **adicionar** teste RED→GREEN da invalidação reversa (P1-3); reescrever `test_pr16_admin_group_capability.py` + `conftest.py:54-56` p/ o serviço transacional (remover reset manual do global); novos asserts de AuditLog em assign_groups/delete/reset.

Fronteira que **não** muda: `test_admin_api.py::test_dat_cannot_patch_is_superuser:550` e toda a suíte `test_rbac_superuser_target_protection.py` (P0-0).

---

## 7. Gates (por PR)

PR-A (frontend): `cd v2/frontend && npm test -- --run <alvo> && npm run typecheck && npm run lint && npm run build && npm run test:checklist`.
PR-B (backend): `pytest <alvo> --no-migrations` + `scripts/rbac_lint.py` + `pyright` + (se migration) `makemigrations --check`.
Ambos antes de Ready: `staging-gate.sh` (8/8 + 3 marcadores). Pós-código: `graphify update .`.
