# Importação: Produtos / Controle (Compras)

Status: PR 1 — contrato fechado, **backend implementado**; **§3, §6, §7, §9 e §11 descreviam `DATCompra` e validações que não existem** (revisto 2026-07-24)
Versão: 2026-07-24 v0.4
Template: [templates/produtos_controle.template.csv](./templates/produtos_controle.template.csv)

> 🔴 **Atualização v0.4 (2026-07-24)** — três correções de fato, provadas em `controle_imports.py`:
>
> 1. **O preview aceita linhas inválidas.** A validação bloqueante é só
>    `if not r["municipio"] or r["quantidade"] is None or not r["codigo"]`
>    (`services/controle_imports.py:208`). Como a normalização faz
>    `int(float(quant_raw or 0))` (`:172`), **quantidade vazia vira `0`** — que não é `None` e
>    portanto **passa**. Quantidade negativa passa. Decimal é truncado em silêncio (`2.7 → 2`).
>    **`data` ausente não é validada** e é gravada como `None`. Achado `M15-04`, issue
>    [#1634](https://github.com/matheusnorjosa/aprender_sistema/issues/1634).
> 2. **UF é lida mas não é usada na resolução.** O campo é normalizado (`:167`) e aparece nas
>    pendências, mas a chamada é `resolve_municipio(r["municipio"])` (`:225`) — **sem a UF**.
>    Municípios homônimos em UFs diferentes são desempatados por `.first()`
>    (`services/resolvers.py:213`). Achado `M15-05`, issue
>    [#1635](https://github.com/matheusnorjosa/aprender_sistema/issues/1635).
> 3. **`Compra.produto` nunca é gravado, e o código do produto não resolve nada.** Os `defaults`
>    do upsert (`:251-258`) são `municipio`, `projeto`, `codigo`, `quantidade`, `data`, `uso` —
>    **sem FK para `Produto`**. O projeto vem de `_infer_projeto_from_produto(produto_norm)`
>    (`:234`), que infere a partir do **nome** do produto; o campo `codigo`/`CÓD` é gravado como
>    string mas **não é usado em lookup nenhum**. Mesmo achado `M15-05` / #1635.
>
> Épico de causa raiz: [#1659](https://github.com/matheusnorjosa/aprender_sistema/issues/1659)
> (import bypassa invariantes). Ver [../audits/ACHADOS_REAIS.md](../audits/ACHADOS_REAIS.md).

> ⚠️ **Atualização v0.2**: a v0.1 tratava o service como "futuro" e deixava aberta a decisão `Compra` vs `DATCompra`. Verificação no código (`controle_imports.py:26`) confirma que **`import_compras_from_file` alimenta `Compra`** (não `DATCompra`). Existem ainda services separados para `Produto` (catálogo), `Municipio`, `Colecoes`, etc. Esta versão lista todos.

---

## 1. Objetivo

Importar registros de uso/aquisição de produtos por município, a partir da aba de "Controle" da
planilha `sheets.banco`. **Alimenta `Compra`** (histórico), não `DATCompra` — decisão já resolvida
pelo código (§8).

Cobre (comportamento **real**):
- Lookup de `Municipio` **só por nome** — a UF é lida mas ignorada na resolução (§8).
- Resolução de `Projeto` por **inferência a partir do nome do produto**
  (`_infer_projeto_from_produto`), não pelo código.
- Criação/atualização de `Compra` com idempotência via `external_hash` SHA-1.

Não cobre:
- Criação de Produto novo (catálogo é cadastrado separadamente, ver [ordem_de_importacao.md](./ordem_de_importacao.md) passo 5).
- Criação de Município novo por padrão (`auto_create_municipios=False`).
- ❌ **Lookup de `Produto` por código** — o `CÓD` é gravado como string em `Compra.codigo`,
  mas **não** resolve FK nenhuma; `Compra.produto` fica sem valor (§7).

---

## 2. Dados de origem esperados

Aba `Controle` (ou similar) da planilha `sheets.banco`.

| Coluna planilha | Descrição |
|---|---|
| `F` | Código do produto (ex: `NL-C1`, `BRC-C2`) |
| `Produto` | Nome do produto (sanity check vs `F`) |
| `Quant.` | Quantidade adquirida/utilizada |
| `Município` | Nome do município |
| `UF` | Sigla da unidade federativa |
| `Data` | Data da compra/uso (BR `dd/mm/yyyy`) |
| `Uso das coleções` | Texto livre descrevendo finalidade |

---

## 3. Colunas obrigatórias

| Coluna CSV | Validação |
|---|---|
| `codigo` (vem de `F`) | deve existir em `Produto.codigo` |
| `quantidade` (vem de `Quant.`) | inteiro positivo (>0) |
| `municipio` | deve casar com `Municipio.nome` (case-insensitive, sem acento) |
| `uf` | sigla UF válida (lookup em `Municipio` junto com `municipio`) |
| `data` | data BR válida e razoável (>= 2020-01-01, <= hoje + 7d) |

---

## 4. Colunas opcionais

| Coluna CSV | Comportamento se vazio |
|---|---|
| `produto_nome` (vem de `Produto`) | Usar apenas como sanity check; lookup oficial é por `codigo` |
| `uso` (vem de `Uso das coleções`) | Salvar string vazia em `DATCompra.uso` |

---

## 5. Normalizações esperadas (PR 2 — `normalization.py`)

| Campo | Função (futura) | Resultado |
|---|---|---|
| `codigo` | `normalize_text_key` | Uppercase, strip, remove espaços internos |
| `produto_nome` | `normalize_text_key` | Lowercase, strip, remove acentos para comparação |
| `quantidade` | `int()` + validate >=1 | Inteiro |
| `municipio` + `uf` | `normalize_municipio_uf` | `(nome_normalized, uf_uppercase)` |
| `data` | `parse_br_date` | `datetime.date` em America/Fortaleza |
| `uso` | trim + strip | string |

---

## 6. Validações antes do upload (PR 6)

> 🔴 Corrigido em 2026-07-24 (`M15-04` / [#1634](https://github.com/matheusnorjosa/aprender_sistema/issues/1634)).
> Das 5 validações bloqueantes propostas, **nenhuma foi implementada como descrita**.

### Bloqueantes — pretendidas vs **REAIS** (`controle_imports.py:206-238`)

| Validação pretendida | Real |
|---|---|
| `codigo` não existe em `Produto` → rejeitar | ❌ só rejeita `codigo` **vazio**; não existe lookup em `Produto` |
| `quantidade <= 0` ou não numérico | ❌ só rejeita `quantidade is None`. **Vazio vira `0` e passa** (`int(float(quant_raw or 0))`, `:172`); negativo passa; decimal é truncado |
| `municipio` + `uf` não existe em `Municipio` | ⚠️ parcial — rejeita se `resolve_municipio(nome)` devolver `None`, mas **a UF não entra na busca** (`:225`) |
| `data` fora da faixa razoável | ❌ **não validada.** `parse_date_flexible` devolve `None` em falha e a linha segue; `Compra.data` fica `None` |
| `external_hash` duplicado no próprio arquivo | ❌ não detectado — a 2ª linha simplesmente sobrescreve a 1ª no `update_or_create` |
| (não previsto) `projeto` não inferível do nome do produto | ✅ **rejeita** → `pendencias.projetos` (`:234-238`) |

### Avisos
❌ **Não existe canal de warning.** As três categorias de pendência são `municipios`, `projetos` e
`linhas_invalidas`. Sanity check `produto_nome` × `Produto.nome` não é feito (não há lookup de
`Produto`). Reimport com hash existente entra em `stats.updated`, sem aviso.

---

## 7. Regras de duplicidade / hash

### Chave natural — **REAL** (`controle_imports.py:193-205`)

`(municipio_id, projeto_id, codigo, produto_norm, quantidade, data, uso_norm)` — **7 partes**.

`projeto_id` **não** vem de `Produto.projeto`: vem de `_infer_projeto_from_produto(produto_norm)`
(`:234`, `:317+`), heurística sobre o **nome normalizado** do produto.

⚠️ **A chave inclui campos mutáveis** (`quantidade` e `uso`). Corrigir a quantidade de uma linha na
planilha muda o hash e o reimport **cria uma segunda `Compra`** em vez de atualizar a primeira —
achado `M15-03` / [#1633](https://github.com/matheusnorjosa/aprender_sistema/issues/1633).

### `external_hash` — **SHA-1** (não SHA-256)

```text
sha1_str("|".join([municipio_id, projeto_id, codigo, produto_norm, quantidade, data, uso_norm]))
```

SHA-1 é congelado por ADR-012 (`v2/docs/adr/ADR-012-sha1-idempotency-hashes.md`).

### Comportamento por match — **REAL** (`:245-282`)

| Hash existe | Ação real no **apply** | Ação real no **dry-run** |
|---|---|---|
| Não | Cria `Compra` → `stats.created` + `created_ids` | conta `stats.created` |
| Sim, algum `default` diferente | `update_or_create` sobrescreve → `stats.updated` | conta `stats.updated` |
| Sim, tudo igual | `stats.skipped` | conta `stats.updated` (⚠️ o dry-run **não distingue** "vai atualizar" de "não muda nada") |

Nenhum warning é emitido em caso de drift entre planilha e banco.

---

## 8. Models / services / endpoints relacionados (estado real do código — 2026-05-05)

### Decisão `Compra` vs `DATCompra` — **RESOLVIDA pelo código atual**

Lendo `apps/core/services/controle_imports.py:26`:

```python
from apps.core.models import Compra, Municipio, Produto, Projeto
```

→ **O fluxo de import de "Compras" alimenta `Compra` (histórico ETL com `external_hash` SHA1)**, **não** `DATCompra`. Este é o estado em produção. `DATCompra` é alimentado por outro fluxo operacional (Admin/UI), não por planilha.

### Tabela completa de imports relacionados

| Componente | Caminho | Função | Status |
|---|---|---|---|
| **Service Compras** | `apps/core/services/controle_imports.py` | `import_compras_from_file(...)`. Aba "🟥 COMPRAS" da Planilha de Controle. Alimenta `Compra`. Idempotência via `external_hash` SHA1 determinístico. Gera relatório em `out_etl/import_compras_report.json`. | ✅ **já implementado** |
| **Service Catálogo Produtos** | `apps/core/services/produtos_import.py` | `import_produtos_from_file(...)`. Alimenta `Produto` (catálogo). Idempotência por `Produto.codigo`. | ✅ **já implementado** |
| **Service Municipios** | `apps/core/services/municipios_import.py` | `import_municipios_from_file(...)`. Cadastro mestre. | ✅ **já implementado** |
| **Service Coleções** | `apps/core/services/colecoes_import.py` | `import_colecoes_from_file(...)`. | ✅ **já implementado** |
| **Service Ações Controle** | `apps/core/services/controle_acoes_import.py` | `import_acoes_controle(...)`. Idempotência SHA1. | ✅ **já implementado** |
| **Service DAT Cadastros** | `apps/core/services/dat_cadastros_import.py` | `import_dat_cadastros(...)`. Cadastros consolidados DAT. Idempotência SHA1 (linha 301). | ✅ **já implementado** |
| **Service Deslocamentos** | `apps/core/services/deslocamentos_import.py` | `import_deslocamentos(...)`. Idempotência SHA1. | ✅ **já implementado** |
| Model `Compra` | `apps/core/models/compra.py` | Histórico ETL: `codigo`+`municipio`+`projeto`+`data` + `external_hash` | ✅ existe |
| Model `DATCompra` | `apps/core/models/dat_compra.py` | Gestão operacional (`quantidade_utilizada`, `status_uso`, `valor_unitario`, `ano_uso`) — **não alimentado por import** | ✅ existe |
| Model `Produto` | `apps/core/models/organizacao.py` | Catálogo (codigo único, FK Projeto) | ✅ existe |
| Model `Municipio` | `apps/core/models/organizacao.py` | nome, uf, ibge_code | ✅ existe |
| Resolvers compartilhados | `apps/core/services/resolvers.py` | `resolve_municipio` (com `_split_city_uf` para "Cidade - UF"), `resolve_projeto` (aliases IDEB→GESTÃO ESCOLAR, Nível N→NN) | ✅ existe |

### Endpoints HTTP (estado real — 2026-05-05)

| Endpoint | View | Gate RBAC |
|---|---|---|
| `POST /api/controle/import-compras/` | `ImportComprasView` em `apps/core/views_controle_imports.py` | `IsAuthenticated + HasPerm("import_spreadsheet")` (PR-A1 DAT-Imports 2026-04-29 centralizou em DAT-only) |
| `POST /api/produtos/import/` | `ImportProdutosView` em `apps/core/views_import_produtos.py` | `IsAuthenticated + HasPerm("import_spreadsheet")` |
| `POST /api/municipios/import/` | `ImportMunicipiosView` em `apps/core/views_import_municipios.py` | `IsAuthenticated + HasPerm("manage_admin_registries")` |
| `POST /api/colecoes/import/` | `ImportColecoesView` em `apps/core/views_import_colecoes.py` | `IsAuthenticated + HasPerm("manage_admin_registries")` |
| `POST /api/controle/import-acoes/` | `ControleImportAcoesView` em `apps/core/views_imports.py` | `IsAuthenticated + HasPerm("import_spreadsheet")` |
| `POST /api/dat/import-cadastros/` | `DATImportCadastrosView` em `apps/core/views_imports.py` | `IsAuthenticated + HasPerm("manage_admin_registries")` |

Todos aceitam `?dry_run=true|false` (default `true`).

**Endpoints async** (ASQ-005 Fase 1): apenas `/api/imports/bloqueios/` por enquanto. Compras + produtos + cadastros migram em Fase 2 (ver `apps/core/models/import_job.py` linhas 41-44 — comentário do código define ordem).

### Shape de retorno (exemplo confirmado em `ImportComprasView` linha 60-72)

```json
{
    "path": "/tmp/xyz.csv",
    "dry_run": true,
    "stats": {"created": 10, "updated": 5, "skipped": 2, "errors": 0},
    "pendencias": {
        "municipios": [...],
        "projetos": [...],
        "linhas_invalidas": [...]
    },
    "created_ids": [...],
    "ts": "2025-10-21T..."
}
```

> ⚠️ Cada service retorna shape ligeiramente diferente (uns têm `created_ids`, outros não; `stats.unchanged` em uns, `stats.skipped` em outros). Padronização é objetivo de **PR 2** do roadmap revisto.

### Makefile

`make import-compras-dry FILE=...` no Makefile chama via curl `POST /api/controle/import-compras/?dry_run=true` — **não** é management command Django.

---

## 9. O que pode ser criado/atualizado

> 🔴 Esta seção falava de `DATCompra`. O import alimenta **`Compra`** (§8). Corrigida em 2026-07-24.

### Cria — **REAL** (`controle_imports.py:251-262`)
`Compra` com exatamente 6 campos + o hash: `municipio`, `projeto`, `codigo` (string), `quantidade`,
`data`, `uso`, `external_hash`.

❌ **`Compra.produto` não é gravado** — o import nunca resolve o FK do produto (`M15-05` / #1635).
`status_uso`, `quantidade_utilizada`, `valor_unitario` e `ano_uso` são campos de **`DATCompra`**,
que este import não toca.

### Atualiza — **REAL**
Todos os 6 campos acima, via `update_or_create` quando o `external_hash` bate. Sem warning.
Como `quantidade` e `uso` fazem parte do hash (§7), na prática só `municipio`/`projeto`/`data`
podem mudar sem gerar linha nova — e `codigo`/`produto_norm` também entram no hash.

---

## 10. O que NÃO deve acontecer automaticamente

> ⚠️ Coluna "Aplicado?" adicionada em 2026-07-24.

| Regra pretendida | Aplicada? | Prova |
|---|---|---|
| Criar `Produto` novo | ✅ sim | o service nem consulta `Produto` |
| Criar `Municipio` novo | ✅ por padrão | `auto_create_municipios=False` é o default de `import_compras_from_file` |
| Deletar linhas que sumiram da planilha | ✅ sim | o service só faz `update_or_create` |
| Rejeitar quantidade inválida | ❌ **não** | vazio→`0`, negativo passa, decimal truncado (`:172`, `:208`) — #1634 |
| Rejeitar data ausente/inválida | ❌ **não** | `data=None` é gravado (`:180`, `:257`) — #1634 |
| Usar UF para desambiguar município | ❌ **não** | `resolve_municipio(r["municipio"])` sem UF (`:225`) — #1635 |
| Usar o código do produto para resolver o catálogo | ❌ **não** | projeto vem do **nome** do produto (`:234`) — #1635 |
| Registrar quem rodou o import | ❌ **não** | nenhum `AuditLog` (§11) |

---

## 11. Como auditar depois

### AuditLog — 🔴 **NÃO EXISTE para este import**

A ação `IMPORT_PRODUTOS_CONTROLE` nunca existiu. `AuditLog.Action`
(`apps/core/models/auditoria.py:72-73`) só define `IMPORT_JOB_COMPLETED` e `IMPORT_JOB_FAILED`,
emitidos apenas no caminho assíncrono (`apps/core/tasks.py:634,669`), hoje limitado a `bloqueios`.

O que **existe** neste import é o relatório JSON em disco:
`<BASE_DIR>/out_etl/import_compras_report.json`, reescrito a cada execução (inclusive dry-run).
Não é auditoria — não tem usuário, não tem histórico e o arquivo seguinte sobrescreve o anterior.

### Drift check
- Comparar contagem por município: `Compra.objects.values("municipio").annotate(c=Count("id"))`.
- Listar `Compra` com `data__isnull=True` ou `quantidade__lte=0` — são as linhas inválidas que o
  preview deixou passar (#1634).
- Listar `Compra` com `produto__isnull=True` — hoje serão **todas** (#1635).
- Detectar duplicatas de #1633: agrupar por `(municipio, projeto, codigo, data)` e procurar
  `count > 1` — cada correção de quantidade na planilha gera uma linha extra.

### Reports operacionais
- `view_compras_dashboard` (Diretoria + DAT) exibe dashboard.
- `view_compras_pendencias`, `view_compras_stats` para painéis específicos.

---

## 12. Riscos identificados

> ⚠️ Coluna "Mitigação" corrigida em 2026-07-24 — a maioria descrevia mitigações inexistentes.

| Risco | Severidade | Mitigação **real hoje** |
|---|---|---|
| **Município homônimo em UF diferente** | **P1 vivo** | ❌ **Nenhuma.** UF é lida e descartada; desempate por `.first()` — [#1635](https://github.com/matheusnorjosa/aprender_sistema/issues/1635) |
| **Quantidade vazia/negativa/decimal aceita no preview** | **P1 vivo** | ❌ **Nenhuma** — vazio vira `0` e passa ([#1634](https://github.com/matheusnorjosa/aprender_sistema/issues/1634)) |
| **Data ausente gravada como `None`** | **P1 vivo** | ❌ **Nenhuma** — `data` não está na validação bloqueante (#1634) |
| **`Compra.produto` nunca preenchido** | **P1 vivo** | ❌ **Nenhuma** — não há FK no `defaults` (#1635) |
| **Reimport com `quantidade` corrigida duplica a linha** | **P1 vivo** | ❌ **Nenhuma** — `quantidade` e `uso` estão dentro do hash ([#1633](https://github.com/matheusnorjosa/aprender_sistema/issues/1633)) |
| `F` mal preenchido ou trocado entre linhas | Alta | ❌ Nenhuma — o código não resolve nada; só é gravado como texto |
| Produto com nome variante (acento, caixa) | Média | ⚠️ Parcial — `norm_text` + `_infer_projeto_from_produto`; se falhar, vira `pendencias.projetos` |
| Apply sem rastro de auditoria | Alta | ❌ Nenhuma — só o JSON sobrescrevível em `out_etl/` (§11) |
| Encoding latin-1 do Excel | Média | Especificar UTF-8 no template |
| Decimal com vírgula (`12,50`) | Baixa | ❌ `int(float("12,50"))` estoura → `quantidade=None` → linha rejeitada |

---

## 13. Pendências para Matheus (revistas — só as que o código ainda não responde)

### Resolvidas pelo código atual

- ~~`Compra` vs `DATCompra`?~~ → **Resolvido**: import atual alimenta `Compra`. `DATCompra` é fluxo operacional separado (Admin/UI), não importação.
- ~~Catálogo de Produtos é congelado?~~ → **Resolvido**: existe `produtos_import.py` + `POST /api/produtos/import/`. Catálogo é atualizável via planilha.

### Pendências reais ainda

1. **`valor_unitario` no `sheets.banco`**: o template original (7 colunas) não inclui. Se vier na planilha real, `Compra` aceita? (verificar schema do model — não confirmado).
2. **Granularidade**: 1 linha = 1 compra única, ou 1 linha = somatório por município/ano? Definir como o `external_hash` deve ser composto se for agregado.
3. **`Uso das coleções`** (campo texto livre): há vocabulário fechado (Alfabetização, Acompanhamento, Reposição) ou string livre?
4. 🔴 **Identidade real de `Compra`** — bloqueante. Hoje `quantidade` e `uso` fazem parte do
   `external_hash`, então corrigir uma quantidade na planilha **cria uma segunda linha** em vez de
   atualizar a primeira ([#1633](https://github.com/matheusnorjosa/aprender_sistema/issues/1633)).
   Decidir a chave de identidade (provável: `municipio + projeto + codigo + data`) antes de
   qualquer reimport em massa.
5. 🔴 **Invariantes de linha** — definir o que deve ser bloqueante: `quantidade >= 1`, `data`
   obrigatória e em faixa razoável, `codigo` existente em `Produto` (#1634).
6. 🔴 **UF na resolução de município** e **FK `Compra.produto`** (#1635).
7. **Cabeçalho real do CSV** que `controle_imports.py` aceita: confirmado em §15 (variantes
   `CÓD`/`COD`/`Cód`/`id`/`ID`, `Município`/`Municipio`, `Quant.`/`Quant`/`Quantidade`,
   `Uso das coleções`/`Uso`). Falta confirmar com Matheus qual variante `sheets.banco` exporta.
8. **Alinhar template CSV deste doc** com o cabeçalho real (§15).
9. **Auditoria**: decidir se o apply passa a gravar `AuditLog` ou se a migração para `ImportJob`
   (Fase 2 ASQ-005) resolve. Hoje só existe o JSON sobrescrevível em `out_etl/` (§11).

---

## 14. Histórico de versões

- 2026-05-05 — v0.1 — PR 1 (contrato inicial). Decisão `Compra` vs `DATCompra` pendente.
- 2026-05-05 — v0.2 — PR 1 v0.2. Auditoria contra código real. **`Compra` confirmado como destino** do import. Lista 7 services adjacentes já implementados. Reorienta roadmap.
- 2026-05-05 — v0.3 — PR 2. **Cabeçalho real confirmado** (`CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções` com variantes case/acento). Template atualizado. Shape de retorno documentado em [dry_run_response_contract.md](./dry_run_response_contract.md) (§3.2 família dataclass + JSON em disco).
- 2026-07-24 — v0.4 — Varredura de docs pós-auditoria M00–M28. Substituídas as referências a
  `DATCompra` por `Compra` em §1, §9 e §11. Registrados `M15-04`/#1634 (preview aceita quantidade
  vazia/negativa/decimal e data ausente), `M15-05`/#1635 (UF ignorada na resolução; `Compra.produto`
  nunca gravado; código do produto não resolve nada) e `M15-03`/#1633 (hash sobre campos mutáveis
  duplica linha). Corrigidas a chave natural (7 partes) e a ausência de `AuditLog`.

---

## 15. Cabeçalho real do CSV de Compras (confirmado em PR 2 — 2026-05-05)

Lendo `apps/core/services/controle_imports.py` linhas 156-163, o service aceita **múltiplas variantes** do mesmo cabeçalho:

| Campo destino | Variantes aceitas no CSV/XLSX |
|---|---|
| `codigo` | `CÓD` · `COD` · `Cód` · `id` · `ID` |
| `produto` | `Produto` |
| `quantidade` | `Quant.` · `Quant` · `Quantidade` |
| `municipio` | `Município` · `Municipio` |
| `uf` | `UF` |
| `data` | `Data` |
| `uso` | `Uso das coleções` · `Uso` |

O template [templates/produtos_controle.template.csv](./templates/produtos_controle.template.csv) foi atualizado em PR 2 para usar o cabeçalho da planilha original (`CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções`), pois é o que o service mais provavelmente recebe ao ler diretamente XLSX exportado do `sheets.banco`.

### Idempotência

Confirmado em `controle_imports.py:187-199`:

```text
external_hash = SHA1( municipio_id | projeto_id | codigo | produto_norm | quantidade | data | uso_norm )
```

`projeto_id` é **inferido** a partir do nome do produto via `_infer_projeto_from_produto(produto_norm)` (cache pré-construído de `Produto → Projeto`), **não vem do CSV**.

### Validações bloqueantes (`controle_imports.py:206-238`)

Linha é rejeitada (com entrada em `pendencias.linhas_invalidas`) se:
- `municipio` vazio, **OU**
- `quantidade` é `None` (parse de int estourou), **OU**
- `codigo` vazio.

Linha é rejeitada (em `pendencias.municipios` ou `pendencias.projetos`) se:
- `resolve_municipio(nome)` retornar `None` — ⚠️ **sem passar a UF**, **OU**
- `_infer_projeto_from_produto(produto_norm)` retornar `None`.

🔴 **O que essa lista NÃO rejeita** (achado `M15-04` / #1634):
`quantidade` vazia (vira `0` por `int(float(quant_raw or 0))`, `:172`), `quantidade` negativa,
`quantidade` decimal (truncada), e `data` ausente ou impossível de parsear (gravada como `None`).

### Shape de retorno (confirmado em `controle_imports.py:279-290`)

Padrão "dataclass + relatório JSON em disco" — ver [dry_run_response_contract.md §3.2](./dry_run_response_contract.md). É **diferente** do shape dos demais 8 services modernos (família "dict aninhado"). PR 6 futura unifica.
