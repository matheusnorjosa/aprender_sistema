# Plano: Centralização de Importações no Módulo DAT

**Data**: 2026-04-29
**Status**: ✅ **decisões aprovadas** — pronto para iniciar PR-B
**Base**: [`v2/docs/analysis/imports_inventory.md`](../analysis/imports_inventory.md)
**Branch atual**: `main` em `530fbe7`

> **Escopo**: este plano cobre **apenas import em massa/planilha** (upload de CSV/XLSX).
> O fluxo manual de Controle/Assistente Administrativo lançando bloqueio/deslocamento em
> nome de outro usuário é **issue separada** (programa hardening RBAC, PR 13).

## 1. Regra de negócio final

- Todas as importações administrativas/base ficam no módulo DAT
- Rota canônica: **`/dat/importacoes`** (plural)
- Apenas DAT e superuser podem realizar importações (frontend + backend)
- Controle pode usar dados importados, mas **não tem botões nem acesso aos endpoints**
- Compras: dado em Controle, mas importação fica em DAT > Importações
- Registros de Turmas: **fora** desta reorganização
- ASQ-005 async (`/api/imports/bloqueios/`): **fora** — Phase 2 trata
- PR municípios IBGE: **fora** — não tocar pipeline
- RBAC Grade Mensal/Aprovações: **fora**

## 2. Mapeamento (do inventário)

11 importações ativas hoje:

| # | Importação | Endpoint | Hoje em (rota frontend) | Permission backend hoje |
|---|------------|----------|-------------------------|--------------------------|
| 1 | Compras | `POST /api/controle/import-compras/` | `/controle` + `/controle/compras` + `/compras-materiais` + `/dat/compras-materiais` (4×) | `CanImportCompras` (DAT, Controle) |
| 2 | Ações | `POST /api/controle/import-acoes/` | `/controle` + ComprasPage (4 rotas) | `CanImportGenericSpreadsheet` (DAT, Controle) |
| 3 | Cadastros DAT | `POST /api/dat/import-cadastros/` | `/dat/importacao` | `HasPerm("manage_admin_registries")` (DAT) |
| 4 | Bloqueios | `POST /api/disponibilidade/import-bloqueios/` | `/disponibilidade` + `/solicitacoes/disponibilidade` | `CanImportAvailabilityBlocks` (DAT, Controle) |
| 5 | Deslocamentos | `POST /api/deslocamentos/import/` | `/solicitacoes/deslocamentos` | `CanImportGenericSpreadsheet` (DAT, Controle) |
| 6 | Eventos/Solicitações | `POST /api/solicitacoes/import/` | `/controle` + ComprasPage (4 rotas) | `CanImportGenericSpreadsheet` (DAT, Controle) |
| 7 | Usuários | `POST /api/usuarios/import/` | `/dat/admin/usuarios` (embutido no CRUD) | `HasPerm("manage_admin_registries")` (DAT) |
| 8 | Municípios | `POST /api/municipios/import/` | `/dat/admin/municipios` (embutido no CRUD) | `HasPerm("manage_admin_registries")` (DAT) |
| 9 | Coleções | `POST /api/colecoes/import/` | `/dat/admin/colecoes` | `HasPerm("manage_admin_registries")` (DAT) |
| 10 | Vínculos (Equipe-Gerência) | `POST /api/equipe-gerencia/import/` | `/dat/admin/equipe-gerencia` | `HasPerm("manage_admin_registries")` (DAT) |
| 11 | Produtos | `POST /api/produtos/import/` | `/controle` + ComprasPage (4 rotas) | `CanImportGenericSpreadsheet` (DAT, Controle) |

**Já DAT-only (5)**: Cadastros, Usuários, Municípios, Coleções, Vínculos
**Hoje DAT+Controle (6)**: Compras, Ações, Bloqueios, Deslocamentos, Eventos, Produtos

## 3. Decisões de produto — APROVADAS (2026-04-29)

### D-1 ✅ Reusar `HasPerm("import_spreadsheet")`

Usar `HasPerm("import_spreadsheet")` direto. Não criar `CanUseDatImports` agora.
Motivo: `import_spreadsheet` já é DAT-only no seed atual e resolve o escopo sem nova abstração.

### D-2 ✅ Bloqueios via planilha = DAT-only

Importação em massa de bloqueios → DAT-only.
**Não decide** o fluxo manual de lançamento de bloqueio por Controle/Assistente Administrativo
em nome de outro usuário — esse é tratado em **issue separada** (programa hardening RBAC, PR 13).

### D-3 ✅ Deslocamentos via planilha = DAT-only

Importação em massa de deslocamentos → DAT-only.
**Não decide** o fluxo manual de lançamento de deslocamento por Controle/Assistente Administrativo
em nome de outro usuário — esse é tratado em **issue separada** (programa hardening RBAC, PR 13).

### D-4 ✅ Layout agrupado por categoria

Página `/dat/importacoes` com 3 grupos:

- **Cadastros base**: Usuários, Municípios, Coleções, Cadastros DAT, Vínculos
- **Operacional**: Compras, Ações, Eventos, Produtos
- **Disponibilidade**: Bloqueios, Deslocamentos

### D-5 ✅ Manter rota antiga com redirect

Manter `/dat/importacao` com redirect 301 → `/dat/importacoes`.

### D-6 ✅ Banner informativo com link condicional

Banner explica que importações foram centralizadas em **DAT > Importações**.
Link clicável `/dat/importacoes` **apenas para DAT/superuser**.
Para outros perfis: texto informativo sem link (não dar link para área proibida).

---

## 4. Plano em PRs pequenos (ordem aprovada: B → C → A1 → D)

A ordem foi invertida em relação ao rascunho original. Razão: criar a alternativa visual
**antes** de fechar os endpoints reduz risco operacional. Quando PR-A1 entrar em prod,
DAT já tem `/dat/importacoes` pronta e Controle já viu o aviso no menu.

---

### PR-B (1º): Frontend — criar página `/dat/importacoes`

**Escopo**:

- Nova rota `/dat/importacoes` no `AppRoutes.tsx`
- Nova página `pages/DAT/ImportacoesPage.tsx`
- 11 cards de `ImportUploader` agrupados por 3 categorias (D-4):
  - **Cadastros base**: Usuários, Municípios, Coleções, Cadastros DAT, Vínculos
  - **Operacional**: Compras, Ações, Eventos, Produtos
  - **Disponibilidade**: Bloqueios, Deslocamentos
- **Não remove nada ainda** — coexiste com botões antigos
- Reutiliza funções `importCompras`, `importAcoes`, etc. do `api/ops.ts`
- Guard de rota: `canDAT` ou `is_superuser` (não-DAT recebe `<Forbidden>`)

**Arquivos prováveis**:

- NEW: `v2/frontend/src/pages/DAT/ImportacoesPage.tsx`
- `v2/frontend/src/components/AppRoutes.tsx` (rota nova com gate)
- NEW: `v2/frontend/src/pages/DAT/__tests__/ImportacoesPage.test.tsx`

**Testes**:

- Página carrega com 11 cards agrupados (smoke)
- Não-DAT recebe Forbidden via guard
- Cards renderizam `ImportUploader` com `onDryRun`/`onApply` corretos

**Riscos**: 🟢 **BAIXO** — só adição. Coexistência com fluxos antigos.

**Ordem**: **PRIMEIRO**.

---

### PR-C (2º): Reorganizar menu lateral DAT + redirect

**Escopo**:

- `AppSidebar.tsx`: substituir submenu DAT atual:
  - **Antes**: Administração, Importar Coleções, Importar Vínculos, Cadastros, Importação, Registros de Turmas
  - **Depois**: Administração, Cadastros, **Importações** (→ `/dat/importacoes`), Registros de Turmas
- Remover "Importar Coleções" e "Importar Vínculos" do menu (passam a ser cards dentro de Importações)
- Renomear "Importação" (singular) → "Importações" (plural)
- Redirect 301 de `/dat/importacao` → `/dat/importacoes` (D-5)

**Arquivos prováveis**:

- `v2/frontend/src/components/AppSidebar.tsx`
- `v2/frontend/src/components/AppRoutes.tsx` (redirect)

**Testes**:

- Sidebar para `canDAT` mostra exatamente: Administração + Cadastros + Importações + Registros de Turmas
- Sidebar para Controle/Coord/Formador NÃO mostra "Importações"
- `/dat/importacao` (singular) redireciona para `/dat/importacoes`

**Riscos**: 🟡 **MÉDIO** — UX change para DAT acostumado.

**Ordem**: **SEGUNDO** (depois de PR-B).

---

### PR-A1 (3º): Backend — endpoints DAT-only via `import_spreadsheet`

**Escopo**:

- Trocar `permission_classes` em 6 endpoints hoje DAT+Controle para
  `[IsAuthenticated, HasPerm("import_spreadsheet")]` (D-1):
  - `views_controle_imports.py` — Compras
  - `views_imports.py` — Ações
  - `views_import_bloqueios.py` — Bloqueios (D-2 — apenas import em massa)
  - `views_import_deslocamentos.py` — Deslocamentos (D-3 — apenas import em massa)
  - `views_import_eventos.py` — Eventos
  - `views_import_produtos.py` — Produtos
- Manter os 5 já DAT-only inalterados (`HasPerm("manage_admin_registries")`)
- **Não alterar lógica interna** dos imports, só o gate
- **Não tocar** em ASQ-005 (`/api/imports/bloqueios/` async)
- **Não tocar** em fluxo manual de Controle lançando bloqueio/deslocamento — issue separada
- Tests novos: `test_dat_imports_dat_only.py`

**Arquivos prováveis**:

- 6 arquivos `views_*_imports*.py` listados acima
- NEW: `v2/backend/apps/core/tests/test_dat_imports_dat_only.py`

**Testes**:

- DAT → 200 em todos 11 endpoints
- Controle → 403 nos 6 reorganizados
- Coord, Apoio, Gerente, Diretoria, Formador → 403 em todos
- Anonymous → 401/403
- Smoke: ASQ-005 async (`POST /api/imports/bloqueios/`) NÃO foi tocado

**Riscos**:

- 🔴 **ALTO** — Se Controle hoje usa endpoints em produção, vai parar imediatamente.
- **Mitigação**: PR-B + PR-C já mergeados antes deste, então DAT já tem alternativa pronta.
- **Auditoria recomendada**: pesquisar logs ou perguntar time Controle se houve upload de planilha em Compras/Ações/Eventos/Produtos no último mês.

**Impacto operacional**:

- Controle perde auto-serviço para os 6 imports.
- Fluxo novo: solicitar ao DAT.

**Ordem**: **TERCEIRO** (depois de PR-B + PR-C).

---

### PR-D (4º): Remover botões de importação fora do DAT + banners

**Escopo**:

- `ControlePage.tsx`: remover seção "Importação de dados" (4 cards)
- `DATModule/ComprasPage.tsx`: remover seção equivalente (4 cards)
- `Disponibilidade.tsx`: remover botão "Importar bloqueios"
- `Deslocamentos/DeslocamentosPage.tsx`: remover botão "Importar deslocamentos"
- Adicionar **banner informativo** em cada uma das 4 páginas:
  - Texto: "Importações foram centralizadas em **DAT > Importações**."
  - **Para DAT/superuser**: link clicável `/dat/importacoes`
  - **Para outros perfis**: texto sem link (não dar link para área proibida — D-6)

**Arquivos prováveis**:

- `v2/frontend/src/pages/Controle/ControlePage.tsx`
- `v2/frontend/src/pages/DATModule/ComprasPage.tsx`
- `v2/frontend/src/pages/Disponibilidade.tsx`
- `v2/frontend/src/pages/Deslocamentos/DeslocamentosPage.tsx`
- NEW (opcional): `v2/frontend/src/components/ImportsMigratedBanner.tsx` (componente reutilizável)
- Tests ajustados (snapshot/render)

**Testes**:

- Cada uma das 4 páginas NÃO tem cards/botões de import
- Banner presente em todas com texto correto
- Banner mostra link clicável apenas para DAT/superuser
- Banner para Controle/Coord/Formador é texto puro (sem `<a>`)
- DATModule/ComprasPage continua funcional para listagem

**Riscos**: 🟠 **MÉDIO-ALTO** — remove caminhos de UX existentes.

**Pré-requisitos** (todos mergeados):

1. PR-B (página `/dat/importacoes` existe)
2. PR-C (menu DAT aponta para nova página)
3. PR-A1 (endpoints já fechados — sem regressão de UX exposta a 403)

**Ordem**: **ÚLTIMO**.

---

### PR-E (opcional): Tests adicionais por perfil

Se PR-B, PR-C, PR-A1, PR-D já incluem testes próprios, este pode ser desnecessário.
Caso contrário:

- `test_dat_imports_e2e.py` (backend): 8 perfis × 11 endpoints
- Testes de integração frontend: AppSidebar para 8 perfis, AppRoutes para 8 perfis

**Riscos**: 🟢 **BAIXO** — só testes.

---

## 5. Ordem recomendada (aprovada)

```text
1. PR-B  — criar /dat/importacoes (nova página, sem remoção)         [primeiro]
2. PR-C  — reorganizar menu DAT + redirect /dat/importacao            [segundo]
3. PR-A1 — backend DAT-only nos 6 endpoints (Controle perde acesso)   [terceiro]
4. PR-D  — remover botões antigos + banners informativos              [último]
5. PR-E  — testes adicionais (opcional)
```

Razão da ordem: criar alternativa visual e menu **antes** de fechar endpoints garante que
DAT já tem fluxo novo pronto e Controle já tem aviso no menu quando o backend deixar de
responder. Reduz janela de regressão operacional para zero.

## 6. Mapa "fluxo Controle hoje → fluxo Controle depois"

| Antes (Controle clica) | Depois (Controle clica) |
|------------------------|--------------------------|
| `/controle` → "Importar COMPRAS" | banner: "Importação migrada para DAT" |
| `/controle` → "Importar AÇÕES" | banner: idem |
| `/controle` → "Importar EVENTOS" | banner: idem |
| `/controle` → "Importar PRODUTOS" | banner: idem |
| `/controle/compras` → tab "Importar" | banner: idem |
| `/disponibilidade` → "Importar bloqueios" | depende de D-2 |
| `/solicitacoes/deslocamentos` → "Importar" | depende de D-3 |

**Caminho novo único** (DAT/superuser): `/dat/importacoes` — 1 página, 11 cards.

## 7. Riscos cross-PR

- **Risco operacional**: Se Controle estava operando imports em prod, PR-A1 quebra. **Mitigação**: auditoria de logs ou pesquisa qualitativa antes do PR.
- **Risco de UX**: usuários DAT acostumados com submenus específicos (Importar Coleções, Importar Vínculos) vão ter que aprender página unificada. **Mitigação**: comunicação prévia + onboarding interno.
- **Risco de coexistência**: PR-A1 (backend) sem PR-B (frontend) deixa Controle sem alternativa visual. **Mitigação**: sequenciar corretamente — se PR-A1 mergeado primeiro, comunicar imediatamente que PR-B vem em sequência.
- **Risco de regressão de import async**: PR-D não toca em ASQ-005 (`/api/imports/bloqueios/`). Se Phase 2 do ASQ-005 (#778) entrar em paralelo, alinhar com plano.
- **Risco de RBAC dependente**: PR-A1 não aprofunda em RBAC de Bloqueios/Deslocamentos. Se decisão D-2/D-3 disser "manter Controle", a regra "DAT-only" tem exceções explícitas.

## 8. Checklist de validação por PR (decisões já aprovadas)

### PR-B (1º)
- [x] D-4 (layout agrupado por categoria) ✅ aprovado
- [x] D-5 (redirect) ✅ aprovado
- [ ] Página renderiza com 11 cards em 3 grupos (smoke)
- [ ] Guard de rota: não-DAT → Forbidden
- [ ] CI verde, staging gate verde

### PR-C (2º)
- [ ] PR-B mergeado
- [ ] Sidebar DAT: 4 itens (Administração, Cadastros, Importações, Registros)
- [ ] Outros perfis: sem item Importações
- [ ] Redirect 301 `/dat/importacao` → `/dat/importacoes`
- [ ] Tests por perfil
- [ ] CI verde, staging gate verde

### PR-A1 (3º)
- [x] D-1 (`HasPerm("import_spreadsheet")` direto) ✅ aprovado
- [x] D-2 (bloqueios import-em-massa = DAT-only) ✅ aprovado
- [x] D-3 (deslocamentos import-em-massa = DAT-only) ✅ aprovado
- [ ] Auditoria operacional Controle imports (recomendada antes do merge)
- [ ] Tests: DAT 200 + Controle 403 + outros 403 em todos 6 endpoints
- [ ] Smoke: ASQ-005 async não foi tocado
- [ ] Smoke: views de bloqueio/deslocamento manual (não-import) não foram tocadas
- [ ] CI verde, staging gate verde

### PR-D (4º)
- [ ] PR-B + PR-C + PR-A1 todos mergeados
- [x] D-6 (banner com link condicional) ✅ aprovado
- [ ] Tests confirmando ausência dos cards antigos em ControlePage, ComprasPage, Disponibilidade, DeslocamentosPage
- [ ] Tests do banner com link clicável apenas para DAT/superuser
- [ ] CI verde, staging gate verde

## 9. Itens fora deste plano (não tocar)

- Importação async ASQ-005 (`/api/imports/bloqueios/`) — Phase 2 separada (#778)
- PR municípios IBGE (#1298 mergeado; pipeline IBGE pode evoluir em outro PR)
- RBAC Grade Mensal / Aprovações (programa hardening em curso, PRs separados)
- `seed_produtos` management command (não relacionado)
- Registros de Turmas (`/dat/registros`) — fora desta reorganização

## 10. Próximo passo

Decisões D-1 a D-6 ✅ aprovadas em 2026-04-29. Pronto para iniciar:

**PR-B**: criar página `/dat/importacoes` com 11 cards agrupados em 3 categorias.

Branch sugerida: `feat/dat-importacoes-page`.

Quando PR-B mergear, seguir: PR-C → PR-A1 → PR-D.

**Não tocar**:
- ASQ-005 async (`/api/imports/bloqueios/`) — Phase 2 separada (#778)
- Pipeline IBGE (PR #1298 já mergeado)
- RBAC Grade Mensal/Aprovações (programa hardening em curso)
- Registros de Turmas (`/dat/registros`)
- Fluxo manual de Controle/Assistente Administrativo lançando bloqueio/deslocamento em
  nome de outro usuário (issue separada do programa hardening RBAC, PR 13)
