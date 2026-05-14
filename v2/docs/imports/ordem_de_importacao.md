# Ordem de Importação

Status: PR 1 — documentação (revista 2026-05-05)
Versão: 2026-05-05 v0.2

> ⚠️ **Atualização v0.2**: substituiu pendências que o código já responde por pendências reais. Os 11 services `*_import.py` já existem; a "ordem" é operacional (sequência de execução em produção) e não mais um roadmap de implementação.

A ordem abaixo respeita as dependências de chave estrangeira e regras de domínio. **Não pular passos**: cada etapa cria os referenciais usados pela próxima.

---

## Ordem recomendada

### 1. Usuários

- **Por quê primeiro**: vários objetos referenciam `Usuario` via FK (Solicitacao.coordenador, Solicitacao.formadores M2M, AvailabilityBlock.usuario, AuditLog.usuario, DATCompra.created_by, etc.).
- **Documento**: [usuarios.md](./usuarios.md)
- **Pré-requisito**: nenhum (depois disso, cadastros base já podem ser feitos por usuário admin).

### 2. Cadastros base — Grupos / Setores / Funções

- **Por quê**: definir 13 Setores + 5 Funções (SSOT em `apps/core/constants.py`).
- **Como**: management command `seed_rbac` (manual, com `--verbose`). **NÃO automatizar** em deploy (D17).
- **Atribuição Group × Capability**: via Django Admin (`/admin/core/permissaofuncional/`), nunca em migration.
- **Sem documento de import** porque cadastros base já existem no schema (não vêm de planilha).

### 3. Municípios

- **Por quê**: Solicitacao e DATCompra usam FK para `Municipio`.
- **Service real**: `apps/core/services/municipios_import.py` (`import_municipios_from_file`).
- **Endpoint**: `POST /api/municipios/import/` — gate `HasPerm("manage_admin_registries")`.
- **Pendência para Matheus**: confirmar cabeçalho real esperado e se `sheets.banco` é a fonte ou se há fixture/seed inicial separada.

### 4. Projetos

- **Por quê**: Solicitacao e Produto usam FK para `Projeto`.
- **Fonte atual**: cadastro inicial; `fluxo` (SUPER/NAO_SUPER) define gate de aprovação (PA-01).
- **Sem service `projetos_import.py` dedicado** no código atual. `sheets.banco` provavelmente não inclui catálogo de projetos — apenas referencia via nome em Produtos e Agenda. Resolvidos no runtime via `resolve_projeto` (com aliases IDEB→GESTÃO ESCOLAR, Nível N→NN).

### 5. Produtos (catálogo)

- **Por quê**: Compra/DATCompra usam FK para `Produto`.
- **Service real**: `apps/core/services/produtos_import.py` (`import_produtos_from_file`).
- **Endpoint**: `POST /api/produtos/import/` — gate `HasPerm("import_spreadsheet")`.
- **Fonte histórica**: 139 produtos cadastrados (`produtos.xlsx`), cada um com `codigo` único e FK para `Projeto`.
- Catálogo é **atualizável via importação** — não está congelado.

### 6. Controle/Produtos por município (Compras / DATCompra)

- **Por quê**: registra uso operacional (`DATCompra`) ou histórico (`Compra`) de cada produto em cada município.
- **Documento**: [produtos_controle.md](./produtos_controle.md)
- **Pré-requisitos**: Produtos cadastrados (passo 5), Municípios (passo 3), Projetos (passo 4).

### 7. Disponibilidade

- **Por quê**: declara bloqueios (T/P) de formadores.
- **Documento**: [disponibilidade.md](./disponibilidade.md)
- **Service real**: `apps/core/services/bloqueios_import.py` (`import_bloqueios_from_file`).
- **Endpoints**: `POST /api/disponibilidade/import-bloqueios/` (síncrono) **e** `POST /api/imports/bloqueios/` (assíncrono, ASQ-005 Fase 1 — único piloto async hoje).
- **Pré-requisitos**: Usuários (passo 1).
- **Limites conhecidos**: tipos `T` e `P` suportados. **`D` (deslocamento) não armazenado como bloqueio** — calculado dinamicamente pelo `availability_service` entre Solicitações de municípios diferentes. **Recorrência** ainda não modelada.

### 8. Agenda / Solicitações / Eventos

- **Por quê**: agendamento concreto de eventos.
- **Documento**: [agenda_solicitacoes.md](./agenda_solicitacoes.md)
- **Service real**: `apps/core/services/eventos_import.py` (`import_eventos_from_file`). Cria 1 `Solicitacao` + N `Participation` (coord + formadores 1..5). PA-01 aplicada automaticamente.
- **Endpoint**: `POST /api/solicitacoes/import/` — gate `HasPerm("import_spreadsheet")`.
- **Pré-requisitos**: Usuários (passo 1), Municípios (passo 3), Projetos (passo 4).
- **Crítico**: PA-01 aplicada — SUPER + data futura → `pendente`. GCal **nunca é tocado** pelo import.

### 9. Google Calendar — somente após validação manual

- **Por quê**: publicar é efeito externo (cria evento no calendar de produção).
- **NÃO faz parte do import** automatizado.
- **Fluxo correto**:
  1. Importar Agenda (passo 8) → solicitações ficam `pendente` ou `aprovado` por reconciliação.
  2. Revisão manual no frontend (`/aprovacoes`).
  3. Preview GCal (`POST /api/solicitacoes/{id}/preview-gcal/`).
  4. Publish (`POST /api/solicitacoes/{id}/publish/`) — só após aprovação manual.
- **PA-03** (CP-02): integrações externas (RF05/RF06) só rodam **após** aprovação manual completa.

---

## Razões da ordem

```text
Usuários ────► Cadastros base (Grupos/Setores/Funções)
   │              │
   ▼              ▼
   │           Municípios ────► Projetos ────► Produtos
   │              │                │              │
   │              ▼                ▼              ▼
   └────► Disponibilidade        Agenda ────► Controle/Compras
                                  │
                                  ▼
                          (revisão manual)
                                  │
                                  ▼
                          Google Calendar
```

Cada seta indica dependência de FK ou de validação de domínio.

---

## Reentrância (re-execução de imports)

Todos os imports são **idempotentes** via `external_hash`. Re-rodar o mesmo arquivo:

- **Sem mudança**: nenhuma operação (linhas com hash existente são ignoradas).
- **Atualização tolerada**: campos não-chave podem ser atualizados se `external_hash` bater e linha vier com dados diferentes (depende do tipo — ver doc específico).
- **Re-criação**: para forçar re-criação, deletar a linha do banco antes (com cuidado em FKs).

Auditar reentrância via `AuditLog` filtrado por `action LIKE 'IMPORT_%'` e `usuario`.

---

## Pendências para Matheus

- Existe pipeline automatizado entre `sheets.banco` e o sistema (ex: cron + API) ou todo import é manual via UI/CLI?
- Municípios e Projetos têm uma fonte de cadastro contínua na planilha ou ficam congelados após o seed inicial?
- Em quais cenários **Cadastros base** (passo 2) precisam ser refeitos pós-deploy? Sentinela D17 deveria bloquear?
- Disponibilidade deve preceder Agenda no fluxo real ou as duas chegam juntas?
