# Importação: Agenda / Solicitações / Eventos

Status: PR 1 — contrato fechado, **backend já implementado** com regras PA-01 ativas (revisto 2026-05-05)
Versão: 2026-05-05 v0.2
Template: [templates/agenda_solicitacoes.template.csv](./templates/agenda_solicitacoes.template.csv)

> ⚠️ **Atualização v0.2**: a v0.1 tratava o service como "futuro". Na verdade `apps/core/services/eventos_import.py` já existe e funciona com PA-01 aplicado (SUPER + data futura → `pendente`), criação de `Participation` M2M (coordenador + formadores 1..5) e idempotência via `external_hash`. Endpoint funcional: `POST /api/solicitacoes/import/`.

---

## 1. Objetivo

Importar registros de agendamento de eventos pedagógicos (formações, acompanhamentos, provas) a partir da aba de "Agenda" da planilha `sheets.banco`. Alimenta `apps.core.models.solicitacao.Solicitacao`.

Cobre:
- Criação de `Solicitacao` em status correto (PA-01).
- Lookup de Municipio, Projeto, Coordenador, Formadores.
- Validação de horários (RD-06 timezone Fortaleza, fim > início).
- Idempotência via `external_hash`.

NÃO cobre (crítico):
- **Publicação no Google Calendar** (RF05/RF06) — só após aprovação manual (PA-03).
- **Aprovação automática** — se `projeto.fluxo=="SUPER"`, status inicial é `pendente`.
- **Atualização/cancelamento** de Solicitacao existente automaticamente — exige revisão humana.

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

### Chave natural
Composta: `(data, hora_inicio, projeto, municipio, formador_primary)`.

### `external_hash`

SHA256 sobre:
```text
data.isoformat() + "|" + hora_inicio.strftime("%H:%M") + "|" + hora_fim.strftime("%H:%M") + "|"
  + str(projeto.id) + "|" + str(municipio.id) + "|" + str(formador_primary.id)
```

`formador_primary` é o primeiro formador não-vazio (`formador_1` ou primeiro preenchido).

### Comportamento por match
| Hash existe no banco | Linha vem com `cancelar=true` | Linha vem com `atualizar=true` | Ação |
|---|---|---|---|
| Não | Não | Não | Criar Solicitacao |
| Não | Sim | — | **Warning crítico** — pediu para cancelar algo que não existe |
| Não | — | Sim | Criar (com warning informando que `atualizar` veio em hash novo) |
| Sim | Não | Não | Ignorar (idempotente); registrar em AuditLog |
| Sim | Sim | — | **Não cancelar**; gerar relatório de revisão manual |
| Sim | — | Sim | **Não atualizar**; gerar relatório de revisão manual |

---

## 8. Models / services / endpoints relacionados (estado real do código — 2026-05-05)

| Componente | Caminho | Função | Status |
|---|---|---|---|
| Model `Solicitacao` | `apps/core/models/solicitacao.py` | SSOT do agendamento | ✅ existe |
| Model `Participation` | `apps/core/models/` | M2M Solicitacao ↔ Usuario com role (COORDENADOR/FORMADOR) | ✅ existe |
| Model `Usuario` | `apps/core/models/usuario.py` | Coordenador/Formador FK + M2M | ✅ existe |
| Model `Municipio`, `Projeto`, `TipoEvento` | `apps/core/models/organizacao.py` | FKs | ✅ existe |
| **Service de import** | `apps/core/services/eventos_import.py` | `import_eventos_from_file(path: str, dry_run: bool = True) -> dict`. Aplica PA-01 (`Projeto.fluxo=='SUPER'` + data futura → `status='pendente'`; senão `'aprovado'`). Cria 1 `Participation(role='COORDENADOR')` + até 5 `Participation(role='FORMADOR')`. Idempotência por `external_hash`. Timezone fixado em `America/Fortaleza` (linha 51). | ✅ **já implementado** |
| Resolvers usados | `apps/core/services/resolvers.py` | `resolve_municipio`, `resolve_projeto`, `resolve_tipo_evento`, `resolve_user_by_email`, `resolve_user_by_name` | ✅ existe |
| Service availability | `apps/core/services/availability_service.py:check_conflicts()` | RD-01..08 — **não é chamado pelo import** (linhas importadas entram diretamente sem check) | ✅ existe |
| **Endpoint síncrono** | `POST /api/solicitacoes/import/` (`ImportEventosView` em `apps/core/views_import_eventos.py`) | dry_run via query param; multipart `file=` no body | ✅ **já funciona** |
| Endpoint async | (não implementado para eventos) | ASQ-005 Fase 2 migrará | ⏳ Fase 2 do `ImportJob` |
| Gate RBAC efetivo | `IsAuthenticated + HasPerm("import_spreadsheet")` (DAT) | NÃO `manage_admin_registries` — eventos é operacional, não cadastro | ✅ aplicado em prod |
| Endpoint manual (1 a 1) | `POST /api/solicitacoes/` (`SolicitacaoViewSet.create`) | Para criação não-bulk; usa `HasPerm("create_solicitation")` | ✅ existe |
| AuditLog action | (registrado pelo service durante apply — não confirmado nome exato) | rastreio | ⚠️ verificar |

### Comportamento real do service (lido em código + docstring)

- **Idempotência**: `external_hash` SHA-? sobre tupla natural (municipio + projeto + tipo + data + hora_inicio + coordenador). Re-import com mesma chave **não duplica**.
- **PA-01 aplicada automaticamente** (linhas 19-22 do docstring):
  - `Projeto.fluxo == 'SUPER'` **e** `data >= hoje` → `status='pendente'` (aguarda aprovação manual em `/aprovacoes`).
  - `Projeto.fluxo == 'NAO_SUPER'` **OU** `data < hoje` → `status='aprovado'`.
- **Participation criada por linha** (linhas 22-23): 1 `role='COORDENADOR'` + até 5 `role='FORMADOR'`. Reconciliação por email (preferido) ou nome (fallback heurístico via `resolve_user_by_name`).
- **Timezone**: `ZoneInfo("America/Fortaleza")` (linha 51 do service).
- **Google Calendar**: **NÃO é tocado pelo import** — `external_event_id` fica `None`, `gcal_status` permanece `NONE`. Publicação só via fluxo manual (preview + publish, gate `CanAccessSolicitationApprovals`).

---

## 9. O que pode ser criado/atualizado

### Pode criar
- `Solicitacao` com:
  - `status='pendente'` se `Projeto.fluxo=='SUPER'`.
  - `status='aprovado'` se `Projeto.fluxo=='NAO_SUPER'` (auto-approve PR18) — **com flag `imported_from_sheets=True`** sugerido para PR futura.
  - `is_online=False` por default (planilha não indica online/presencial — pendência).
  - `gcal_status='NONE'` (não publicar).
  - `external_event_id=None` (não vincular a evento GCal existente).
  - `meet_link=None`.

### Pode atualizar
- **Nada** automaticamente. Linhas com hash existente são ignoradas (idempotência).
- Atualizações reais exigem fluxo manual no frontend (`/solicitacoes/{id}/editar`).

---

## 10. O que NÃO deve acontecer automaticamente

| Item | Por quê |
|---|---|
| Publicar no Google Calendar | PA-03: integrações pós-aprovação manual |
| Aprovar Solicitacao mesmo com `aprovacao_planilha=true` | PA-01: SUPER nunca auto-aprova (PR18 só aplica a NAO_SUPER) |
| Cancelar Solicitacao mesmo com `cancelar=true` | Cancel envolve `cancel_gcal` policy + AuditLog; precisa fluxo manual |
| Atualizar Solicitacao mesmo com `atualizar=true` | Update precisa passar por validação RD-01..08 atualizada |
| Criar Usuario novo (Coordenador/Formador inexistente) | Usuários vêm do import #1; agenda só **reconcilia** |
| Criar Municipio/Projeto novo | Cadastros mestres vêm dos passos 3-4 da ordem |
| Atribuir grupo `Gerente` a usuário | Sensibilidade RBAC — admin manual |
| Enviar emails para `convidados` | Nenhum side-effect de notificação |

---

## 11. Como auditar depois

### AuditLog
```python
AuditLog.objects.filter(
    action__in=["IMPORT_AGENDA", "IMPORT_AGENDA_DRY_RUN"],
    created_at__gte=<timestamp>
).values(
    "usuario", "details__arquivo_hash",
    "details__linhas_criadas",
    "details__linhas_ignoradas",
    "details__linhas_rejeitadas",
    "details__cancelar_ignorados",   # linhas com flag cancelar=true não-executadas
    "details__atualizar_ignorados",  # linhas com flag atualizar=true não-executadas
    "details__conflitos_rd",         # contagem de conflitos RD anotados
)
```

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

| Risco | Severidade | Mitigação |
|---|---|---|
| **Publicação automática em GCal** | **Crítica** | Hard gate: `gcal_status='NONE'`, `external_event_id=None`; nenhum task Celery disparado |
| **Aprovação automática SUPER** | **Crítica** | PA-01: status `pendente` quando `Projeto.fluxo=="SUPER"`, ignora `aprovacao_planilha` |
| Cancel automático destruindo dados | Alta | NÃO cancelar; só relatar |
| Update automático sobrescrevendo decisões | Alta | NÃO atualizar; só relatar |
| Match errado de Formador por nome (homônimos) | Alta | Pendência: usar CPF/email se vier; senão warning explícito |
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
