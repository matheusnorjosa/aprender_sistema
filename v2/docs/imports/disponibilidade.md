# Importação: Disponibilidade / Bloqueios

Status: PR 1 — **backend implementado para tipos T/P; tipo D e recorrência ainda em aberto** (revisto 2026-10-19)
Versão: 2026-10-19 v0.4
Template: [templates/disponibilidade.template.csv](./templates/disponibilidade.template.csv)

> 🟢 **Atualização v0.4 (2026-10-19) — achado `M22-14`, issue
> [#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643) (épico
> [#1658](https://github.com/matheusnorjosa/aprender_sistema/issues/1658)).**
>
> A v0.3 (2026-07-24) descrevia três comportamentos que, juntos, faziam o import **criar um
> bloqueio auto-aprovado na agenda da pessoa errada, em silêncio**: fallback por substring +
> `.first()` em `resolve_user_by_name`, `created_by` não gravado e nenhum `AuditLog`. Isso foi
> corrigido:
>
> 1. **Homônimo não vira chute (#1929).** `resolve_user_by_name` (`services/resolvers.py`) exige
>    candidato único — nome completo exato, depois todos os tokens do nome. Ambiguidade devolve
>    `None` + WARNING e a linha vira pendência `usuarios`.
> 2. **Autor e auditoria (#2011).** `import_bloqueios_from_file(..., actor=...)` grava
>    `created_by=actor` e um `AuditLog` `DELEGATE_BLOCK_CREATE` (`origem=import`) por bloco criado.
>    As duas rotas passam o ator (`request.user` na síncrona, `job.user` no `ImportJob`), e ambas são
>    `SuperuserOnly`.
> 3. **Alvo precisa ser Formador ativo (#2016)** para bloqueio com início a partir de 31/07/2026
>    (`_FORMADOR_CUTOFF` / `_is_active_formador` em `bloqueios_import.py`); antes disso é dado
>    histórico e aceita qualquer usuário.
>
> **Residual:** a pendência `usuarios` não distingue ambíguo de não encontrado; `status="aprovado"`
> segue incondicional; `tipo` inválido é coagido para `T`; bloqueios importados antes do #2011 têm
> `created_by` nulo. SSOT: `bloqueios_import.py` e `resolvers.py`. Ver
> [../audits/ACHADOS_REAIS.md](../audits/ACHADOS_REAIS.md).

> ⚠️ **Atualização v0.2**: a v0.1 tratava o formato como totalmente pendente. Verificação contra o código mostra que `apps/core/services/bloqueios_import.py` já existe e funciona para tipos **T** (total) e **P** (parcial), com endpoint síncrono `POST /api/disponibilidade/import-bloqueios/` **e** endpoint assíncrono `POST /api/imports/bloqueios/` (ASQ-005 Fase 1 — `bloqueios` é o piloto). Tipo **D** (deslocamento) e bloqueios **recorrentes** continuam em aberto.

---

## 1. Objetivo

Importar bloqueios de disponibilidade de formadores e coordenadores a partir de aba apropriada da planilha `sheets.banco` (nome exato a confirmar). Alimenta `apps.core.models.agenda.AvailabilityBlock`.

Cobre (proposta):
- Criação de bloqueio Total (T), Parcial (P) ou Deslocamento (D).
- Reconciliação de Usuário (formador/coordenador).
- Idempotência via `external_hash`.

---

## 2. Status do contrato (revisto 2026-05-05)

O backend de import de bloqueios **já existe e funciona** para tipos **T** (Total) e **P** (Parcial). O service `bloqueios_import.py` aceita o cabeçalho:

```text
usuario,inicio,fim,tipo,motivo
```

(docstring linhas 6-12). Reconciliação de `usuario` é por **nome** via `resolve_user_by_name` — vulnerável a homônimos; preferência por email/CPF ainda é pendência.

Tipo **D** (Deslocamento) **não está no service de bloqueios**: hoje o service `apps/core/services/availability_service.py:check_conflicts()` **calcula** D dinamicamente (RD-04 buffer entre municípios diferentes). Importar D explícito da planilha exigiria mudança de runtime.

Códigos do sistema:
- **T** (Total), **P** (Parcial) — armazenados em `AvailabilityBlock.tipo`.
- **D** (Deslocamento) — derivado, não armazenado como bloqueio.
- **M** (Capacidade), **X** (Evento+Bloqueio) — códigos de **conflito retornado por check_conflicts**, não tipos de bloqueio.

Pendências reais nesta dimensão: importar **D** explícito (decisão), suporte a **recorrência** (não há campo no model), identificador robusto (CPF/email em vez de nome).

---

## 3. Dados de origem esperados (proposta)

| Coluna planilha | Descrição | Confirmado? |
|---|---|---|
| `Usuario` (nome ou email ou CPF) | Identificador do formador/coordenador | ❌ Pendência |
| `Tipo` (T/P/D) | Total / Parcial / Deslocamento | ❌ Pendência |
| `Data inicio` | Data inicial (BR `dd/mm/yyyy`) | Proposta |
| `Data fim` | Data final | Proposta |
| `Hora inicio` (se parcial) | Hora de início | Proposta |
| `Hora fim` (se parcial) | Hora de fim | Proposta |
| `Cidade origem` (se deslocamento) | Município de origem | Proposta |
| `Cidade destino` (se deslocamento) | Município de destino | Proposta |
| `Motivo` | Texto livre | Proposta |

---

## 4. Colunas obrigatórias (proposta)

| Coluna CSV | Validação |
|---|---|
| `usuario` | Lookup `Usuario`; deve existir; deve ter Função `Formador` ou `Coordenador` |
| `tipo` | Enum `{T, P, D}` |
| `data_inicio` | Data BR válida |
| `data_fim` | Data BR válida; >= `data_inicio` |

---

## 5. Colunas opcionais (proposta)

| Coluna CSV | Comportamento se vazio |
|---|---|
| `hora_inicio` | Obrigatório se `tipo==P`; senão default 00:00 |
| `hora_fim` | Obrigatório se `tipo==P`; senão default 23:59 |
| `cidade_origem`, `cidade_destino` | Obrigatórios se `tipo==D`; senão ignorar |
| `motivo` | string vazia se vazio |

---

## 6. Normalizações esperadas (PR 2)

| Campo | Função (futura) | Resultado |
|---|---|---|
| `usuario` | `normalize_text_key` + lookup | `Usuario.id` |
| `tipo` | upper + validate enum | `T`/`P`/`D` |
| `data_inicio`, `data_fim` | `parse_br_date` | `date` |
| `hora_inicio`, `hora_fim` | `parse_br_time` | `time` |
| `data + hora` → `inicio`/`fim` | `make_aware(tz=America/Fortaleza)` | `datetime` UTC armazenado |
| `cidade_*` | `normalize_municipio_uf` ou lookup `Municipio` | FK Municipio (futuro) ou texto |
| `motivo` | strip | string |

---

## 7. Validações antes do upload (PR 6, proposta)

### Bloqueantes
- `usuario` não encontrado.
- `tipo` fora de `{T, P, D}`.
- `data_fim < data_inicio`.
- `tipo==P` mas `hora_inicio` e/ou `hora_fim` vazios.
- `tipo==D` mas `cidade_origem` e/ou `cidade_destino` vazios.
- `tipo==D` e `cidade_origem == cidade_destino` (não há deslocamento real).
- `external_hash` duplicado no próprio arquivo.

### Avisos
- `data_inicio` no passado → criar (histórico) com warning.
- `data_inicio` muito no futuro (> 1 ano) → warning.
- Sobreposição com outro bloqueio do mesmo usuário → criar (RD-02/03 permite múltiplos blocos) com warning.

---

## 8. Regras de duplicidade / hash (proposta)

### Chave natural — **REAL**
`(usuario, inicio, fim, tipo)`, aplicada como filtro direto no ORM (`bloqueios_import.py`,
`_process_row`): `AvailabilityBlock.objects.filter(usuario=..., inicio=..., fim=..., tipo=...).first()`.

### `external_hash` — **NÃO EXISTE neste import**

Apesar da docstring do módulo dizer "dry_run + external_hash para idempotencia"
(`bloqueios_import.py:4` — o comentário está errado), **o service não calcula hash nenhum**.
A idempotência é o filtro pela tupla natural acima. Não há SHA-256 (nem SHA-1) aqui.

### Comportamento por match — **REAL**
| Chave natural existe | Ação real |
|---|---|
| Não | Cria `AvailabilityBlock` com `status="aprovado"` |
| Sim, e `motivo` mudou (e não é vazio) | **Atualiza `motivo`** → `stats.updated` |
| Sim, sem mudança de `motivo` | `stats.unchanged` |

Observações de comportamento que o contrato original não previa:
- **`fim` à meia-noite é reescrito** para `23:59:59` antes da comparação — logo, o mesmo dia
  informado como `01/08` e como `01/08 00:00` produzem a **mesma** chave.
- **`tipo` inválido não é rejeitado.** Qualquer valor que não contenha `"parcial"` nem seja `"p"`
  vira **`T` (Total)** em silêncio; coluna ausente também vira `T`. A validação `tipo ∈ {T,P,D}`
  proposta em §7 **não existe**.

---

## 9. Models / services / endpoints relacionados (estado real do código — 2026-05-05)

| Componente | Caminho | Função | Status |
|---|---|---|---|
| Model `AvailabilityBlock` | `apps/core/models/agenda.py` | `tipo` (T/P — não D), `inicio`, `fim`, `usuario`, `motivo`, `status`, **`created_by`** (PR 13) | ✅ existe |
| ViewSet (CRUD) | `views_availability.AvailabilityBlockViewSet` | CRUD; `POST` permite delegação via helper `user_can_delegate_availability_block` (PR 13) | ✅ existe |
| **Service de import** | `apps/core/services/bloqueios_import.py` | `import_bloqueios_from_file(*, path: str, dry_run: bool = True, actor=None) -> dict` (`actor` desde o #2011). Cabeçalho: `usuario,inicio,fim,tipo,motivo`. Reconciliação de `usuario` via `resolve_user_by_name` (linha 28 do service). Timezone `America/Fortaleza` (linha 30). | ✅ **já implementado** |
| Service `check_conflicts` | `apps/core/services/availability_service.py` | RD-01..08 (consome bloqueios — não é o service de import). **Calcula D dinamicamente** entre Solicitações em municípios diferentes; D não é armazenado como bloqueio. | ✅ existe |
| **Endpoint síncrono** | `POST /api/disponibilidade/import-bloqueios/` (`ImportBloqueiosView` em `apps/core/views_import_bloqueios.py`) | dry_run + multipart `file=` | ✅ **já funciona** |
| **Endpoint assíncrono (ASQ-005 Fase 1 — piloto)** | `POST /api/imports/bloqueios/` → cria `ImportJob`, retorna `202 Accepted` | Despacha Celery task `task_run_import_job`. Job persiste com `import_type='bloqueios'`. Status acompanhado via `GET /api/imports/<id>/`. | ✅ **já funciona** (único tipo async hoje) |
| Endpoint async (status) | `GET /api/imports/<id>/` | Retorna `ImportJob` serializado (status, stats, pendencias) | ✅ existe |
| Endpoint async (lista) | `GET /api/imports/` | Lista jobs do usuário (filtro `type=` `status=`) | ✅ existe |
| Gate RBAC (endpoint sync) | `IsAuthenticated + SuperuserOnly` (D20) | Só superusuário (decisão do dono 02/10/2026); nenhuma capability abre. A policy `import_availability_blocks` é apenas para exposição via `/api/me/policies/` | ✅ aplicado |
| Gate RBAC (endpoint async upload) | `IsAuthenticated + SuperuserOnly` (D20) | `apps/core/views/imports.py`; `CanImportGenericSpreadsheet` segue em `policies.py`, mas não gateia mais esta rota | ✅ aplicado |
| AuditLog delegação | `DELEGATE_BLOCK_CREATE` (PR 13) | Quando outro user cria bloqueio em nome de Formador: POST manual e, desde o #2011, também o import (`details.origem="import"`, ator = quem rodou) | ✅ existe |

### Comportamento real do service (lido em código + docstring)

- **Cabeçalho aceito** (docstring linhas 6-12 de `bloqueios_import.py`):
  - `usuario` (obrigatório, nome do formador)
  - `inicio` (obrigatório, datetime)
  - `fim` (obrigatório, datetime > inicio)
  - `tipo` (obrigatório, **T=Total** ou **P=Parcial**; **D não suportado**)
  - `motivo` (opcional)
- **Reconciliação**: `resolve_user_by_name(name)` (`services/resolvers.py`) exige candidato único
  (#1929): (1) nome completo exato; (2) todos os tokens do nome presentes no nome do usuário.
  Comparação acento/caixa-insensível. 2+ candidatos → `None` + WARNING → pendência `usuarios`
  (a pendência não diz se foi ambíguo ou não encontrado). A partir de 31/07/2026 (data do
  bloqueio), o alvo também precisa ser **Formador ativo** (#2016, `_is_active_formador`), senão
  pendência. Achado `M22-14` / [#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643).
  *(Até o #1929 havia três tentativas frouxas por `icontains` + `.first()`, sem detectar ambiguidade.)*
- **Timezone**: `ZoneInfo("America/Fortaleza")` fixo (`bloqueios_import.py:30`).
- **Idempotência**: tupla natural `(usuario, inicio, fim, tipo)`. **Não há `external_hash`** — ver §8.
- **`created_by`**: ✅ gravado com o ator do import desde o #2011 (`created_by=actor`), mais um
  `AuditLog` `DELEGATE_BLOCK_CREATE` por bloco criado (§12). Chamada sem ator (legada) e bloqueios
  importados antes do #2011 ficam com `created_by` nulo.
- **`status`**: 🔴 **`"aprovado"` incondicional**, com o comentário `# Auto-aprovado` no código.
  O formador alvo não revisa e não é notificado.

---

## 10. O que pode ser criado/atualizado

### Pode criar — **REAL**
- `AvailabilityBlock` com:
  - `usuario` = o candidato único que `resolve_user_by_name` devolver (#1929); homônimo vira pendência.
    A partir de 31/07/2026, só Formador ativo (#2016).
  - `status='aprovado'` — auto-aprovado, mas **não** "declarado pelo próprio": quem declara é o
    operador do import, não o formador.
  - `tipo` (coerção silenciosa para `T` se não for parcial), `inicio`, `fim`, `motivo`.
  - ✅ `created_by` = ator do import (#2011).

### Pode atualizar — **REAL**
- `motivo`, quando a chave natural já existe e o novo motivo é não-vazio e diferente.
- Nada além disso. (A v0.2 dizia "nada"; era quase certo, faltava o `motivo`.)

---

## 11. O que NÃO deve acontecer automaticamente

> ⚠️ Coluna "Aplicado?" adicionada em 2026-07-24.

| Regra pretendida | Aplicada? | Prova |
|---|---|---|
| Não deletar bloqueios ausentes da planilha (import é additive) | ✅ sim | o service só faz `create`/`save(update_fields=["motivo"])` |
| Não criar bloqueio para quem não é Formador | ✅ a partir de 31/07/2026 | `_is_active_formador` (#2016): bloqueio com início desde o cutoff exige Formador ativo; antes é histórico e aceita qualquer usuário |
| Não criar bloqueio na agenda da pessoa errada | ✅ sim | `resolve_user_by_name` exige candidato único; homônimo → pendência `usuarios` (#1929) |
| Timezone sempre via America/Fortaleza | ✅ sim | `TZ = ZoneInfo("America/Fortaleza")` (`:30`), aplicado em `_parse_datetime_flexible` |
| Não notificar usuário nem Controle | ✅ sim | nenhum envio no service — mas isso é o que **esconde** o bloqueio errado do formador |
| Não mover/cancelar Solicitação conflitante | ✅ sim | o service não toca em `Solicitacao` |
| Registrar quem criou o bloqueio | ✅ sim | `created_by=actor` + `AuditLog` `DELEGATE_BLOCK_CREATE` (#2011, §12) |

---

## 12. Como auditar depois

### AuditLog — depende do caminho usado

| Caminho | Grava `AuditLog`? |
|---|---|
| `POST /api/disponibilidade/import-bloqueios/` (síncrono) | ✅ por bloco — `DELEGATE_BLOCK_CREATE` (`origem=import`) para cada bloqueio criado (#2011); não há ação de resumo do import |
| `POST /api/imports/bloqueios/` (assíncrono, `ImportJob`) | ✅ sim — `IMPORT_JOB_COMPLETED` / `IMPORT_JOB_FAILED` (`apps/core/tasks.py`) + `DELEGATE_BLOCK_CREATE` por bloco (ator = `job.user`) |

Filtrar `AuditLog` por `action="DELEGATE_BLOCK_CREATE"` e `details__origem="import"` lista os
bloqueios criados por import, com `target_user_id`, `block_id`, `inicio` e `fim`.

### Drift check
- Comparar `AvailabilityBlock.objects.filter(created_at__date=<dia>).count()` com `linhas_criadas`.
- Listar formadores com bloqueio `>= 90 dias` no horizonte (possível erro de planilha).
- Cruzar bloqueios com Solicitações existentes para detectar conflitos pré-existentes.

### Relatório de conflitos pós-import
Listar Solicitações `status='aprovado'` que após o import passam a colidir com bloqueio T/P/D → fila de revisão.

---

## 13. Riscos identificados

> ⚠️ Coluna "Mitigação" corrigida em 2026-07-24 — várias descreviam mitigações inexistentes.

| Risco | Severidade | Mitigação **real hoje** |
|---|---|---|
| **Match errado de Usuario por nome** (bloqueio na agenda de terceiro) | ✅ Mitigado | **#1929** — candidato único; ambiguidade → `None` + WARNING → pendência `usuarios`. Residual: a pendência não distingue ambíguo de não encontrado. [#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643) |
| **Bloqueio auto-aprovado sem autor e sem auditoria** | Média (residual) | ✅ autor + auditoria (**#2011**: `created_by=actor` + `DELEGATE_BLOCK_CREATE`). Segue `status="aprovado"` incondicional; bloqueios anteriores ao #2011 têm `created_by` nulo |
| `tipo` inválido vira `T` (Total) em silêncio | Alta | ❌ Nenhuma — coerção sem pendência (ver §8) |
| Bloqueio em horário UTC errado | Alta | ✅ Mitigado — `TZ` fixo em `America/Fortaleza` (`:30`) |
| Usuario inexistente | Alta | ✅ Mitigado — linha vira `pendencias.usuarios` e é pulada |
| Bloqueio T sobrescrevendo Solicitacao já aprovada | Alta | ✅ Mitigado — o service não toca em `Solicitacao` |
| Bloqueio para quem não é Formador | Média | ✅ a partir de 31/07/2026 — `_is_active_formador` (#2016); antes do cutoff é histórico e aceita qualquer usuário |
| Deslocamento sem origem/destino | Média | Não se aplica — tipo D não é suportado (§2) |
| Lapso de timezone em sync internacional | Baixa | Documentar TZ no template |

---

## 14. Pendências para Matheus (revistas)

### Resolvidas pelo código atual

- ~~Formato definitivo da planilha?~~ → **Resolvido em parte**: `bloqueios_import.py` aceita `usuario,inicio,fim,tipo,motivo`. Falta só confirmar se esse cabeçalho bate com o que `sheets.banco` vai produzir.
- ~~Existe service?~~ → Sim, há ~6 meses no código.
- ~~Existe dry-run?~~ → Sim, todos os services aceitam `dry_run=True`.
- ~~`ImportBatch` para auditoria?~~ → Já existe `ImportJob` (`apps/core/models/import_job.py`) com piloto em `bloqueios`.

### Pendências reais ainda

1. **Identificador do Usuário (#1643).** A parte **(b)** da correção (épico
   [#1658](https://github.com/matheusnorjosa/aprender_sistema/issues/1658)) — **rejeitar
   ambiguidade** em vez de escolher — entrou no #1929: 2+ candidatos viram pendência. Falta
   **(a)** aceitar CPF/email como identificador e distinguir, na pendência, ambíguo de não
   encontrado.
2. **Tipo D (Deslocamento)**: hoje **não suportado** como bloqueio. Deslocamentos são calculados dinamicamente por `availability_service` entre Solicitações de municípios diferentes. Se `sheets.banco` traz D explícito, precisa decidir:
   - (a) ignorar coluna D na importação (manter cálculo dinâmico);
   - (b) estender model `AvailabilityBlock` para aceitar D (mudança de schema);
   - (c) criar model separado `AvailabilityTravel` para deslocamentos declarados.
3. **Bloqueios recorrentes** (toda quarta, todo mês 25): **não há campo de recorrência no model atual**. Importar exige:
   - (a) pré-expandir em N linhas (responsabilidade do `sheets.banco`);
   - (b) ampliar model com `RRULE`/RFC 5545 (mudança grande de runtime).
4. **Política de re-import**: ✅ **verificado** — a chave natural existente só faz o service
   atualizar `motivo`; o resto é ignorado. Se a regra desejada for **substituir** todos os
   bloqueios do usuário no período, exige PR de runtime.
5. **Status inicial**: ✅ **verificado** — o service cria com `status='aprovado'` incondicional.
   Decisão pendente: manter auto-aprovado (fonte oficial) ou passar a `pendente` para revisão do
   formador. (Com o match por candidato único do #1929, homônimo não chega a criar bloqueio; o risco que sobra é o degrau por tokens casar um único usuário que não é a pessoa da planilha.)
6. ~~**`created_by` vazio**~~ → **Resolvido no #2011**: o import grava o operador em `created_by` e
   um `AuditLog` `DELEGATE_BLOCK_CREATE`. Resta o passivo de bloqueios importados antes disso, com
   `created_by` nulo.
7. **Cancelar bloqueios**: planilha tem coluna `cancelar`? Hoje import é additive (não remove). Se for necessário cancelar via planilha, exige PR de runtime + soft-delete no model.
8. **`deslocamentos_import.py`**: confirmar se esse serviço (que existe, com rota
   `deslocamentos/import/` → `ImportDeslocamentosView` em `apps/core/urls.py:76,235-236`) cobre o
   caso de import de deslocamentos como dado independente de bloqueio.
   *(O target `make etl-desloc-dry` citado na v0.2 **não existe** — o ETL legado foi removido.)*

---

## 15. Histórico de versões

- 2026-05-05 — v0.1 — PR 1 (proposta inicial). Tratava formato como totalmente pendente.
- 2026-05-05 — v0.2 — Auditoria contra código real. **`bloqueios_import.py` confirmado funcional** para T/P + endpoint sync **e** async (ASQ-005 piloto). Pendências reorientadas: identificador robusto, tipo D, recorrência continuam abertas.
- 2026-07-24 — v0.3 — Varredura de docs pós-auditoria M00–M28. Registrado `M22-14` / #1643
  (resolução por substring cria bloqueio auto-aprovado na agenda errada). Corrigidos: não existe
  `external_hash` neste import; `created_by` **não** é gravado; `tipo` inválido é coagido para `T`;
  `fim` à meia-noite vira `23:59:59`; o reimport atualiza `motivo`; e o caminho síncrono não grava
  `AuditLog` (só o assíncrono grava).
- 2026-10-19 — v0.4 — Registrado o que fechou o `M22-14`: candidato único em `resolve_user_by_name`
  (#1929), `created_by=actor` + `AuditLog` `DELEGATE_BLOCK_CREATE` nas duas rotas (#2011) e alvo
  Formador ativo a partir de 31/07/2026 (#2016). Residual listado no topo.
