# Importação: Disponibilidade / Bloqueios

Status: PR 1 — **backend implementado para tipos T/P; tipo D e recorrência ainda em aberto** (revisto 2026-05-05)
Versão: 2026-05-05 v0.2
Template: [templates/disponibilidade.template.csv](./templates/disponibilidade.template.csv)

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

### Chave natural
`(usuario.id, tipo, inicio, fim)`.

### `external_hash`
SHA256 sobre:
```text
str(usuario.id) + "|" + tipo + "|" + inicio.isoformat() + "|" + fim.isoformat()
```

### Comportamento por match
| Hash existe | Ação |
|---|---|
| Não | Criar `AvailabilityBlock` |
| Sim | Ignorar (idempotente) com log |

---

## 9. Models / services / endpoints relacionados (estado real do código — 2026-05-05)

| Componente | Caminho | Função | Status |
|---|---|---|---|
| Model `AvailabilityBlock` | `apps/core/models/agenda.py` | `tipo` (T/P — não D), `inicio`, `fim`, `usuario`, `motivo`, `status`, **`created_by`** (PR 13) | ✅ existe |
| ViewSet (CRUD) | `views_availability.AvailabilityBlockViewSet` | CRUD; `POST` permite delegação via helper `user_can_delegate_availability_block` (PR 13) | ✅ existe |
| **Service de import** | `apps/core/services/bloqueios_import.py` | `import_bloqueios_from_file(path: str, dry_run: bool = True) -> dict`. Cabeçalho: `usuario,inicio,fim,tipo,motivo`. Reconciliação de `usuario` via `resolve_user_by_name` (linha 28 do service). Timezone `America/Fortaleza` (linha 30). | ✅ **já implementado** |
| Service `check_conflicts` | `apps/core/services/availability_service.py` | RD-01..08 (consome bloqueios — não é o service de import). **Calcula D dinamicamente** entre Solicitações em municípios diferentes; D não é armazenado como bloqueio. | ✅ existe |
| **Endpoint síncrono** | `POST /api/disponibilidade/import-bloqueios/` (`ImportBloqueiosView` em `apps/core/views_import_bloqueios.py`) | dry_run + multipart `file=` | ✅ **já funciona** |
| **Endpoint assíncrono (ASQ-005 Fase 1 — piloto)** | `POST /api/imports/bloqueios/` → cria `ImportJob`, retorna `202 Accepted` | Despacha Celery task `task_run_import_job`. Job persiste com `import_type='bloqueios'`. Status acompanhado via `GET /api/imports/<id>/`. | ✅ **já funciona** (único tipo async hoje) |
| Endpoint async (status) | `GET /api/imports/<id>/` | Retorna `ImportJob` serializado (status, stats, pendencias) | ✅ existe |
| Endpoint async (lista) | `GET /api/imports/` | Lista jobs do usuário (filtro `type=` `status=`) | ✅ existe |
| Gate RBAC (endpoint sync) | `IsAuthenticated + HasPerm("import_spreadsheet")` (DAT) | NÃO `import_availability_blocks` direto — policy `import_availability_blocks` é apenas para exposição via `/api/me/policies/` | ✅ aplicado |
| Gate RBAC (endpoint async upload) | `IsAuthenticated + CanImportGenericSpreadsheet` (Policy class) | Verificar em `apps/core/views/imports.py` | ✅ aplicado |
| AuditLog delegação | `DELEGATE_BLOCK_CREATE` (PR 13) | Quando outro user cria bloqueio em nome de Formador (não vem de import — vem de POST manual) | ✅ existe |

### Comportamento real do service (lido em código + docstring)

- **Cabeçalho aceito** (docstring linhas 6-12 de `bloqueios_import.py`):
  - `usuario` (obrigatório, nome do formador)
  - `inicio` (obrigatório, datetime)
  - `fim` (obrigatório, datetime > inicio)
  - `tipo` (obrigatório, **T=Total** ou **P=Parcial**; **D não suportado**)
  - `motivo` (opcional)
- **Reconciliação**: `resolve_user_by_name(name)` em `resolvers.py`, com fallback heurístico (primeiro nome + último nome, ou parte exata). **Vulnerável a homônimos** — pendência conhecida.
- **Timezone**: `ZoneInfo("America/Fortaleza")` fixo (linha 30 do service).
- **Idempotência**: tupla natural `(usuario, inicio, fim, tipo)` — não confirmado se há `external_hash` SHA256 explícito (verificar `_process_row`).
- **`created_by`**: ao chamar `save()` o service grava `created_by=...` (não confirmado se é o usuário que disparou o import ou `None`).

---

## 10. O que pode ser criado/atualizado

### Pode criar
- `AvailabilityBlock` com:
  - `usuario` = formador/coordenador alvo.
  - `created_by` = usuário que rodou o import (audit trail).
  - `status='aprovado'` (auto-aprovado como bloqueio declarado pelo próprio).
  - `tipo`, `inicio`, `fim` conforme planilha.
  - `motivo` (texto).

### Pode atualizar
- Nada. Idempotência via hash; mudanças exigem fluxo manual ou re-import com hash diferente.

---

## 11. O que NÃO deve acontecer automaticamente

- Deletar bloqueios existentes que não estão na planilha (a planilha é additive).
- Criar bloqueio para usuário sem Função `Formador` ou `Coordenador`.
- Ajustar timezone para UTC sem passar por America/Fortaleza.
- Disparar notificação ao usuário ou ao Controle.
- Mover/cancelar Solicitação existente que conflita com o novo bloqueio (deixar fluxo manual decidir).

---

## 12. Como auditar depois

### AuditLog
```python
AuditLog.objects.filter(
    action="IMPORT_AVAILABILITY_BLOCKS",
    created_at__gte=<timestamp>
).values(
    "usuario", "details__arquivo_hash",
    "details__linhas_criadas",
    "details__linhas_ignoradas",
    "details__usuarios_unicos",
)
```

### Drift check
- Comparar `AvailabilityBlock.objects.filter(created_at__date=<dia>).count()` com `linhas_criadas`.
- Listar formadores com bloqueio `>= 90 dias` no horizonte (possível erro de planilha).
- Cruzar bloqueios com Solicitações existentes para detectar conflitos pré-existentes.

### Relatório de conflitos pós-import
Listar Solicitações `status='aprovado'` que após o import passam a colidir com bloqueio T/P/D → fila de revisão.

---

## 13. Riscos identificados

| Risco | Severidade | Mitigação |
|---|---|---|
| Bloqueio em horário UTC errado | Alta | Sempre normalizar via Fortaleza local |
| Bloqueio T sobrescrevendo Solicitacao já aprovada | Alta | NÃO mover/cancelar Solicitacao automaticamente; só relatar |
| Usuario inexistente | Alta | Bloqueante (rejeita linha) |
| Deslocamento sem origem/destino | Média | Bloqueante |
| Bloqueio com `hora_fim==hora_inicio` (P) | Média | RD-01: end==start não é conflito, mas é bloqueio degenerado — warning |
| Match errado de Usuario por nome | Alta | Preferir email/CPF como identificador; senão warning explícito |
| Lapso de timezone em sync internacional | Baixa | Documentar TZ no template |

---

## 14. Pendências para Matheus (revistas)

### Resolvidas pelo código atual

- ~~Formato definitivo da planilha?~~ → **Resolvido em parte**: `bloqueios_import.py` aceita `usuario,inicio,fim,tipo,motivo`. Falta só confirmar se esse cabeçalho bate com o que `sheets.banco` vai produzir.
- ~~Existe service?~~ → Sim, há ~6 meses no código.
- ~~Existe dry-run?~~ → Sim, todos os services aceitam `dry_run=True`.
- ~~`ImportBatch` para auditoria?~~ → Já existe `ImportJob` (`apps/core/models/import_job.py`) com piloto em `bloqueios`.

### Pendências reais ainda

1. **Identificador do Usuário**: hoje o service usa `resolve_user_by_name` com fallback heurístico. Para evitar match errado, ideal trocar para CPF ou email — exige PR de runtime no service.
2. **Tipo D (Deslocamento)**: hoje **não suportado** como bloqueio. Deslocamentos são calculados dinamicamente por `availability_service` entre Solicitações de municípios diferentes. Se `sheets.banco` traz D explícito, precisa decidir:
   - (a) ignorar coluna D na importação (manter cálculo dinâmico);
   - (b) estender model `AvailabilityBlock` para aceitar D (mudança de schema);
   - (c) criar model separado `AvailabilityTravel` para deslocamentos declarados.
3. **Bloqueios recorrentes** (toda quarta, todo mês 25): **não há campo de recorrência no model atual**. Importar exige:
   - (a) pré-expandir em N linhas (responsabilidade do `sheets.banco`);
   - (b) ampliar model com `RRULE`/RFC 5545 (mudança grande de runtime).
4. **Política de re-import**: o service hoje (a verificar lendo `_process_row`) presumivelmente ignora linhas com mesma chave natural. Se a regra desejada for **substituir** todos os bloqueios do usuário no período, exige PR de runtime.
5. **Status inicial**: o service hoje (a verificar) provavelmente cria com `status='aprovado'`. Confirmar se importação por DAT deve ser auto-aprovada (vem de fonte oficial) ou `pendente` para revisão pelo formador.
6. **Cancelar bloqueios**: planilha tem coluna `cancelar`? Hoje import é additive (não remove). Se for necessário cancelar via planilha, exige PR de runtime + soft-delete no model.
7. **`make etl-desloc-dry` e `deslocamentos_import.py`**: confirmar se esse serviço (que existe) cobre o caso de import de deslocamentos como dado independente de bloqueio.

---

## 15. Histórico de versões

- 2026-05-05 — v0.1 — PR 1 (proposta inicial). Tratava formato como totalmente pendente.
- 2026-05-05 — v0.2 — Auditoria contra código real. **`bloqueios_import.py` confirmado funcional** para T/P + endpoint sync **e** async (ASQ-005 piloto). Pendências reorientadas: identificador robusto, tipo D, recorrência continuam abertas.
