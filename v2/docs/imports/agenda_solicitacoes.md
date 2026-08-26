# Importação: Agenda / Solicitações / Eventos

Status: PR 1 — contrato fechado, **backend implementado**; **§9 e §10 descreviam garantias que não existem** (revisto 2026-07-24)
Versão: 2026-07-24 v0.3
Template: [templates/agenda_solicitacoes.template.csv](./templates/agenda_solicitacoes.template.csv)

> ⚠️ **Atualização v0.2**: a v0.1 tratava o service como "futuro". Na verdade `apps/core/services/eventos_import.py` já existe e funciona, cria `Participation` M2M (coordenador + formadores 1..5) e tem idempotência via `external_hash`. Endpoint funcional: `POST /api/solicitacoes/import/`.

> 🔴 **Atualização v0.3 (2026-07-24)** — três correções de fato, todas provadas em código:
>
> 1. **A data do evento NÃO influencia o status.** A v0.2 repetia "SUPER **+ data futura** → `pendente`".
>    O service chama `resolve_initial_status(projeto=projeto)` (`eventos_import.py:497`) — só o
>    `projeto.fluxo` decide. A própria docstring diz: *"A data do evento NAO influencia o status
>    (passado/futuro irrelevante)"* (`eventos_import.py:23`).
> 2. **O import grava solicitação `aprovado` sem o hard gate de disponibilidade.** Para
>    `fluxo == 'NAO_SUPER'` a linha entra direto como aprovada e `check_conflicts` **nunca é
>    chamado** — `eventos_import.py` não importa `availability_service` nem
>    `solicitacao_availability`. Achado `M08-12`, issue
>    [#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620) (épico
>    [#1659](https://github.com/matheusnorjosa/aprender_sistema/issues/1659)).
> 3. **Reimport SOBRESCREVE decisão de aprovação, owner e datas — e reporta "unchanged".**
>    A v0.2 afirmava "linhas com hash existente são ignoradas". Falso: é
>    `Solicitacao.objects.update_or_create(external_hash=..., defaults={...})`
>    (`eventos_import.py:523-539`), e os `defaults` incluem `usuario`, `coordenador`, `inicio`,
>    `fim` e `status`. Pior: o cálculo de `changed` (`:544-556`) compara o objeto **já
>    atualizado** contra os valores novos, então bate sempre igual e a estatística cai em
>    `unchanged`. Achado `M10-07`, issue
>    [#1628](https://github.com/matheusnorjosa/aprender_sistema/issues/1628).
>
> Ver documento vivo: [../audits/ACHADOS_REAIS.md](../audits/ACHADOS_REAIS.md).

---

## 1. Objetivo

Importar registros de agendamento de eventos pedagógicos (formações, acompanhamentos, provas) a partir da aba de "Agenda" da planilha `sheets.banco`. Alimenta `apps.core.models.solicitacao.Solicitacao`.

Cobre:
- Criação de `Solicitacao` em status correto (PA-01).
- Lookup de Municipio, Projeto, Coordenador, Formadores.
- Validação de horários (RD-06 timezone Fortaleza, fim > início).
- Idempotência via `external_hash`.

NÃO cobre (crítico):
- **Publicação no Google Calendar** (RF05/RF06) — só após aprovação manual (PA-03). ✅ verdadeiro:
  `eventos_import.py` não importa nenhum client GCal.
- **Aprovação automática de fluxo SUPER** — se `projeto.fluxo=="SUPER"`, status inicial é `pendente`. ✅
  verdadeiro. ⚠️ Mas `NAO_SUPER` entra **`aprovado`** direto, sem checagem de disponibilidade (#1620).
- ~~**Atualização/cancelamento** de Solicitacao existente automaticamente~~ — ❌ **FALSO**:
  o reimport atualiza sim, e sobrescreve status/owner/datas (#1628). Ver §9.

---

## 2. Dados de origem esperados

Aba `Agenda` (ou `Acompanhamento`) da planilha `sheets.banco`.

| Coluna planilha | Descrição |
|---|---|
| `e` | (?) — semântica a confirmar; possivelmente flag/marker da linha |
| `Aprovação` | Status de aprovação na planilha (texto livre — "Sim"/"Não"/"Pendente") |
| `Atualizar` | Flag indicando que a linha foi modificada (não usar como gatilho automático) |
| `Cancelar` | Flag indicando que o evento foi cancelado |
| `Municípios` | Nome do município onde ocorre o evento |
| `encontro` | Tipo/número de encontro (ex: "Formação 3", "Acompanhamento 1") |
| `tipo` | Tipo de evento (ex: "Formação", "Prova", "Acompanhamento") |
| `data` | Data do evento (BR `dd/mm/yyyy`) |
| `hora início` | Hora de início (BR `HH:MM` 24h) |
| `hora fim` | Hora de fim |
| `projeto` | Nome ou código do projeto |
| `segmento` | Segmento (ex: "Fundamental I", "Fundamental II") |
| `Coord Acompanha` | Coordenador que acompanha (nome) |
| `Coordenador` | Coordenador principal |
| `Formador 1` | Primeiro formador |
| `Formador 2` | Segundo formador (opcional) |
| `Formador 3..5` | Formadores adicionais (opcional) |
| `Convidados` | Emails de convidados extras (separados por `;` ou `,`) |

---

## 3. Colunas obrigatórias

| Coluna CSV | Validação |
|---|---|
| `municipio` (vem de `Municípios`) | Lookup `Municipio.nome` + sanity UF se vier |
| `tipo` | Tipo de evento conhecido (proposta: enum mapping) |
| `data` | Data BR válida; >= hoje - 365 dias e <= hoje + 365 dias (proteção contra typo) |
| `hora_inicio` | `HH:MM` válido |
| `hora_fim` | `HH:MM` válido + maior que `hora_inicio` |
| `projeto` | Lookup `Projeto.nome` ou `Projeto.codigo` |
| `formador_1` | Lookup `Usuario` com Função `Formador` (reconciliação) |

---

## 4. Colunas opcionais

| Coluna CSV | Comportamento se vazio |
|---|---|
| `e` | Ignorado (semântica desconhecida) |
| `aprovacao_planilha` | **NÃO** usar para aprovar; apenas registrar em `details` do AuditLog |
| `atualizar`, `cancelar` | Apenas gerar warning + listar para revisão humana; **não disparar update/cancel** |
| `encontro` | Salvar em campo texto livre ou em `observacoes` |
| `segmento` | Salvar como tag/texto, sem mapeamento estrito |
| `coord_acompanha` | Lookup `Usuario`; pode ficar `null` |
| `coordenador` | Lookup `Usuario` (Função Coordenador); se vazio, herdar do coord. logado |
| `formador_2..5` | Adicionar à M2M `formadores` se preenchido |
| `convidados` | Split por `;`/`,`, validar emails, adicionar em `extra_participants` |

---

## 5. Normalizações esperadas (PR 2 — `normalization.py`)

| Campo | Função (futura) | Resultado |
|---|---|---|
| `municipio` + (uf?) | `normalize_municipio_uf` | `(nome, uf)` |
| `data` | `parse_br_date` | `datetime.date` |
| `hora_inicio`, `hora_fim` | `parse_br_time` | `datetime.time` |
| `data` + `hora_inicio` → `inicio` | combine + `make_aware(tz=America/Fortaleza)` | `datetime` UTC armazenado |
| `data` + `hora_fim` → `fim` | idem | `datetime` UTC armazenado |
| `projeto` | `normalize_text_key` | Lookup nome/código |
| `coordenador`, `formador_*`, `coord_acompanha` | `normalize_text_key` + lookup | `Usuario.id` ou `None` |
| `convidados` | split `[;,]` + `normalize_email` | `list[str]` |
| `atualizar`, `cancelar` | `parse_bool_ptbr` | bool — usado para flag warning, não ação |
| `aprovacao_planilha` | `parse_bool_ptbr` | bool — só registra |

---

## 6. Validações antes do upload (PR 6)

### Bloqueantes
- `municipio` não encontrado em `Municipio`.
- `projeto` não encontrado em `Projeto`.
- `formador_1` não encontrado em `Usuario` ou usuário não tem Função `Formador`.
- `hora_fim <= hora_inicio` (RD-01).
- `data` fora de faixa razoável.
- Email inválido em `convidados`.
- `external_hash` duplicado no próprio arquivo.

### Avisos
- `formador_2..5` não encontrado → criar Solicitacao só com formadores válidos.
- `coordenador` não encontrado → deixar `null`, exigir admin completar.
- Linha com `cancelar=true` → **NÃO cancelar**; criar a Solicitacao normal e listar para revisão.
- Linha com `atualizar=true` → **NÃO atualizar** existente; criar uma nova Solicitacao (idempotência via hash decide se duplica).
- `aprovacao_planilha=true` → **NÃO aprovar**; status inicial conforme `Projeto.fluxo`.
- Conflito RD-01..08 detectado (overlap, deslocamento, capacidade) → warning explícito por código (E, T, P, D, M).

### Verificação pós-import (não bloqueante)
- Reservar slot via `availability_service.check_conflicts()` para cada Solicitacao criada e anotar conflitos em `details`.

---

## 7. Regras de duplicidade / hash

### Chave natural — **REAL** (`eventos_import.py:344-365`)

`(municipio_id, projeto_id, tipo_evento_id, data, hora_inicio, hora_fim)`.

**Não inclui formador nem coordenador.** Consequência: duas turmas simultâneas do mesmo
tipo/projeto/município colidem no mesmo hash e a segunda **sobrescreve** a primeira.

### `external_hash` — **SHA-1**, não SHA-256

```text
stable_import_hash(municipio_id, projeto_id, tipo_evento_id,
                   data.isoformat(), hora_inicio "%H:%M", hora_fim "%H:%M")
= sha1("|".join(partes))     # apps/core/imports/hashing.py:37-60
```

SHA-1 é **congelado por ADR-012** (`v2/docs/adr/ADR-012-sha1-idempotency-hashes.md`): migrar para
SHA-256 quebraria os `external_hash` já gravados em `Compra`, `Solicitacao`, `Deslocamento`,
`AcaoControle`, `AcaoDAT` e `Acompanhamento` (`apps/core/imports/hashing.py:4-11`).

### Comportamento por match — pretendido vs **REAL**

As colunas `cancelar` e `atualizar` **não são lidas pelo service**: `_normalize_row`
(`eventos_import.py:159-256`) só reconhece `municipio`, `projeto`, `tipo_evento`, `data`,
`hora_inicio`, `hora_fim`, `coordenador`, `formador1..5`, `encontro`, `segmento` e `local`.
`aprovacao`, `cancelar`, `atualizar`, `coord_acompanha` e `convidados` são **silenciosamente ignoradas**.

| Hash existe no banco | Ação pretendida | Ação **real** (`:523-556`) |
|---|---|---|
| Não | Criar Solicitacao | Cria (`created=True`) |
| Sim | **Ignorar** (idempotente) | 🔴 **`update_or_create` sobrescreve** `usuario`, `coordenador`, `municipio`, `projeto`, `tipo_evento`, `inicio`, `fim`, `status`, `observacoes`, `local`, `encontro`, `segmento` |
| Sim, com `cancelar=true` | Não cancelar; relatar | Coluna ignorada; a linha é aplicada como qualquer outra |
| Sim, com `atualizar=true` | Não atualizar; relatar | Coluna ignorada; **atualiza de qualquer jeito** |
| Sim, e algo mudou | Contar como `updated` | 🔴 Conta como **`unchanged`** — `changed` é calculado após o save (#1628) |

---

## 8. Models / services / endpoints relacionados (estado real do código — 2026-05-05)

| Componente | Caminho | Função | Status |
|---|---|---|---|
| Model `Solicitacao` | `apps/core/models/solicitacao.py` | SSOT do agendamento | ✅ existe |
| Model `Participation` | `apps/core/models/` | M2M Solicitacao ↔ Usuario com role (COORDENADOR/FORMADOR) | ✅ existe |
| Model `Usuario` | `apps/core/models/usuario.py` | Coordenador/Formador FK + M2M | ✅ existe |
| Model `Municipio`, `Projeto`, `TipoEvento` | `apps/core/models/organizacao.py` | FKs | ✅ existe |
| **Service de import** | `apps/core/services/eventos_import.py` | `import_eventos_from_file(*, path: str, dry_run: bool = True) -> dict`. Status inicial vem de `resolve_initial_status(projeto=projeto)` (`:497`) — **só o `fluxo` decide, a data não** (`:23`). Cria 1 `Participation(role='COORDENADOR')` + até 5 `Participation(role='FORMADOR')`. Idempotência por `external_hash` SHA-1. Timezone `America/Fortaleza` (`:55`). | ✅ **já implementado** |
| Resolvers usados | `apps/core/services/resolvers.py` | `resolve_municipio`, `resolve_projeto`, `resolve_tipo_evento`, `resolve_user_by_email`, `resolve_user_by_name` | ✅ existe |
| Service availability | `apps/core/services/availability_service.py:check_conflicts()` | RD-01..08 — 🔴 **não é chamado pelo import.** Nem `availability_service` nem `solicitacao_availability` aparecem nos imports de `eventos_import.py:38-53`. Uma linha `NAO_SUPER` vira solicitação **aprovada** sem passar pelo hard gate — `M08-12` / [#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620) | ✅ existe, ❌ não usado aqui |
| **Endpoint síncrono** | `POST /api/solicitacoes/import/` (`ImportEventosView` em `apps/core/views_import_eventos.py`) | dry_run via query param; multipart `file=` no body | ✅ **já funciona** |
| Endpoint async | (não implementado para eventos) | ASQ-005 Fase 2 migrará | ⏳ Fase 2 do `ImportJob` |
| Gate RBAC efetivo | `IsAuthenticated + HasPerm("import_spreadsheet")` (DAT) | NÃO `manage_admin_registries` — eventos é operacional, não cadastro | ✅ aplicado em prod |
| Endpoint manual (1 a 1) | `POST /api/solicitacoes/` (`SolicitacaoViewSet.create`) | Para criação não-bulk; usa `HasPerm("create_solicitation")` | ✅ existe |
| AuditLog action | **(nenhuma)** | 🔴 O import síncrono **não grava `AuditLog`**. `AuditLog.Action` (`apps/core/models/auditoria.py:72-73`) só tem `IMPORT_JOB_COMPLETED`/`IMPORT_JOB_FAILED`, emitidos no caminho async (`apps/core/tasks.py:634,669`), que hoje cobre apenas `bloqueios` | ❌ não existe |

### Comportamento real do service (lido em código)

- **Idempotência**: `external_hash` **SHA-1** sobre `(municipio_id, projeto_id, tipo_evento_id, data,
  hora_inicio, hora_fim)` (`:344-365`). **Sem coordenador e sem formador na chave.** Re-import com a
  mesma chave **não duplica — mas sobrescreve** (ver §7 e §9).
- **Status inicial** (`:495-497`, docstring `:19-23`):
  - `Projeto.fluxo == 'SUPER'` → `status='pendente'` (aguarda aprovação manual em `/aprovacoes`).
  - `Projeto.fluxo == 'NAO_SUPER'` → `status='aprovado'`.
  - **A data do evento não entra na decisão** — passado e futuro são tratados igual.
- **Participation criada por linha** (`:562-607`): 1 `role='COORDENADOR'` + até 5 `role='FORMADOR'`.
  Reconciliação por email (preferido) ou nome — `_resolve_user` (`:368-380`) cai em
  `resolve_user_by_name`, que faz **fallback por substring** (`icontains`) e resolve ambiguidade com `.first()`
  (`services/resolvers.py:89-131`). Achado `M22-14` /
  [#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643), épico
  [#1658](https://github.com/matheusnorjosa/aprender_sistema/issues/1658) — um homônimo entra na
  agenda da pessoa errada, em silêncio. (O #1613/M02-09 cobriu só projeto/tipo_evento; o residual de
  pessoa segue vivo em #1643.)
- **Timezone**: `ZoneInfo("America/Fortaleza")` (`:55`).
- **Google Calendar**: **NÃO é tocado pelo import** — nenhum client GCal é importado pelo service.
  Publicação só via fluxo manual (preview + publish).

---

## 9. O que pode ser criado/atualizado

### Pode criar
- `Solicitacao` com:
  - `status='pendente'` se `Projeto.fluxo=='SUPER'`.
  - `status='aprovado'` se `Projeto.fluxo=='NAO_SUPER'` — 🔴 **sem passar pelo hard gate de
    disponibilidade** (#1620). A flag `imported_from_sheets` continua sendo apenas uma sugestão;
    não existe no model.
  - `is_online` não é escrito pelo import (fica no default do model — planilha não indica).
  - `gcal_status` / `external_event_id` / `meet_link` não são escritos (ficam nos defaults do model).

### Pode atualizar — 🔴 a v0.2 dizia "nada"; é falso

Em toda linha cujo `external_hash` já exista, `update_or_create` (`eventos_import.py:523-539`)
sobrescreve **11 campos**, incluindo três que carregam decisão humana:

| Campo sobrescrito | Por que importa |
|---|---|
| `status` | **apaga a decisão de aprovação** — uma solicitação reprovada/pendente volta ao valor derivado do `fluxo` |
| `usuario` e `coordenador` | **troca o dono** da solicitação para quem a planilha disser |
| `inicio` / `fim` | **move o evento** sem passar por RD-01..08 |
| `municipio`, `projeto`, `tipo_evento`, `observacoes`, `local`, `encontro`, `segmento` | reescritos com o valor da planilha |

E a resposta reporta isso como **`unchanged`** (`:544-556`), então nem o operador que rodou o
import percebe. Achado `M10-07` / [#1628](https://github.com/matheusnorjosa/aprender_sistema/issues/1628).

---

## 10. O que NÃO deve acontecer automaticamente

> ⚠️ Coluna "Aplicado?" adicionada em 2026-07-24. As linhas ❌ são intenção, não garantia.

| Item | Por quê | Aplicado? |
|---|---|---|
| Publicar no Google Calendar | PA-03: integrações pós-aprovação manual | ✅ sim — nenhum client GCal é importado pelo service |
| Aprovar Solicitacao de fluxo SUPER | PA-01: SUPER nunca auto-aprova | ✅ sim — `resolve_initial_status` devolve `pendente` |
| Aprovar sem checar disponibilidade | RD-01..08 é invariante de domínio | ❌ **não** — `NAO_SUPER` entra `aprovado` sem `check_conflicts` (#1620) |
| Cancelar Solicitacao mesmo com `cancelar=true` | Cancel envolve policy + AuditLog | ✅ na prática — a coluna nem é lida (`:159-256`) |
| Atualizar Solicitacao mesmo com `atualizar=true` | Update precisa passar por RD-01..08 | ❌ **não** — atualiza sempre que o hash bate, independente da coluna (#1628) |
| Criar Usuario novo (Coordenador/Formador inexistente) | Usuários vêm do import #1; agenda só reconcilia | ✅ sim — não resolvido vira `pendencias.usuarios` |
| Criar Municipio/Projeto novo | Cadastros mestres vêm dos passos 3-4 da ordem | ✅ sim — não resolvido vira pendência e a linha é pulada |
| Reconciliar formador para a pessoa errada | Homônimo entra na agenda de terceiro | ❌ **não** — `resolve_user_by_name` usa substring + `.first()` (#1643) |
| Atribuir grupo `Gerente` a usuário | Sensibilidade RBAC | ✅ sim — **neste** import. Ver [usuarios.md](./usuarios.md) §10 para o que acontece no import de usuários |
| Enviar emails para `convidados` | Nenhum side-effect de notificação | ✅ sim — a coluna nem é lida |
| Registrar quem rodou o import | Rastreabilidade | ❌ **não** — nenhum `AuditLog` (§8) |

---

## 11. Como auditar depois

### AuditLog — 🔴 **NÃO EXISTE para este import**

As ações `IMPORT_AGENDA` / `IMPORT_AGENDA_DRY_RUN` **nunca existiram**. `AuditLog.Action`
(`apps/core/models/auditoria.py:72-73`) tem só `IMPORT_JOB_COMPLETED` e `IMPORT_JOB_FAILED`,
emitidos exclusivamente pelo caminho assíncrono (`apps/core/tasks.py:634,669`), hoje limitado a
`bloqueios`. Nenhuma view nem service de import síncrono grava `AuditLog`.

Combinado com o sobrescrito silencioso de §9, isto significa: **um reimport pode apagar uma
decisão de aprovação sem deixar rastro nenhum**. É a razão de #1628 ser P1 e não cosmético.

### Drift check
- Comparar `Solicitacao.objects.filter(created_at__date=<dia>).count()` com `linhas_criadas`.
- Listar Solicitações com `status='pendente'` criadas pelo import — fila de revisão manual.
- Cruzar `external_hash` da Solicitacao com `external_hash` da linha CSV (se persistido em campo dedicado).
- Listar conflitos RD-01..08 detectados durante import e ainda não resolvidos.

### Relatório de revisão manual
Gerar lista de:
- Linhas com `cancelar=true` cujo hash bate com Solicitação existente → para cancelar manualmente.
- Linhas com `atualizar=true` cujo hash bate → para atualizar manualmente.
- Linhas com Coordenador/Formador não encontrado → para reconciliação de usuário.

---

## 12. Riscos identificados

> ⚠️ Coluna "Mitigação" corrigida em 2026-07-24 — três mitigações listadas não existiam.

| Risco | Severidade | Mitigação **real hoje** |
|---|---|---|
| **Publicação automática em GCal** | Crítica | ✅ Mitigado — o service não importa nenhum client GCal |
| **Aprovação automática de fluxo SUPER** | Crítica | ✅ Mitigado — `resolve_initial_status` devolve `pendente` (`:497`) |
| **Aprovação de `NAO_SUPER` sem hard gate de disponibilidade** | **P1 vivo** | ❌ **Nenhuma** — [#1620](https://github.com/matheusnorjosa/aprender_sistema/issues/1620) |
| **Update automático sobrescrevendo decisões, owner e datas** | **P1 vivo** | ❌ **Nenhuma** — e ainda reporta `unchanged` ([#1628](https://github.com/matheusnorjosa/aprender_sistema/issues/1628)) |
| **Match errado de Formador/Coordenador por nome (homônimos)** | **P1 vivo** | ❌ **Nenhuma** — substring + `.first()` (`resolvers.py:89-131`), [#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643) |
| Colisão de hash entre turmas simultâneas | Alta | ❌ Nenhuma — a chave não inclui formador nem coordenador (§7) |
| Cancel automático destruindo dados | Alta | ✅ Na prática — a coluna `cancelar` não é lida |
| **Apply sem rastro de auditoria** | Alta | ❌ **Nenhuma** — não há `AuditLog` (§11) |
| `data + hora_inicio` em timezone errado (cliente assumindo UTC) | Alta | Sempre assumir Fortaleza local na planilha; converter ao salvar |
| `hora_fim` no dia seguinte (evento atravessa meia-noite) | Média | Detectar se hora_fim < hora_inicio → assumir +1 dia (com warning) |
| Convidado com email inválido | Baixa | Bloqueante por linha (rejeitar Convidado); criar Solicitacao sem ele |
| Encontro/segmento com semântica de domínio (mapeamento) | Média | Texto livre por enquanto; futura tabela auxiliar |
| Conflitos RD-01..08 silenciados | Média | Anotar em `details`; expor relatório pós-import |

---

## 13. Pendências para Matheus

1. **Semântica de coluna `e`**: o que significa? Provavelmente flag de "encontrado/exportado" — confirmar antes de ignorar.
2. **`tipo` aceitos**: enum fechado? Quais valores válidos? Hoje o sistema tem campos como `tipo_evento` (não confirmei o nome exato no model).
3. **Online vs presencial**: a planilha tem coluna para indicar evento online? Hoje `Solicitacao.is_online` afeta geração de Meet link.
4. **Reconciliação de Formador por nome**: planilha tem CPF/email do formador ou só nome? Se só nome, política para homônimos.
5. **`aprovacao_planilha=true` em projetos NAO_SUPER**: aceitar como sinal de que a linha está validada (e refletir em `status='aprovado'`) ou ignorar?
6. **`cancelar=true` e `atualizar=true`**: a planilha quer dar uma "instrução" ao sistema. Política definitiva — gerar issue de revisão automaticamente? Mandar email ao admin?
7. **Convidados**: emails listados em `Convidados` viram `extra_participants` na Solicitacao ou vão direto pro `attendees` do GCal (quando publicado)?
8. **`segmento`**: existe tabela `Segmento` no schema? Se sim, lookup; senão, texto livre.
9. **Conflitos RD-08 (descrição clara dos códigos)**: para cada conflito detectado, gerar email/notificação ao coordenador responsável?

---

## 14. Histórico de versões

- 2026-05-05 — v0.1 — PR 1 (contrato inicial). Gates contra GCal automático, aprovação automática, cancel automático.
- 2026-05-05 — v0.2 — Auditoria contra código; service confirmado implementado.
- 2026-07-24 — v0.3 — Varredura de docs pós-auditoria M00–M28. Corrigidas três afirmações falsas:
  (1) a data do evento **não** decide o status; (2) o import grava `aprovado` sem hard gate de
  disponibilidade (#1620); (3) reimport **sobrescreve** status/owner/datas e reporta `unchanged`
  (#1628). Corrigidos também o algoritmo do hash (SHA-1, não SHA-256), a composição da chave
  natural, a resolução por nome com substring (#1613) e a ausência total de `AuditLog`.
