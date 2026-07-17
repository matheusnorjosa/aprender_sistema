# Auditoria de Segurança RBAC — 2026-07-17

Status: **P0 CONFIRMADOS VIVOS EM PRODUÇÃO** — remediação não iniciada
Base: `main` (auditoria refeita sobre `e80a61d2`; verificação de prod sobre a stack viva)
Método: leitura de código + migrations + specs + testes + **verificação read-only na VM01 de produção**
Plano de correção definitiva: `v2/docs/plans/2026-07-17-rbac-correcao-definitiva.md`
Escopo: nenhum arquivo de aplicação alterado nesta auditoria.

---

## 1. Resumo executivo

A arquitetura RBAC (Usuário → Grupos setor/função → PermissaoFuncional → Policy/HasPerm → View/Service → EquipeGerencia) é **bem desenhada**: capability, scope e policy são camadas ortogonais e `HasPerm` falha fechado. O risco **não** está no `HasPerm`, e sim em cinco padrões:

1. capability operacional abre o plano administrativo de identidades/privilégios (Tier-0);
2. capability de ação é tratada como autorização global sobre todas as linhas;
3. vínculos organizacionais inativos ou de papel incorreto continuam ampliando acesso;
4. o frontend duplica a matriz por nome de grupo;
5. seed/cache/auditoria não preservam corretamente revogação e autoria.

**Três P0 confirmados VIVOS em produção**, além de P1 de scope/revogação/cache/integridade da matriz e P2 de manutenção. **Não declarar o RBAC seguro para produção sem fechar os P0.** Há takeover de superuser explorável em **uma requisição**.

| ID | Prioridade | Situação | Resultado |
|---|---|---|---|
| **P0-0** | Crítica | **Confirmado vivo** | DAT redefine a senha de um superuser e toma a conta |
| **P0-1** | Crítica | **Confirmado vivo** | DAT/Controle/Assistente alteram capabilities e memberships de grupos |
| **P0-2** | Crítica | **Confirmado vivo** | Gerente lê/edita/exclui solicitações cross-gerência |
| A-01 | Decisão bloqueante | Aberta | Scope de aprovação do Gerente da Superintendência |
| A-02 | Decisão + schema | Aberta | Scope do Assistente Administrativo do Controle |
| P1-1 | Alta | Confirmado | Grade Mensal aceita papel indevido/inativo e vaza no caso misto |
| P1-2 | Alta | Confirmado | Consulta de disponibilidade aceita qualquer alvo para quem tem a cap |
| P1-3 | Alta | Confirmado | Revogação por relação reversa (`sync_members`) fica stale ≤300s |
| P1-4 | Alta | Confirmado | Service worker cacheia identidade/policies/config |
| P1-5 | Alta | Confirmado | Seed comum apaga atribuições administradas da matriz |
| P1-6 | Alta | Confirmado | Config do sistema usa capabilities sem relação semântica |
| P2-1 | Média | Confirmado | Frontend replica regras por setor e diverge do backend |
| P2-2 | Média | Confirmado | Auditoria incompleta + buffer global concorrente |
| P2-3 | Média | Confirmado | Módulos duplicados, permission morta, docs divergentes |

---

## 2. Verificação em produção (VM01, read-only) — o que confirma que os P0 estão vivos

Executado no console da VM01 via `docker exec` no container `aprender_prod-web-1` (Django shell + `grep` no código deployado) e `nginx_proxy_manager-app-1` (logs). **Somente leitura** — nenhuma escrita, migration, seed ou restart.

### 2.1 A matriz está semeada em produção
```
PF_COUNT = 16          (PermissaoFuncional)
migrations de seed aplicadas: 0065, 0075, 0076, 0077, 0080 (todas)
SUPERUSERS: 1 / 1 ativo   (username: admin)
```
Matriz efetiva (grupo → capabilities), pontos críticos:
- **DAT**: `import_spreadsheet`, `manage_admin_registries`, `manage_purchases_and_materials`, `view_all_availability`
- **Controle**: `manage_purchases_and_materials`, `operate_preagenda`, `run_daily_operations`, `view_all_availability`
- **Assistente Administrativo**: `manage_purchases_and_materials`, `operate_preagenda`, `run_daily_operations`
- **Gerente**: `approve_solicitation_batch`, `create_solicitation`, `edit_solicitation_as_owner_or_privileged`
- **Superintendência**: `approve_solicitation`, `approve_solicitation_batch`, `execute_restricted_operations`
- **Coordenador / Apoio de Coordenação**: `create_solicitation`, `edit_solicitation_as_owner_or_privileged`
- Setores pedagógicos, `Gestor Tecnologico`, `Programador`: `[]`

### 2.2 Contas ativas por capability perigosa (quem explora HOJE)
| Capability | Contas ativas | P0 relacionado |
|---|---|---|
| `manage_admin_registries` | **3** | P0-0 (takeover de superuser) |
| `manage_purchases_and_materials` | **4** | P0-1 (GroupViewSet) |
| `approve_solicitation_batch` | **9** | P0-2 (queryset global de solicitações) |
| `edit_solicitation_as_owner_or_privileged` | **51** | P0-2 (cap de edição insegura) |
| `view_all_availability` | **4** | scope de disponibilidade |

### 2.3 Código vulnerável está deployado (grep no container de prod)
- `apps/core/serializers/usuario.py:257` — `user.set_password(password)` no `update()`, **sem guard de alvo superuser**.
- `apps/core/serializers/usuario.py:334` — `permissao_funcional_ids` gravável (`write_only`, `source="permissoes_funcionais"`).
- `apps/core/views/admin.py:360` — `queryset = Usuario.objects...all()` sob `HasPerm("manage_admin_registries")` (363).
- `apps/core/views/admin.py:468` — bypass `confirm_reserved` no `perform_destroy` de grupos.
- `GIT_COMMIT_SHA` não está setado no env do container (commit exato não capturado; estado do código confirmado por grep).

### 2.4 Divergência matriz × seed (prova de uso do plano administrativo)
O grupo **"Assistente Administrativo" tem 3 capabilities**, mas a migration `0077` **não** atribui nada a ele (o grupo só foi criado depois, na `0081`, sem caps). Logo, essas caps foram atribuídas **pós-migração via admin/API** — e isso **não aparece no AuditLog**. Confirma que o caminho de administração da matriz (P0-1) é usado ativamente, não é hipotético. (Também dá `manage_purchases_and_materials` ao Assistente → 4ª conta do P0-1.)

### 2.5 Trilha de auditoria é cega nas mutações críticas
AuditLog (273 registros) só tem: LOGIN/LOGOUT/GOOGLE_*/ACOES_NOTIFICACOES_DAILY/LOGIN_FAILED(17)/**SYNC_GROUP_MEMBERS(13)**. **Não existe ação de auditoria para reset de senha, update/criação de usuário nem concessão de capability.** Os 13 `SYNC_GROUP_MEMBERS` são todos do ator `admin`, em mar–abr/2026 (setup), nada recente, nada por não-superuser. Logs do Nginx Proxy Manager (retenção curta) não mostram mutação nos endpoints admin.

**Conclusão da revisão de incidente**: **nenhum indício de abuso encontrado**, mas a trilha é cega exatamente onde ocorrem as mutações críticas + retenção de log curta → **não é possível confirmar nem descartar exploração passada**. A cegueira da auditoria é, ela mesma, um achado (governança).

---

## 3. Cadeia de ativação da matriz (por que os P0 estão vivos)

As migrations semeiam e atribuem a matriz automaticamente, e o deploy versionado roda `migrate`:
- `0065_seed_permissoes_funcionais.py:143-152` cria 14 `PermissaoFuncional` + `groups.set()`.
- `0075_dual_write_verb_noun_codenames.py:56-67` cria os codenames verb_noun copiando os vínculos.
- `0076` remove os codenames antigos `pode_*`.
- `0077_realign_funcperm_groups.py:29-69` realinha (`groups.set()`): `manage_admin_registries`→DAT; `manage_purchases_and_materials`→DAT/Controle; `approve_solicitation_batch`→Gerente/Superintendência; `edit_solicitation_as_owner_or_privileged`→Gerente/Coord/Apoio.
- `0080_redistribute_view_all_availability.py:49` fixa `view_all_availability` em Controle/DAT.
- Deploy: `docker-compose.prod.yml:47-50` serviço one-shot `migrate`; web/worker/beat dependem de `service_completed_successfully` (106-107/202-203/261-262). Commit `b4f80393` (#1495). **Correção documental aplicada nesta rodada**: `deploy.spec.md` dizia "migrations manuais" — desatualizado; o compose roda migrate automaticamente.

**Anomalia do dev (não do prod)**: o banco dev tem migrations aplicadas até 0082 mas `PF_COUNT=0` — divergência entre o ledger de migrations e os dados (fake/restore/exclusão pós-migração). É **anômalo, não o baseline**. Prod tem `PF_COUNT=16` (verificado em §2.1).

---

## 4. Achados detalhados

### 4.1 P0-0 — Takeover direto de superuser (1 requisição)
**Cadeia**: DAT tem `manage_admin_registries` → `UsuarioAdminViewSet` (`apps/core/views/admin.py:345`) é `ModelViewSet` completo com `queryset = Usuario.objects...all()` (360) e `filterset_fields` incluindo `is_superuser` → o serializer (`apps/core/serializers/usuario.py:154` validate, `249` update) aceita `password` e só protege o **campo** `is_superuser`/auto-demotion/último superuser, **não o alvo que já é superuser** → `update()` chama `set_password()` (257).
**Exploit**: `GET ?is_superuser=true` → `PATCH /api/usuarios-admin/{id}/ {"password":"<senha válida>"}` → autentica como superuser. Existe em `/api/` e `/api/v1/` (`config/urls.py:107-110`).
**Superfícies adicionais**: `DELETE` não passa pela proteção do serializer; `assign_groups` protege só automodificação; import por CPF pode alterar/desativar/adicionar grupos a um superuser (`apps/core/services/usuarios_import.py:285`). Nenhum desses gera AuditLog.
**Verificado em prod**: 3 contas DAT capazes; superuser único `admin`.

### 4.2 P0-1 — Escalada pelo GroupViewSet / plano Tier-0
**Cadeia**: `GroupViewSet` (`apps/core/views/admin.py:444`) é CRUD completo sob `manage_purchases_and_materials` (DAT/Controle/Assistente) → `GroupSerializer.permissao_funcional_ids` gravável (`apps/core/serializers/usuario.py:334`) → `sync-members` substitui todos os membros → grupos reservados excluíveis via `confirm_reserved=true`. A suíte atual consagra o comportamento (testes de DAT alterando caps/memberships).
**Escalada**: PATCH no grupo Controle adicionando `manage_admin_registries` → usa P0-0; ou `sync-members` no grupo DAT incluindo a própria conta.
**D17**: `rbac.spec.md` + `rbac_authorization_matrix.md` (decisão D17) mandam administrar Grupo×Capability **só no Django Admin superuser-only** (`apps/core/admin_site.py:18`). **`manage_rbac` NÃO resolve** — quem edita Grupo×Capability concede qualquer autoridade a si mesmo (circular).

### 4.3 P0-2 — Solicitações cross-gerência
**Cadeia**: `views_solicitacao.py:182` (`get_queryset`) fica global para quem tem `approve_solicitation_batch` (todo Gerente) → update/delete usam `IsOwnerOrPrivileged` (`apps/core/rbac/permissions.py:192`), que **retorna `True` globalmente** na cap `edit_solicitation_as_owner_or_privileged` (Gerente/Coord/Apoio) antes de checar dono.
**Precisão**: exploit **incondicional só do Gerente** (tem a batch cap → queryset global). **Coord/Apoio puros permanecem owner-scoped** (o `get_queryset` os limita → 404 nas de terceiros antes do object-check); viram risco só se acumularem outra cap global.
**Gap adicional**: `projeto` é gravável no serializer → PATCH pode transferir a solicitação para fora do escopo; não há validação de `projeto.gerencia` contra o vínculo do ator na criação.
**Verificado em prod**: 9 contas com queryset global; 51 com a cap de edição.

### 4.4 A-01 / A-02 — Aprovação: gate correto, scope aberto
O gate `CanAccessSolicitationApprovals` (`apps/core/rbac/policies.py:350`) é **group-based** (superuser OU Gerente+Superintendência OU Assistente+Controle) → funciona mesmo com matriz vazia; **não é bypass**. Mas nem o gate nem o service (`apps/core/services/solicitacao_approval.py:288`) têm dimensão de gerência: o lote consulta `Solicitacao.objects` global; o builder de erros distingue "inexistente" de "existente+status" → **enumeração cross-gerência se a aprovação for escopada**. `matrix.py:19` declara que não cobre scope. **Duas decisões abertas e independentes** (Gerente Sup; Assistente Controle). `EquipeGerencia.PAPEL_CHOICES` (`apps/core/models/organizacao.py`) não representa Assistente Administrativo → se escopado, exige schema/modelo de delegação próprio.

### 4.5 P1-1 — Grade Mensal e escopo ativo
`HasSectorAccess` (`apps/core/rbac/permissions.py:220`): **sem `gerencia_id`, qualquer vínculo ativo basta, sem checar papel** → Formador/Diretoria com vínculo entram; **com `gerencia_id`, nem `ativo=True` é exigido**. A view mensal (`views_availability_monthly.py:184`) agrega **todas** as gerências ativas do usuário sem filtrar papel → **caso misto** (Coordenador em A + Formador em B) passa por A mas recebe A+B. Testes atuais só negam Formador/Diretoria **sem** vínculo (`test_availability_monthly_rbac.py:178`).
**Predicado correto**: `ativo=True AND papel ∈ {GERENTE,COORDENADOR,APOIO}` aplicado **na autorização E no data-scope**. `ativo=True` também omitido em bloqueios/gerências (`views_availability.py:75`), deslocamentos (`views_deslocamento.py:147`) e home stats (`stats.py:109`).

### 4.6 P1-2 — Consulta arbitrária de disponibilidade
`can_check_availability_for_others()` (`views_availability.py:50`) libera qualquer alvo para `view_all_availability | create_solicitation | approve_solicitation_batch` (inclui Coord/Apoio/Gerente), sem gerência compartilhada; expõe conflitos/ids de evento/bloqueios; no lote, ID fora do escopo não bloqueia.

### 4.7 P1-3 — Cache de revogação stale ≤300s
`rbac_signals.py:26` assume `instance = User`; mas `sync_members` usa `group.user_set.set()` (reverse), onde `instance = Group` → invalida a chave errada, ignora `pk_set` → autorização revogada fica cacheada até 300s.

### 4.8 P1-4 — Service worker cacheia API autenticada
`sw.js` cacheia `/api/options/`, `/api/me/`, `/api/config/`; matcher `includes()` → `/api/me/policies/` também entra; cache por URL sobrevive à troca de sessão; logout não purga.

### 4.9 P1-5 / P1-6 — Seed destrutiva e config
`functional_permissions_seed.py:202` com `assign_default_groups=False` faz `groups.clear()`; `seed_rbac.py:142` usa esse modo → apaga a matriz administrada (contradiz D17). `views_config.py:62` gate `manage_purchases_and_materials | approve_solicitation` → DAT+Controle+toda Superintendência mudam config.

### 4.10 P2 — Frontend, auditoria, dead code
`usePermissions.ts:73` deriva acesso de setor/função (divergências: Mapa p/ DAT, Dashboard Equipe omite Controle, `canSeeAllSectors` global). Auditoria ausente em senha/delete/assign_groups/import/CRUD REST de grupos/caps; buffer global `_PENDING_GROUP_CAP_DELTAS` (`signals.py:41`) mistura ator entre threads. Duplicata `views/availability.py` (órfã de rota, re-exportada); `IsGerenteSuperintendencia` não checa Superintendência e está sem consumidor.

---

## 5. O que está correto (preservar)
`HasPerm` falha fechado + bypass superuser explícito · policy de aprovação não concede ao Controle inteiro (exige Assistente+Controle) · `/api/me/policies/` expõe policy keys, não codenames · approval usa transação/locks/AuditLog por item · `mine=true` força owner scope · lint proíbe autorização por nome de grupo (salvo composites marcados) · `view_all_availability` literal e global (Controle/DAT) · frontend não é fronteira de segurança · **IDOR e CSRF de Deslocamentos já corrigidos** (#1454 pronto em branch, #1453 em main).

## 6. Correções epistêmicas acumuladas na auditoria
- ❌ "Matriz só ativável por Admin / P0s dormentes" → migrations semeiam no deploy; **prod confirmado com PF_COUNT=16**.
- ❌ "Ambos P0 falham fechados com matriz vazia" → gate de aprovação é group-based, funciona vazio.
- ❌ "Aprovação cross-gerência é intenção fechada" → requisito **aberto** (A-01/A-02).
- ❌ "Gerente/Coord/Apoio exploram edição global imediatamente" → só Gerente incondicional; Coord/Apoio combinatório.
- ❌ "`manage_rbac` resolve" → circular se editar Grupo×Capability.
- ❌ "Grade Mensal estava correta" → papéis indevidos/inativos/misto passam.
- ❌ "Maior escalada era o GroupViewSet" → superado por P0-0 (takeover de superuser em 1 requisição).
- ⚠ "Vivo em prod" (antes presumido) → **agora observado diretamente**. "142 usuários" não foi verificado nesta sessão e não fundamenta decisão.

---

## Anexo A — saídas brutas da verificação de prod (read-only)
```
PF_COUNT = 16
SUPERUSERS total/ativos = 1 / 1   (username: admin, last_login 2026-07-09)
membros ativos: manage_admin_registries=3 | manage_purchases_and_materials=4 |
                approve_solicitation_batch=9 | edit_solicitation_as_owner_or_privileged=51 |
                view_all_availability=4
migrations de seed aplicadas = [0065,0075,0076,0077,0080]
grep código deployado: set_password@257, permissao_funcional_ids@334,
                       queryset Usuario.all()@360 + manage_admin_registries@363,
                       confirm_reserved@468
AuditLog: sem ação de senha/user/capability; SYNC_GROUP_MEMBERS=13 (todos por `admin`, mar-abr/2026)
NPM access log: sem mutação nos endpoints admin (retenção curta → inconclusivo)
```