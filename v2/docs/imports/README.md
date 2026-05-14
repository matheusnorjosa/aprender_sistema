# Contratos de Importação — `sheets.banco` → Aprender Sistema v2

Status: **PR 1 — documentação e contratos (revisada 2026-05-05 contra código real)**
Versão: 2026-05-05 v0.2
Origem: `sheets.banco` (planilha consolidada externa)
Destino: PostgreSQL (`apps.core`) via endpoints HTTP DRF (síncronos `POST /api/<recurso>/import/`) ou async (`POST /api/imports/<tipo>/` — ASQ-005 Fase 1, apenas `bloqueios` por enquanto)

> ⚠️ **Atualização v0.2 (2026-05-05)**: a versão inicial v0.1 tratou como "futuro" várias coisas que **já existem no código**. Esta versão corrige o drift, lista paths reais, e reorienta o roadmap. Ver §3.1 "Estado real do código" e §8 "Roadmap revisto".

---

## 1. Propósito

Este diretório define **contratos de importação** entre a planilha externa `sheets.banco` e o sistema Aprender Sistema v2. Cobre:

- Formato esperado das colunas em cada CSV.
- Normalizações exigidas antes do upload.
- Validações que o sistema aplica.
- Idempotência (regras de duplicidade e `external_hash`).
- Models, services e endpoints do backend envolvidos.
- O que **não** deve acontecer automaticamente (gates de revisão humana).
- Como auditar o resultado.

Esta PR (PR 1) entrega **apenas a documentação e templates fictícios**. Não cria endpoints novos, não altera models, não importa dados reais.

---

## 2. Princípios gerais (válidos para os 4 tipos)

### 2.1 Dry-run obrigatório antes de apply

Toda importação tem 2 etapas:

1. **Dry-run** — valida + retorna preview, **não persiste**.
2. **Apply** — só após dry-run sem erros bloqueantes.

Comandos atuais (referência — não implementados nesta PR):
- `make etl-acomp-dry` / `etl-acomp-apply` — acompanhamento legacy.
- `make etl-desloc-dry` / `etl-desloc-apply` — deslocamentos.
- `make etl-acoes-dry` / `etl-acoes-apply` — ações controle.
- `make etl-dat-dry` / `etl-dat-apply` — DAT cadastros.
- `make import-compras-dry` / `import-cadastros-dry` / `import-acoes-dry`.

### 2.2 Idempotência via `external_hash`

Imports históricos usam SHA1 (ou SHA256 nos services novos) sobre uma chave natural composta. Re-rodar o mesmo arquivo **não duplica linhas**.

Implementação atual: vista em `apps/core/services/dat_cadastros_import.py:301`, `controle_acoes_import.py:265`, `controle_imports.py:36`, `deslocamentos_import.py:257` (auditoria 2026-05 sugere consolidar em `services/hash_utils.py::compute_external_hash`).

### 2.3 RBAC — quem pode importar

- Imports históricos (legacy): exigem `import_spreadsheet` (DAT).
- Imports operacionais: cobertas por policies públicas:
  - `import_availability_blocks` — DAT + Controle/Gerente/Coord.
  - `import_compras` — DAT + Compras + Controle.
  - `import_generic_spreadsheet` — DAT + Controle.

Atribuição via Django Admin (D17 — admin-driven, ratificado 2026-05-04). Não automático em deploy.

### 2.4 Audit trail

Toda importação real grava `AuditLog` com:
- `usuario` (quem rodou).
- `action` (ex: `IMPORT_USUARIOS`, `IMPORT_COMPRAS`).
- `model_name`.
- `details` (JSON): `arquivo_hash`, `linhas_processadas`, `linhas_criadas`, `linhas_atualizadas`, `linhas_ignoradas`, `linhas_erro`.

Nota: a estrutura `ImportBatch` proposta na PR 4 (futura) substitui parte do `details` por modelo dedicado com rastreabilidade rica.

### 2.5 Timezone

Datas de calendário (Solicitação, AvailabilityBlock) **são armazenadas em UTC** e comparadas em **`America/Fortaleza`** (RD-06). Toda data/hora vinda do CSV deve ser tratada como horário local Fortaleza antes de virar UTC.

### 2.6 Nenhum efeito colateral perigoso

Importação **NUNCA**:
- Publica eventos no Google Calendar (mesmo se `external_event_id` vier preenchido).
- Aprova solicitações (PA-01: fluxo SUPER exige aprovação manual).
- Atribui grupos `Gerente`/`Superintendência` automaticamente.
- Cria usuário com `is_superuser=True`.
- Sobrescreve dados sem `external_hash` confirmando match.

---

## 3. Tipos de importação cobertos

| Tipo | Documento | Template CSV | Backend implementado | Endpoint |
|---|---|---|---|---|
| Usuários | [usuarios.md](./usuarios.md) | [templates/usuarios.template.csv](./templates/usuarios.template.csv) | ✅ Sim | `POST /api/usuarios/import/` |
| Produtos / Controle / Compras | [produtos_controle.md](./produtos_controle.md) | [templates/produtos_controle.template.csv](./templates/produtos_controle.template.csv) | ✅ Sim | `POST /api/produtos/import/` + `POST /api/controle/import-compras/` |
| Agenda / Solicitações / Eventos | [agenda_solicitacoes.md](./agenda_solicitacoes.md) | [templates/agenda_solicitacoes.template.csv](./templates/agenda_solicitacoes.template.csv) | ✅ Sim, com PA-01 | `POST /api/solicitacoes/import/` |
| Disponibilidade / Bloqueios | [disponibilidade.md](./disponibilidade.md) | [templates/disponibilidade.template.csv](./templates/disponibilidade.template.csv) | ✅ Tipos T/P (D pendente) | `POST /api/disponibilidade/import-bloqueios/` (sync) + `POST /api/imports/bloqueios/` (async, ImportJob) |

Ordem de execução: [ordem_de_importacao.md](./ordem_de_importacao.md).

**Auditoria de shape de retorno** (PR 2, 2026-05-05): [dry_run_response_contract.md](./dry_run_response_contract.md) — análise dos 11 services + contrato padrão proposto + plano de migração em 5 fases.

---

## 3.1 Estado real do código (auditoria 2026-05-05)

Para os 4 tipos acima, o backend **já tem implementação funcional** em produção. Os contratos deste diretório descrevem o formato esperado da planilha `sheets.banco` e servem para **alinhar a geração de CSV externa com o que o backend já aceita** — não para projetar funcionalidades inexistentes.

### Services (11 já implementados em `apps/core/services/`)

| Service | Função pública | Idempotência | Dry-run |
|---|---|---|---|
| `usuarios_import.py` | `import_usuarios_from_file(path, dry_run=True)` | CPF (unique) | ✅ |
| `eventos_import.py` | `import_eventos_from_file(path, dry_run=True)` | `external_hash` + Participation M2M | ✅ |
| `bloqueios_import.py` | `import_bloqueios_from_file(path, dry_run=True)` | tupla (usuario, inicio, fim, tipo) | ✅ |
| `produtos_import.py` | `import_produtos_from_file(...)` | `Produto.codigo` | ✅ |
| `colecoes_import.py` | `import_colecoes_from_file(...)` | — | ✅ |
| `municipios_import.py` | `import_municipios_from_file(...)` | — | ✅ |
| `equipe_gerencia_import.py` | `import_equipe_gerencia_from_file(...)` | — | ✅ |
| `controle_imports.py` | `import_compras_from_file(...)` (alimenta **`Compra`**) | SHA1 `external_hash` | ✅ |
| `controle_acoes_import.py` | `import_acoes_controle(...)` | SHA1 | ✅ |
| `dat_cadastros_import.py` | `import_dat_cadastros(...)` | SHA1 | ✅ |
| `deslocamentos_import.py` | `import_deslocamentos(...)` | SHA1 | ✅ |

Helpers de reconciliação compartilhados em `apps/core/services/resolvers.py`:

- `resolve_user_by_email(email)`, `resolve_user_by_name(name)` (com fallback heurístico por partes do nome).
- `resolve_municipio(nome)` — aceita formatos `"Cidade"`, `"Cidade - UF"`, `"Cidade (UF)"`, `"Cidade/UF"`; normaliza com NFKD.
- `resolve_projeto(nome)` — aceita código ou nome; aplica `normalize_projeto_name` com aliases (IDEB→GESTÃO ESCOLAR, "Nível 1"→N1, "Vida &"→"VIDA E", etc.).
- `resolve_tipo_evento(nome)`.
- `_nfkd(value)` para normalização case-insensitive sem acento.
- Texto base em `apps/core/services/normalize.py::norm_text()`.

### Endpoints HTTP

**Síncronos** (10 endpoints, retornam `{stats, pendencias, dry_run, file}`):

| Endpoint | View | Gate RBAC |
|---|---|---|
| `POST /api/usuarios/import/` | `ImportUsuariosView` | `HasPerm("manage_admin_registries")` |
| `POST /api/solicitacoes/import/` | `ImportEventosView` | `HasPerm("import_spreadsheet")` |
| `POST /api/disponibilidade/import-bloqueios/` | `ImportBloqueiosView` | `HasPerm("import_spreadsheet")` |
| `POST /api/produtos/import/` | `ImportProdutosView` | `HasPerm("import_spreadsheet")` |
| `POST /api/municipios/import/` | `ImportMunicipiosView` | `HasPerm("manage_admin_registries")` |
| `POST /api/colecoes/import/` | `ImportColecoesView` | `HasPerm("manage_admin_registries")` |
| `POST /api/equipe-gerencia/import/` | `ImportEquipeGerenciaView` | `HasPerm("manage_admin_registries")` |
| `POST /api/controle/import-compras/` | `ImportComprasView` | `HasPerm("import_spreadsheet")` |
| `POST /api/controle/import-acoes/` | `ControleImportAcoesView` | `HasPerm("import_spreadsheet")` |
| `POST /api/dat/import-cadastros/` | `DATImportCadastrosView` | `HasPerm("manage_admin_registries")` |

Todos aceitam `?dry_run=true|false` (default `true`).

**Assíncronos (ASQ-005 Fase 1)** — apenas `bloqueios` por enquanto:

- `POST /api/imports/bloqueios/` — cria `ImportJob` + dispatcha Celery task; retorna `202 Accepted` com `job_id`.
- `GET /api/imports/<id>/` — status + stats + pendencias do job.
- `GET /api/imports/` — lista jobs do usuário (filtros `type=`, `status=`).

### Model `ImportJob` ([apps/core/models/import_job.py](../../backend/apps/core/models/import_job.py))

Modelo de rastreabilidade de execuções async. Campos:

- `user` (FK Usuario, PROTECT), `import_type` (TextChoices — hoje só `BLOQUEIOS`), `status` (QUEUED|RUNNING|SUCCESS|FAILED).
- `file` (FileField em `imports/%Y/%m/%d/`), `original_filename`.
- `dry_run` (Boolean), `stats` (JSON), `pendencias` (JSON).
- `error_message` (≤500c), `error_traceback` (não exposto via API).
- `celery_task_id`, `duration_ms`, timestamps + métodos `mark_running/success/failed`.

Comentário do código: **"Fase 2 migrará USUARIOS, COMPRAS, ACOES, DESLOCAMENTOS, EVENTOS, PRODUTOS, MUNICIPIOS, COLECOES, EQUIPE_GERENCIA"** — esse é o backlog real.

### Frontend (3 páginas confirmadas; mais provavelmente)

- `v2/frontend/src/pages/DAT/ImportacoesPage.tsx` — hub `/dat/importacoes`.
- `v2/frontend/src/pages/AdminDAT/ColecoesImportPage.tsx`.
- `v2/frontend/src/pages/AdminDAT/EquipeGerenciaImportPage.tsx`.
- Páginas adjacentes de cadastro AdminDAT (Usuarios, Municipios, Produtos, Projetos, Grupos, Setores, Funcoes, Gerencias) — gerenciam CRUD, **não confirmado** se cada uma tem botão de upload de planilha.

### Makefile (chama endpoints HTTP via curl)

Targets atuais em `v2/Makefile` (ex: `make import-compras-dry FILE=...`) **chamam `curl` para `/api/<recurso>/import/?dry_run=true`** — **não** existem `management commands` `etl_*.py` nem `import_*.py` em `apps/core/management/commands/`. Documentação `make etl-acomp-dry` em outros docs do projeto é referência histórica.

---

## 4. Convenções dos templates CSV

- **Encoding**: UTF-8 (sem BOM).
- **Separador**: `,` (vírgula).
- **Quote**: aspas duplas em campos com vírgula/espaço/linha.
- **Decimal**: ponto (`12.50`, não `12,50`).
- **Data**: `dd/mm/yyyy` (BR) — normalizada para ISO no service.
- **Hora**: `HH:MM` (24h).
- **Boolean** (quando aplicável): `sim`/`não`, `true`/`false`, `1`/`0`.
- **CPF**: 11 dígitos sem máscara (vai ser normalizado).
- **Telefone**: dígitos puros ou com máscara — será normalizado.
- **Cabeçalho**: snake_case ou nomes da planilha original (documento explicita por tipo).

Todos os templates contêm **uma linha fictícia** com CPF `00000000000` e email `*.exemplo@example.com` — **não usar como dado real**.

---

## 5. Como propor mudanças de contrato

1. Editar o markdown do tipo afetado nesta pasta.
2. Atualizar o template CSV correspondente.
3. Documentar a mudança em "Histórico de versões" do próprio arquivo.
4. PR com label `documentation` + revisão obrigatória do dono da etapa.
5. Após merge, atualizar service correspondente (PR separada).

Mudanças que quebram contrato (renomear coluna obrigatória, mudar tipo de dado, mudar regra de hash) exigem deprecation period: aceitar formato antigo por 1 release com warning, derrubar no seguinte.

---

## 6. Pendências cross-cutting (para Matheus)

- **Reconciliação de Usuario por nome** vs por email vs por CPF: em Agenda (Formador 1..5), qual chave usar? CPF não aparece na planilha de agenda. Atualmente, services legacy fazem fuzzy-match por nome — **risco de match errado**.
- **Mapeamento Cargo → Função RBAC**: `usuarios.md` propõe tabela; falta confirmar todos os termos da planilha original.
- **Disponibilidade** ainda não tem contrato estável — formato em aberto.
- **Decisão D17 e Imports**: imports não devem atribuir capabilities (admin-driven). Confirmar que `seed_rbac` automático não é parte do pipeline de import.

---

## 7. Referências internas

- `v2/docs/RBAC_NAMING.md` — convenção RBAC.
- `v2/docs/IMPLEMENTACAO_PA.md` — política de aprovação (PA-01..07).
- `v2/docs/GUIDE_AVAILABILITY.md` — RD-01..08.
- `v2/docs/GUIDE_GCAL.md` — integração GCal.
- `v2/docs/MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md` — gerência ↔ setor.
- `apps/core/services/dat_cadastros_import.py` — service exemplar (idempotência via SHA1).
- `apps/core/management/commands/etl_*.py` — comandos atuais.

---

## 8. Roadmap das próximas PRs (revisto 2026-05-05)

> ⚠️ O roadmap anterior (v0.1) propunha "criar do zero" coisas que já existem. Esta versão alinha o backlog ao código real.

| PR | Escopo | Justificativa | Risco |
|---|---|---|---|
| PR 1 | Documentação e contratos + templates (este PR, revisado) | Alinhar `sheets.banco` com formato aceito hoje | Nenhum (docs-only) |
| PR 2 | **Auditar e padronizar shape de retorno de dry-run** nos 11 services existentes | Cada service hoje retorna estrutura ligeiramente diferente (`stats/pendencias`, `relatório`, `created_ids`, etc.); contrato único facilita frontend e testes | Baixo (não muda comportamento) |
| PR 3 | **Consolidar helpers de normalização** em `apps/core/imports/normalization.py` extraindo o que já existe em `services/resolvers.py` + `services/normalize.py` | Hoje há helpers úteis (`resolve_municipio`, `resolve_projeto`, `_nfkd`, `norm_text`) mas falta `normalize_cpf`, `normalize_phone`, `parse_br_date`, `parse_bool_ptbr`, `build_import_hash` como API pública | Baixo (refactor) |
| PR 4 | **Migrar 9 imports síncronos restantes para `ImportJob` async** (ASQ-005 Fase 2) — usuários, compras, ações, deslocamentos, eventos, produtos, municípios, coleções, equipe_gerencia. Um tipo por sub-PR | Padroniza upload + rastreabilidade; já há infra pronta para `bloqueios` | Médio (Celery + auditoria) |
| PR 5 | **Adicionar botões "Baixar template"** nas páginas de import existentes (`ImportacoesPage.tsx`, `ColecoesImportPage.tsx`, `EquipeGerenciaImportPage.tsx`, e demais que aceitem upload) — apontando para `v2/docs/imports/templates/*.csv` | UX: hoje **não confirmado** se algum botão existe | Baixo (frontend simples) |
| PR 6 (talvez desnecessária) | Reforçar **validadores específicos** apenas se PR 2 identificar lacuna | Cada service já tem suas validações; provavelmente bastam ajustes pontuais | A definir após PR 2 |

### Ordem sugerida

1. **PR 2** (auditar shape de retorno) — barata, esclarece estado real.
2. **PR 3** (consolidar normalizadores) — refactor seguro com testes.
3. **PR 5** (botões de template) — paralelizável com 2 e 3.
4. **PR 4** (migração async, 1 tipo por sub-PR) — depende de PR 2 estabilizar contrato.
5. **PR 6** só se PR 2 expuser regras divergentes.

### Coisas que **NÃO** precisam virar PR

- Criar `ImportBatch` (já existe `ImportJob`).
- Criar dry-run (todos os services já implementam).
- Criar services `*_import.py` (11 já existem).
- Criar endpoints (10 síncronos + 3 async já existem).
- Criar `normalize_text_key`, `resolve_municipio`, `resolve_projeto` (já existem em `resolvers.py`/`normalize.py`).
