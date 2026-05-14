# Importação: Produtos / Controle (Compras)

Status: PR 1 — contrato fechado, **backend já implementado** para vários fluxos (revisto 2026-05-05)
Versão: 2026-05-05 v0.2
Template: [templates/produtos_controle.template.csv](./templates/produtos_controle.template.csv)

> ⚠️ **Atualização v0.2**: a v0.1 tratava o service como "futuro" e deixava aberta a decisão `Compra` vs `DATCompra`. Verificação no código (`controle_imports.py:26`) confirma que **`import_compras_from_file` alimenta `Compra`** (não `DATCompra`). Existem ainda services separados para `Produto` (catálogo), `Municipio`, `Colecoes`, etc. Esta versão lista todos.

---

## 1. Objetivo

Importar registros de uso/aquisição de produtos por município, a partir da aba de "Controle" da planilha `sheets.banco`. Alimenta a tabela `DATCompra` (gestão operacional DAT) — ou alternativamente `Compra` (histórico ETL), conforme decisão de produto.

Cobre:
- Lookup de `Produto` por código (`F`).
- Lookup de `Municipio` por nome + UF.
- Lookup de `Projeto` (via `Produto.projeto`).
- Criação/atualização de `DATCompra` com idempotência via `external_hash`.

Não cobre:
- Criação de Produto novo (catálogo é cadastrado separadamente, ver `ordem_de_importacao.md` passo 5).
- Criação de Município novo (cadastro mestre).

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

### Bloqueantes
- `codigo` não existe em `Produto` → rejeitar (catálogo deve ser cadastrado antes).
- `quantidade` <= 0 ou não numérico.
- `municipio` + `uf` não existe em `Municipio`.
- `data` fora da faixa razoável (futuro distante > 7d ou passado anterior a 2020).
- `external_hash` duplicado **no próprio arquivo**.

### Avisos
- `produto_nome` da planilha diverge do `Produto.nome` do banco (sanity check) → aceitar mas avisar (pode ser typo na planilha).
- Linha com `external_hash` já existente no banco → ignorar (idempotência) com warning.
- `data` no futuro próximo (1-7 dias) → aceitar (pode ser agendamento).

---

## 7. Regras de duplicidade / hash

### Chave natural
Tupla: `(produto.codigo, municipio.id, projeto.id, data)`.

`projeto` é derivado de `Produto.projeto` (FK do catálogo). Cada produto pertence a um único projeto, então `projeto` não vem da planilha.

### `external_hash` (idempotência)

SHA1 (consistente com services legacy) ou SHA256 (novo padrão) sobre:
```text
normalize_text_key(codigo) + "|" + str(municipio.id) + "|" + str(projeto.id) + "|" + data.isoformat()
```

### Comportamento por match
| Hash existe | Linha igual | Ação |
|---|---|---|
| Não | — | Criar `DATCompra` |
| Sim | Sim (campos não-chave iguais) | Ignorar (idempotente) |
| Sim | Não (`quantidade`/`uso` diferentes) | **Atualizar** com warning explícito (drift entre planilha e banco) |

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

### Pode criar
- Novo `DATCompra` com `status_uso='disponivel'` (default do save() do model).
- `quantidade_utilizada=0` inicialmente (atualizado por outro fluxo).

### Pode atualizar
- `quantidade` (se planilha re-importa com valor diferente — warning).
- `uso` (texto livre, atualizar tolerado).
- `valor_unitario` (se vier — futuro).

---

## 10. O que NÃO deve acontecer automaticamente

- Criar `Produto` novo (catálogo deve estar completo antes).
- Criar `Municipio` novo (cadastro mestre separado).
- Marcar `status_uso=ESGOTADO` automaticamente — model já calcula em `save()` baseado em `quantidade_utilizada`, mas sem efeito colateral externo.
- Reduzir `quantidade` se planilha vier menor — gerar warning, deixar admin decidir.
- Deletar linhas que sumiram da planilha — soft-delete só via admin.

---

## 11. Como auditar depois

### AuditLog
```python
AuditLog.objects.filter(
    action="IMPORT_PRODUTOS_CONTROLE",
    created_at__gte=<timestamp>
).values(
    "usuario",
    "details__arquivo_hash",
    "details__linhas_criadas",
    "details__linhas_atualizadas",
    "details__linhas_ignoradas",
    "details__warnings_count",
)
```

### Drift check
- Comparar contagem por município: `DATCompra.objects.values("municipio").annotate(c=Count("id"))`.
- Listar drift quantidade: `DATCompra` com `quantidade != Compra` (legacy) para a mesma chave natural.
- Reconciliação: gerar relatório `produto × municipio × ano` e comparar com planilha original.

### Reports operacionais
- `view_compras_dashboard` (Diretoria + DAT) exibe dashboard.
- `view_compras_pendencias`, `view_compras_stats` para painéis específicos.

---

## 12. Riscos identificados

| Risco | Severidade | Mitigação |
|---|---|---|
| Produto com nome variante (acento, caixa) → lookup falha | Média | Lookup oficial por `codigo` (`F`); `Produto` é sanity check; rejeitar só se `F` não existe |
| `F` mal preenchido ou trocado entre linhas | Alta | Validar match `F` ↔ `Produto.nome` (warning se diverge) |
| Município duplicado (homônimos sem UF) | Alta | Sempre exigir `UF`; lookup conjunto |
| Quantidade negativa ou zero | Média | Bloqueante; importação rejeita |
| Data futura > 7 dias | Baixa | Warning; aceitar (pode ser agendamento) |
| Reimport com `quantidade` diferente | Média | Atualizar com warning explícito + AuditLog `details.before` |
| Encoding latin-1 do Excel | Média | Especificar UTF-8 no template; rejeitar decode |
| Decimal com vírgula (`12,50`) | Baixa | Normalizador converte; warning se ambíguo |

---

## 13. Pendências para Matheus (revistas — só as que o código ainda não responde)

### Resolvidas pelo código atual

- ~~`Compra` vs `DATCompra`?~~ → **Resolvido**: import atual alimenta `Compra`. `DATCompra` é fluxo operacional separado (Admin/UI), não importação.
- ~~Catálogo de Produtos é congelado?~~ → **Resolvido**: existe `produtos_import.py` + `POST /api/produtos/import/`. Catálogo é atualizável via planilha.

### Pendências reais ainda

1. **`valor_unitario` no `sheets.banco`**: o template original (7 colunas) não inclui. Se vier na planilha real, `Compra` aceita? (verificar schema do model — não confirmado).
2. **Granularidade**: 1 linha = 1 compra única, ou 1 linha = somatório por município/ano? Definir como o `external_hash` deve ser composto se for agregado.
3. **`Uso das coleções`** (campo texto livre): há vocabulário fechado (Alfabetização, Acompanhamento, Reposição) ou string livre?
4. **Atualização vs criação** em re-import com mesmo hash + `quantidade` diferente:
   - O código atual (a confirmar lendo `_process_row` de `controle_imports.py`) provavelmente **ignora** (idempotência total).
   - Se a regra desejada for **atualizar** (sobrescrever) ou **acumular**, exige PR de runtime separada.
5. **Cabeçalho real do CSV** que `controle_imports.py` aceita: a docstring (linhas 1-8) menciona "aba 🟥 COMPRAS". Confirmar com Matheus se planilha real tem essas mesmas colunas (`F`, `Produto`, `Quant.`, `Município`, `UF`, `Data`, `Uso das coleções`) **OU** colunas em snake_case (`codigo`, `produto_nome`, `quantidade`, etc.).
6. **Alinhar template CSV deste doc** com o cabeçalho real que `controle_imports.py` aceita (não confirmado se v0.1 do template está certo).

---

## 14. Histórico de versões

- 2026-05-05 — v0.1 — PR 1 (contrato inicial). Decisão `Compra` vs `DATCompra` pendente.
- 2026-05-05 — v0.2 — PR 1 v0.2. Auditoria contra código real. **`Compra` confirmado como destino** do import. Lista 7 services adjacentes já implementados. Reorienta roadmap.
- 2026-05-05 — v0.3 — PR 2. **Cabeçalho real confirmado** (`CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções` com variantes case/acento). Template atualizado. Shape de retorno documentado em [dry_run_response_contract.md](./dry_run_response_contract.md) (§3.2 família dataclass + JSON em disco).

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

### Validações bloqueantes (linhas 204-205)

Linha é rejeitada (com entrada em `pendencias.linhas_invalidas`) se:
- `municipio` vazio, **OU**
- `quantidade` é `None` (parse de int falhou), **OU**
- `codigo` vazio.

Linha é rejeitada (em `pendencias.municipios` ou `pendencias.projetos`) se:
- `resolve_municipio(nome)` retornar `None`, **OU**
- `_infer_projeto_from_produto(produto_norm)` retornar `None`.

### Shape de retorno (confirmado em `controle_imports.py:279-290`)

Padrão "dataclass + relatório JSON em disco" — ver [dry_run_response_contract.md §3.2](./dry_run_response_contract.md). É **diferente** do shape dos demais 8 services modernos (família "dict aninhado"). PR 6 futura unifica.
