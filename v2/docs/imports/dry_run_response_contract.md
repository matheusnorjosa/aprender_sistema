# Contrato de resposta de dry-run / import — auditoria + proposta

Status: **PR 2 — docs-only (sem alteração de runtime)**
Versão: 2026-05-05 v0.1
Escopo: auditoria dos 11 services `*_import.py` existentes + proposta de contrato unificado de resposta.

> Esta PR não altera código. Apenas inspeciona o estado atual, identifica inconsistências e propõe um contrato futuro. Implementação fica para PRs subsequentes.

---

## 1. Resumo executivo

| Métrica | Valor |
|---|---|
| Services auditados | **11** |
| Todos têm parâmetro `dry_run`? | ✅ Sim — todos aceitam `dry_run: bool` (default `True` em 8; `False` em 3 legacy) |
| Padrões de retorno distintos identificados | **2** ("dataclass legacy" + "dict aninhado moderno") |
| Services com idempotência via `external_hash` (SHA1) | 4 (compras, ações controle, DAT cadastros, eventos) |
| Services com idempotência via campo unique | 3 (usuarios=cpf, produtos=codigo, municipios=nome+uf) |
| Services com idempotência via tupla natural sem hash | 4 (bloqueios, colecoes, equipe_gerencia, deslocamentos) — confirmar lendo `_process_row` |
| Services que retornam `created_ids` | **1** (compras) |
| Services que gravam relatório JSON em disco (`out_etl/`) | **3** (compras, ações controle, DAT cadastros) |
| Padrão `savepoint-per-row` (ASQ-016) | **7** (todos os "modernos") |

**Conclusão principal**: backend tem 2 famílias de imports com shape diferente; padronização exige escolher uma das duas como referência e migrar o restante. **Recomendação: usar família "dict aninhado moderno" como base** (mais recente, mais usada, mais alinhada com `ImportJob.stats`/`pendencias` que já são JSON).

---

## 2. Service-by-service: tabela mestra

> Notação: ✅ confirmado lendo código · ⚠️ inferido sem leitura de `_process_row` · ❓ não verificado

### 2.1 Serviços modernos ("família dict aninhado")

| # | Service | Endpoint | View | Função | dry_run default | Cabeçalho CSV aceito | Models afetados | Cria | Atualiza | Savepoint-per-row | Idempotência | Hash | Padrão de retorno |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `usuarios_import.py` | `POST /api/usuarios/import/` | `ImportUsuariosView` (`views_import_usuarios.py`) | `import_usuarios_from_file(*, path, dry_run=True)` | `True` | `cpf,nome,email,telefone,cargo,is_active,grupos` | `Usuario` (+ `Group` M2M) | ✅ | ✅ (campos não-chave) | ✅ ASQ-016 | CPF unique | — | dict aninhado |
| 2 | `eventos_import.py` | `POST /api/solicitacoes/import/` | `ImportEventosView` | `import_eventos_from_file(*, path, dry_run=True)` | `True` | `municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,formador1..5,encontro,segmento,local` | `Solicitacao` (+ `Participation` M2M, role COORDENADOR/FORMADOR) | ✅ | ⚠️ (idempotência absorve) | ⚠️ (provável) | `external_hash` ⚠️ | SHA-? | dict aninhado |
| 3 | `bloqueios_import.py` | `POST /api/disponibilidade/import-bloqueios/` **+** `POST /api/imports/bloqueios/` (async via `ImportJob`) | `ImportBloqueiosView` + `ImportJobBloqueiosUploadView` | `import_bloqueios_from_file(*, path, dry_run=True)` | `True` | `usuario,inicio,fim,tipo,motivo` (tipo ∈ {T, P}) | `AvailabilityBlock` | ✅ | ⚠️ | ⚠️ | tupla (usuario,inicio,fim,tipo) ⚠️ | — | dict aninhado |
| 4 | `produtos_import.py` | `POST /api/produtos/import/` | `ImportProdutosView` | `import_produtos_from_file(*, path, dry_run=True)` | `True` | `codigo,nome,projeto,descricao,ativo` | `Produto` | ✅ | ✅ | ✅ ASQ-016 | codigo unique | — | dict aninhado |
| 5 | `colecoes_import.py` | `POST /api/colecoes/import/` | `ImportColecoesView` | `import_colecoes_from_file(*, path, dry_run=True)` | `True` | `nome,projeto,descricao,ativo` | `Colecao` (+ FK `Projeto`) | ✅ | ✅ | ✅ ASQ-016 | (nome, projeto) ⚠️ | — | dict aninhado |
| 6 | `municipios_import.py` | `POST /api/municipios/import/` | `ImportMunicipiosView` | `import_municipios_from_file(*, path, dry_run=True)` | `True` | `nome,uf,ibge_code,ativo` | `Municipio` | ✅ | ✅ | ✅ ASQ-016 | (nome, uf) ⚠️ | — | dict aninhado |
| 7 | `equipe_gerencia_import.py` | `POST /api/equipe-gerencia/import/` | `ImportEquipeGerenciaView` | `import_equipe_gerencia_from_file(*, path, dry_run=True)` | `True` | `setor/gerencia,papel/funcao,usuario_cpf,usuario_email,usuario_nome,coordenador_supervisor,ativo` (flexível) | `EquipeGerencia` + `Gerencia` (+ FK `Usuario`) | ✅ | ✅ | ✅ ASQ-016 | (gerencia, usuario, papel) ⚠️ | — | dict aninhado **+ extras** (`gerencias_created`, `gerencias_existing`) |
| 8 | `deslocamentos_import.py` | (não confirmado endpoint sync) | (não confirmado view) | `import_deslocamentos_from_file(*, path, dry_run=True)` | `True` | `usuario,origem,destino,data_inicio,data_fim,observacao` | `Deslocamento` | ✅ | ⚠️ | ✅ ASQ-016 | `external_hash` ⚠️ | SHA-? ⚠️ | dict aninhado |

### 2.2 Serviços legacy ("família dataclass + JSON em disco")

| # | Service | Endpoint | View | Função | dry_run default | Cabeçalho CSV aceito | Models afetados | Cria | Atualiza | Savepoint-per-row | Idempotência | Hash | Padrão de retorno |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | `controle_imports.py` (**Compras**) | `POST /api/controle/import-compras/` | `ImportComprasView` (`views_controle_imports.py`) | `import_compras_from_file(*, path, dry_run=True, auto_create_municipios=False)` | `True` | **`CÓD`/`COD`/`Cód`/`id`/`ID`** (variantes), **`Produto`**, **`Quant.`/`Quant`/`Quantidade`**, **`Município`/`Municipio`**, **`UF`**, **`Data`**, **`Uso das coleções`/`Uso`** | `Compra` (FK `Municipio`, `Projeto`) | ✅ | ✅ (via `update_or_create`) | ❌ — `transaction.atomic()` única | `external_hash` SHA1 | `SHA1(municipio_id\|projeto_id\|codigo\|produto_norm\|quantidade\|data\|uso_norm)` | dataclass + `created_ids` + relatório JSON em `out_etl/import_compras_report.json` |
| 10 | `controle_acoes_import.py` | `POST /api/controle/import-acoes/` | `ControleImportAcoesView` (`views_imports.py`) | `import_acoes_controle(file_path, dry_run=False)` | **`False`** ⚠️ | (não documentado em docstring; padrão Município, Projeto, Coordenador, datas) | `AcaoControle` | ✅ | ✅ (via `update_or_create`) | ✅ ASQ-016 | `external_hash` SHA1 | `SHA1(municipio_id\|projeto_id\|coordenador_id)` | dict aninhado **+ relatório JSON** em `out_etl/import_acoes_controle_report.json` |
| 11 | `dat_cadastros_import.py` | `POST /api/dat/import-cadastros/` | `DATImportCadastrosView` (`views_imports.py`) | `import_dat_cadastros(file_path, dry_run=False)` | **`False`** ⚠️ | (não documentado em docstring; padrão Município, Projeto, Tipo de ação, Responsável) | `AcaoDAT` (+ FK `TipoAcaoDAT`) | ✅ | ✅ (via `update_or_create`) | ✅ ASQ-016 | `external_hash` SHA1 | `SHA1(municipio_id\|projeto_id\|tipo_acao\|responsavel_id)` | dict aninhado **+ relatório JSON** em `out_etl/import_dat_cadastros_report.json` |

### 2.3 Observações por inconsistência

| Inconsistência | Services afetados | Risco |
|---|---|---|
| **`dry_run` default `False`** em vez de `True` | `controle_acoes_import`, `dat_cadastros_import` | **Alto** — chamada interna sem keyword vai persistir. Endpoints externos protegem via query-param, mas chamada Python direta é perigosa |
| **Stats com 4 campos vs 4+aninhado** | `controle_imports` (dataclass `{created,updated,skipped,errors}`) vs demais (dict `{created,updated,unchanged,skipped:{...}}`) | Médio — frontend precisa branch lógica |
| **`pendencias` com chaves diferentes** | Cada service define categorias próprias (`municipios`, `projetos`, `cpf_invalid`, `dates`, `usuarios`, `outros`, etc.) | Médio — frontend não pode tratar genericamente |
| **`created_ids` só em compras** | `controle_imports` retorna lista; demais não | Baixo — não é semântica universal |
| **Relatório JSON em `out_etl/`** só em 3 (compras, ações controle, DAT cadastros) | Resto não persiste em disco | Baixo — feature legacy; `ImportJob.stats/pendencias` substitui |
| **Sem `row_number` na resposta** | Todos | **Alto** — frontend não consegue mapear erro/warning à linha do CSV de forma estruturada (alguns colocam `linha`/`row` dentro do dict de pendência, outros não) |
| **Sem `error_code` / `warning_code` estruturados** | Todos — categorização vive em chaves do dict de pendências (`cpf_invalid`, `municipios`, etc.) | **Alto** — i18n e filtragem por código ficam difíceis |
| **Sem preview das primeiras N linhas** | Todos | Médio — frontend não pode exibir prévia visual sem rodar dry-run + parsear |
| **`auto_create_municipios=False`** parâmetro só em `controle_imports` | Demais não têm flag análoga | Baixo — específico do domínio |
| **Tipo D (Deslocamento) ausente** em `bloqueios_import` | Apenas T e P aceitos | Médio — RD-04 calcula D dinamicamente; planilha não traz D explícito |
| **`controle_imports` sem savepoint-per-row** | Apenas ele usa `transaction.atomic()` única | Baixo — rollback total em erro de uma linha; ASQ-016 já protege os demais |

---

## 3. Padrão de retorno — duas famílias

### 3.1 Família A — "dict aninhado moderno" (8 services)

```json
{
  "stats": {
    "created": 10,
    "updated": 5,
    "unchanged": 2,
    "skipped": {"<categoria_1>": 0, "<categoria_2>": 0, "other": 0}
  },
  "pendencias": {
    "<categoria_1>": [{"linha": N, "row": "<repr>", "erro": "msg"}],
    "<categoria_2>": [],
    "outros": []
  },
  "dry_run": true,
  "file": "/tmp/xyz.csv"
}
```

### 3.2 Família B — "dataclass + relatório JSON" (3 services legacy)

```json
{
  "path": "/tmp/xyz.csv",
  "dry_run": true,
  "stats": {"created": 10, "updated": 5, "skipped": 2, "errors": 0},
  "pendencias": {
    "municipios": [{"row": 2, "municipio": "X", "uf": "CE"}],
    "projetos": [],
    "linhas_invalidas": []
  },
  "created_ids": [42, 43, 44],
  "ts": "2026-05-05T12:00:00-03:00"
}
```

Além disso, gravam relatório completo em `<settings.BASE_DIR>/out_etl/import_<tipo>_report.json` no apply.

---

## 4. Contrato padrão proposto (PR 6 — futuro)

### 4.1 Objetivo

Unificar resposta entre os 11 services + `ImportJob.stats` + `ImportJob.pendencias` para que **frontend possa renderizar genericamente** qualquer tipo de import.

### 4.2 Princípios

1. **Compatibilidade gradual**: adicionar campos novos sem remover os antigos por 1 release. Migrar service-by-service.
2. **Códigos estáveis** em vez de chaves descritivas: `INVALID_CPF` em vez de `cpf_invalid`. Permite i18n no frontend.
3. **`row_number` obrigatório** em cada erro/warning: ancora ao CSV original.
4. **Preview das primeiras 50 linhas** opcional (`preview=true` query param).
5. **Idempotência exposta**: campo `import_hash` por linha, mesmo em dry-run, para auditoria de drift.
6. **Não quebrar `ImportJob`**: `stats` e `pendencias` ali já são JSONField — contrato novo é subset compatível.

### 4.3 Schema proposto

```json
{
  "ok": true,
  "dry_run": true,
  "import_type": "usuarios",
  "file": {
    "path": "/tmp/xyz.csv",
    "original_filename": "usuarios_2026_05.csv",
    "size_bytes": 4321,
    "checksum_sha256": "<file_hash>"
  },
  "summary": {
    "total_rows": 100,
    "valid_rows": 92,
    "created_rows": 80,
    "updated_rows": 8,
    "unchanged_rows": 4,
    "skipped_rows": 5,
    "warning_rows": 3,
    "invalid_rows": 3
  },
  "errors_by_code": {
    "INVALID_CPF": 2,
    "MUNICIPIO_NOT_FOUND": 1
  },
  "warnings_by_code": {
    "EMAIL_DOMAIN_UNUSUAL": 3
  },
  "rows": [
    {
      "row_number": 2,
      "status": "valid",
      "action": "create",
      "errors": [],
      "warnings": [],
      "normalized": {"cpf": "12345678901", "nome": "Maria Exemplo"},
      "import_hash": "sha256:abcdef..."
    },
    {
      "row_number": 3,
      "status": "invalid",
      "action": null,
      "errors": [
        {"code": "INVALID_CPF", "field": "cpf", "message": "CPF 11 dígitos inválido", "value": "123"}
      ],
      "warnings": [],
      "normalized": null,
      "import_hash": null
    }
  ],
  "metadata": {
    "service": "apps.core.services.usuarios_import",
    "started_at": "2026-05-05T12:00:00-03:00",
    "finished_at": "2026-05-05T12:00:01-03:00",
    "duration_ms": 950
  }
}
```

### 4.4 Mapeamento campos atuais → contrato novo

| Campo atual (família A/B) | Campo contrato | Mudança |
|---|---|---|
| `stats.created` | `summary.created_rows` | rename |
| `stats.updated` | `summary.updated_rows` | rename |
| `stats.unchanged` (apenas A) | `summary.unchanged_rows` | preservar |
| `stats.skipped` (B) ou `stats.skipped.<cat>` (A) | `summary.invalid_rows` + `summary.skipped_rows` | dividir entre inválido (bloqueante) e skipped (ok mas não persiste) |
| `stats.errors` (B) | `summary.invalid_rows` | rename |
| `pendencias.<categoria>` | `rows[*]` com `errors:[{code,...}]` | reestruturar — categoria vira `error.code` |
| `created_ids` (compras) | `rows[*].metadata.created_id` quando `action==create` | opcional, restrito a apply |
| `dry_run` | `dry_run` | manter |
| `file` (string) | `file.path` | aninhar |
| `ts` (B) | `metadata.finished_at` | rename |
| `path` (B) | `file.path` | rename |

### 4.5 Códigos de erro propostos (1ª versão — completar conforme migração)

| Código | Significado | Service mais comum |
|---|---|---|
| `INVALID_CPF` | CPF não tem 11 dígitos ou DV inválido | usuarios |
| `MISSING_REQUIRED_FIELD` | Campo obrigatório vazio | todos |
| `MUNICIPIO_NOT_FOUND` | Lookup `resolve_municipio` retornou None | eventos, compras, ações, DAT |
| `PROJETO_NOT_FOUND` | Lookup `resolve_projeto` retornou None | eventos, compras, ações, DAT |
| `USUARIO_NOT_FOUND` | `resolve_user_by_email/name` retornou None | eventos, bloqueios, deslocamentos, equipe_gerencia |
| `INVALID_DATE` | Falha em `parse_date_flexible` ou similar | todos com data |
| `INVALID_TIME` | Falha em parse de hora | eventos |
| `END_BEFORE_START` | `fim <= inicio` | eventos, bloqueios, deslocamentos |
| `INVALID_QUANTITY` | Quantidade não inteira/<=0 | compras |
| `INVALID_TIPO_ACAO` | Tipo de ação fora do `TipoAcaoDAT`/`TipoAcaoControle` | ações controle, DAT cadastros |
| `INVALID_TIPO_BLOQUEIO` | `tipo ∉ {T, P}` | bloqueios |
| `DUPLICATE_IN_FILE` | Mesma chave natural aparece 2x no CSV | todos |
| `EMAIL_DOMAIN_UNUSUAL` | Email fora de allowlist (warning) | usuarios |
| `OTHER` | Erro genérico (fallback) | todos |

---

## 5. Classificação de risco para padronização

Critérios: complexidade, models afetados, dry_run real, idempotência, uso em produção, relação com GCal/RBAC.

### 5.1 Baixo risco (começar por aqui)

| Service | Justificativa |
|---|---|
| `municipios_import.py` | Cadastro mestre. Sem FK para nada crítico. Sem GCal. Cache de options para invalidar é simples. |
| `colecoes_import.py` | Cadastro mestre. FK apenas `Projeto`. Sem GCal. |
| `usuarios_import.py` | Cadastro de identidade. Atribuição de grupos via coluna `grupos` (não automática para Função sensível). Sem GCal. Padrão moderno já bem alinhado ao contrato. |
| `produtos_import.py` | Cadastro mestre. FK apenas `Projeto`. |
| `equipe_gerencia_import.py` | Cadastro de vínculo. Tem extras `gerencias_created/existing` no stats — bom caso de teste para extensibilidade do contrato. |

### 5.2 Médio risco

| Service | Justificativa |
|---|---|
| `bloqueios_import.py` | Reconciliação por nome é frágil. Já tem **endpoint sync E async** (`ImportJob`). Bom candidato para validar contrato funcionar nas duas modalidades. |
| `deslocamentos_import.py` | Reconciliação por nome/email. Endpoint sync não confirmado. |
| `controle_acoes_import.py` | Legacy. Default `dry_run=False`. Grava JSON em disco. Migrar exige corrigir default. |
| `dat_cadastros_import.py` | Legacy. Mesmas características de controle_acoes. Mapa `TipoAcaoDAT` complexo. |

### 5.3 Alto risco

| Service | Justificativa |
|---|---|
| `eventos_import.py` | **Toca Solicitação + Participation M2M + PA-01** automática. Erro de contrato pode mascarar status/data errados. Relação indireta com GCal (campo `external_event_id` permanece None mas é hot path). Migrar último. |
| `controle_imports.py` (Compras) | Família dataclass diferente; cabeçalho com variantes case/acento; chave de idempotência depende de `_infer_projeto_from_produto` (cache + heurística). Grava JSON em disco. Endpoint usado em produção pelo Makefile via curl. |

---

## 6. Plano de migração seguro (para PR 6 futura)

### Fase 0 — Acordo de contrato (esta PR 2)

✅ Auditoria + contrato proposto + códigos de erro nomeados.

### Fase 1 — Wrapper que traduz o retorno legado

- Criar helper `apps/core/imports/response_adapter.py::to_standard_response(legacy_response, import_type)`.
- Frontend consome **apenas** o contrato novo via wrapper, sem mudar services.
- Risco: baixo (wrapper puro, não toca DB).

### Fase 2 — Migrar services baixo risco (1 PR por service)

Ordem sugerida:
1. `municipios_import.py`
2. `colecoes_import.py`
3. `produtos_import.py`
4. `equipe_gerencia_import.py`
5. `usuarios_import.py`

Cada PR:
- Retorna contrato novo nativo.
- Wrapper continua aceitando ambos para outros services.
- Tests cobrem que campos do contrato existem.

### Fase 3 — Migrar services médio risco

6. `deslocamentos_import.py`
7. `bloqueios_import.py` (cuidado: usado por endpoint sync **e** async via `ImportJob`)
8. `controle_acoes_import.py` (corrigir `dry_run=False` default antes)
9. `dat_cadastros_import.py` (corrigir `dry_run=False` default antes)

### Fase 4 — Migrar alto risco

10. `controle_imports.py` (Compras) — preservar `created_ids` e `out_etl/*.json` em modo legacy paralelo.
11. `eventos_import.py` — testar PA-01 + Participation antes de release.

### Fase 5 — Retirar wrapper de tradução

Quando todos os 11 retornarem contrato novo nativamente, remover `response_adapter.py` e mover frontend a consumir direto.

---

## 7. Critério de aceite desta PR

Quem ler este documento consegue responder:

| Pergunta | Resposta |
|---|---|
| Todos os imports retornam o mesmo formato? | **Não** — 2 famílias (dict aninhado moderno: 8; dataclass+JSON em disco: 3). Ver §2.1 / §2.2. |
| Quais retornam stats? | Todos os 11. Mas com shape diferente (4-campos vs 4+aninhado). Ver §3. |
| Quais retornam pendências? | Todos os 11. Mas com chaves de categoria diferentes por service. Ver §2.3. |
| Quais retornam erro por linha? | **Nenhum nativamente** — alguns colocam `linha`/`row` dentro do dict de pendência; nenhum tem array `rows[*]` com `row_number` estruturado. **Lacuna real para padronizar.** |
| Quais têm dry_run real? | Todos os 11. Mas 2 têm default `False` (`controle_acoes_import`, `dat_cadastros_import`) — risco se chamado via Python direto. |
| Quais têm idempotência? | **Todos** — 4 via SHA1 explícito (compras, ações controle, DAT cadastros, eventos), 3 via campo unique (usuarios=cpf, produtos=codigo, municipios=nome+uf), 4 via tupla natural sem hash visível (bloqueios, colecoes, equipe_gerencia, deslocamentos). |
| Quais podem ser migrados para `ImportJob` async? | **Todos os 11**, conforme comentário em `apps/core/models/import_job.py:41-44`. Hoje só `bloqueios` está async (piloto ASQ-005 Fase 1). |
| Qual deve ser o contrato padrão futuro? | Schema em §4.3. Resume: `summary` agregado, `rows[*]` com `row_number`+`errors[{code,field,message}]`+`warnings[]`+`normalized`+`import_hash`, `errors_by_code`/`warnings_by_code` agregados, `metadata`. |
| Qual service deve ser padronizado primeiro? | **`municipios_import.py`** (baixo risco, cadastro mestre, sem FK críticas). Sequência completa em §6. |

---

## 8. Pendências de leitura (para validar nesta PR ou em PRs subsequentes)

| Item | O que falta verificar |
|---|---|
| Shape final de `usuarios_import._process_row` | Confirmar que tem `import_hash` em alguma forma. Hoje a docstring lista apenas `created/updated/unchanged/skipped` em stats. |
| Shape final de `eventos_import.py` apply (linha que cria Solicitacao + Participation) | Confirmar valor de `external_hash` exato e como Participation é registrada (1 linha por participante? embebida em row?). |
| Shape final de `bloqueios_import.py` apply | Confirmar `external_hash` ou chave natural. |
| `_process_row` de `colecoes_import.py`, `municipios_import.py`, `produtos_import.py`, `equipe_gerencia_import.py`, `deslocamentos_import.py` | Confirmar exatamente quais campos vão para `pendencias.outros` vs categorias específicas. |
| Endpoint sync de **`deslocamentos`** | Existe view DRF correspondente? `views_import_deslocamentos.py` existe na pasta — falta confirmar rota e gate. |
| Default `dry_run=False` em `controle_acoes_import` e `dat_cadastros_import` | Decidir se é bug a corrigir ou intencional (Makefile chama com `?dry_run=true|false` explícito). |

---

## 9. Pendências de produto

1. **Códigos de erro nomeados**: validar a lista §4.5 com Matheus. Acrescentar/remover conforme casos reais.
2. **Preview das primeiras 50 linhas**: implementar como opt-in (`?preview=true`) ou sempre?
3. **`import_hash` por linha em dry-run**: aceita esforço extra para auditoria pré-apply ou só após apply?
4. **`out_etl/*_report.json` (legacy)**: continuar gravando mesmo após migração para contrato novo, ou descontinuar?
5. **`controle_acoes_import` e `dat_cadastros_import` com default `dry_run=False`**: corrigir agora (PR de runtime separada) ou esperar migração ao contrato novo?
6. **Cabeçalhos com acento (`CÓD`, `Município`, `Uso das coleções`)**: manter aceitação de variantes ou forçar snake_case nos templates (mais limpo)?

---

## 10. Histórico de versões

- 2026-05-05 — v0.1 — PR 2. Auditoria inicial dos 11 services. Proposta de contrato padrão + plano de migração em 5 fases. Cabeçalho de Compras (`CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções`) confirmado lendo `controle_imports.py:156-163`.
