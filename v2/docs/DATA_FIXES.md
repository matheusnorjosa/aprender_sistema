# Data Fixes — Aprender Sistema v2

Este documento registra correções e transformações de dados aplicadas ao banco de dados do AS v2.

---

## Issue #150 — Consolidação de Projetos Duplicados (2025-11-17)

**Problema**: Existiam 3 pares de projetos duplicados no banco de dados com nomes variantes, causando inconsistências em imports ETL e queries.

**Solução**: Data migration `0036_consolidate_duplicate_projetos.py` que:
1. Identifica pares duplicados
2. Atualiza todas as FKs para o projeto canônico
3. Remove projetos duplicados
4. Cria helper `project_normalizer.py` para normalização futura

### Pares Consolidados

| Duplicado (REMOVIDO) | Canônico (MANTIDO) | Fluxo |
|---|---|---|
| `LEIO ESCREVO E CALCULO` | `LEIO, ESCREVO E CALCULO` | NAO_SUPER |
| `Gestão Escolar` | `GESTÃO ESCOLAR` | NAO_SUPER |
| `LER OUVIR E CONTAR` | `LER, OUVIR E CONTAR` | NAO_SUPER |

### Nomes Canônicos e Variantes Conhecidas

O helper `apps/core/services/project_normalizer.py` mapeia variantes conhecidas:

#### LEIO, ESCREVO E CALCULO (Canônico)
Variantes:
- `LEIO ESCREVO E CALCULO` (sem vírgulas)
- `LEIO,ESCREVO E CALCULO` (vírgula sem espaço)
- `LEIO ESCREVO E CÁLCULO` (sem vírgulas, com acento)
- `LEIO, ESCREVO E CÁLCULO` (com acento)

#### GESTÃO ESCOLAR (Canônico)
Variantes:
- `GESTAO ESCOLAR` (sem acentos uppercase)
- `Gestao Escolar` (sem acentos mixed case)
- `IDEB10` (nome antigo/legado)

**Nota**: `Gestão Escolar` (mixed case COM acentos) não precisa estar explicitamente na lista, pois `.upper()` já converte para o canônico `GESTÃO ESCOLAR`.

#### LER, OUVIR E CONTAR (Canônico)
Variantes:
- `LER OUVIR E CONTAR` (sem vírgulas)
- `LER,OUVIR E CONTAR` (vírgula sem espaço)
- `LER OUVIR CONTAR` (sem vírgulas e sem "E")

### Modelos Afetados

A migration atualizou FKs nos seguintes modelos:
- `Solicitacao` (projeto FK)
- `AcaoControle` (projeto FK)
- `AcaoDAT` (projeto FK)
- `Compra` (projeto FK)

### Uso do Normalizer

```python
from apps.core.services.project_normalizer import (
    normalize_project_name,
    is_known_variant,
    get_canonical_name,
)

# Normalizar nome de projeto
normalize_project_name("LEIO ESCREVO E CALCULO")  # → "LEIO, ESCREVO E CALCULO"
normalize_project_name("IDEB10")  # → "GESTÃO ESCOLAR"

# Verificar se é variante conhecida
is_known_variant("IDEB10")  # → True
is_known_variant("GESTÃO ESCOLAR")  # → False (é canônico)

# Obter canônico se for variante
get_canonical_name("IDEB10")  # → "GESTÃO ESCOLAR"
get_canonical_name("GESTÃO ESCOLAR")  # → None (já é canônico)
```

### Testes

**Normalizer** (`apps/core/tests/test_project_normalizer.py`):
- 34 testes cobrindo normalização, detecção de variantes, e integração
- Valida todos os casos: uppercase, lowercase, com/sem acentos, com/sem vírgulas

**Migration** (`apps/core/tests/test_project_dedup_migration.py`):
- 11 testes cobrindo:
  - Consolidação de cada par
  - Atualização de FKs
  - Deleção de duplicados
  - Idempotência
  - Edge cases (canônico já existe, duplicado ausente, banco vazio)

### Arquivos Relacionados

**Migration**:
- `v2/backend/apps/core/migrations/0036_consolidate_duplicate_projetos.py`

**Helper Service**:
- `v2/backend/apps/core/services/project_normalizer.py`

**Testes**:
- `v2/backend/apps/core/tests/test_project_normalizer.py` (34 testes)
- `v2/backend/apps/core/tests/test_project_dedup_migration.py` (11 testes)

**Documentação**:
- `v2/docs/PLANO_GERENCIAS_SETORES.md` (Task 3 - status atualizado)
- `v2/docs/DATA_FIXES.md` (este arquivo)

### Próximos Passos

**Para novos imports ETL**:
1. Sempre use `normalize_project_name()` antes de buscar/criar projetos
2. Exemplo:
```python
from apps.core.services.project_normalizer import normalize_project_name

nome_planilha = "LEIO ESCREVO E CALCULO"  # Vem da planilha
nome_normalizado = normalize_project_name(nome_planilha)  # "LEIO, ESCREVO E CALCULO"

projeto, created = Projeto.objects.get_or_create(
    nome=nome_normalizado,
    defaults={"fluxo": "NAO_SUPER", "ativo": True}
)
```

**Para adicionar novas variantes**:
1. Edite `CANONICAL_PROJECT_NAMES` em `project_normalizer.py`
2. Adicione testes em `test_project_normalizer.py`
3. Rodar testes: `pytest apps/core/tests/test_project_normalizer.py -v`

---

## Issue #152 — Correção de Fluxo de Projetos SUPER (2025-11-17)

**Problema**: 4 projetos estavam incorretamente marcados com `fluxo='NAO_SUPER'` (auto-aprovação) quando deveriam ser `fluxo='SUPER'` (aprovação manual pela Superintendência), violando a Política de Aprovação Manual (PA-01 a PA-07).

**Solução**: Data migration `0037_fix_superintendencia_fluxo.py` que atualiza o campo `fluxo` de NAO_SUPER para SUPER nos 4 projetos afetados.

### Projetos Corrigidos

| Projeto | Fluxo Anterior | Fluxo Corrigido | Razão |
|---|---|---|---|
| `LER OUVIR E CONTAR` | NAO_SUPER | SUPER | Listado na aba "Super" da planilha |
| `LER, OUVIR E CONTAR` | NAO_SUPER | SUPER | Listado na aba "Super" da planilha |
| `PROJETO CATAVENTO 2` | NAO_SUPER | SUPER | Variante de Cataventos (projeto SUPER) |
| `PROJETO CATAVENTO 3` | NAO_SUPER | SUPER | Variante de Cataventos (projeto SUPER) |

**Nota**: Ambas variantes "LER OUVIR E CONTAR" (sem vírgulas) e "LER, OUVIR E CONTAR" (com vírgulas) foram corrigidas.

### Impacto

**Comportamento Anterior** (INCORRETO):
- Solicitações para estes 4 projetos eram auto-aprovadas (`status='aprovado'` na criação)
- Violação de PA-01: "Sem auto-aprovação"

**Comportamento Após Correção** (CORRETO):
- Novas solicitações para estes projetos iniciam com `status='pendente'`
- Requerem aprovação manual pela Superintendência (conforme PA-01 a PA-07)
- Histórico de solicitações antigas permanece intacto (apenas lógica futura muda)

### Auditoria Recomendada

Para verificar se há solicitações que foram auto-aprovadas indevidamente no passado:

```sql
-- Solicitações aprovadas para os 4 projetos (potencialmente auto-aprovadas)
SELECT s.id, s.created_at, s.status, p.nome AS projeto_nome
FROM core_solicitacao s
JOIN core_projeto p ON s.projeto_id = p.id
WHERE p.nome IN (
  'LER OUVIR E CONTAR',
  'LER, OUVIR E CONTAR',
  'PROJETO CATAVENTO 2',
  'PROJETO CATAVENTO 3'
)
AND s.status = 'aprovado'
ORDER BY s.created_at DESC;
```

### Testes

**Migration** (`apps/core/tests/test_fix_superintendencia_migration.py`):
- 9 testes cobrindo:
  - Correção de variantes LER/OUVIR/CONTAR
  - Correção de CATAVENTO 2/3
  - Preservação de outros projetos
  - Idempotência (rodar 2x não quebra)
  - Skip de projetos já SUPER
  - Reversibilidade (rollback)
  - Graceful handling de projetos ausentes
  - Contadores corretos

**Todos os 9 testes passando** ✅

### Arquivos Relacionados

**Migration**:
- `v2/backend/apps/core/migrations/0037_fix_superintendencia_fluxo.py`

**Testes**:
- `v2/backend/apps/core/tests/test_fix_superintendencia_migration.py` (9 testes)

**Documentação**:
- `v2/docs/PLANO_GERENCIAS_SETORES.md` (Task 5 - status atualizado)
- `v2/docs/DATA_FIXES.md` (este arquivo)

### Reversão (Se Necessário)

A migration é reversível. Para reverter:

```bash
docker compose exec web python manage.py migrate core 0036
```

Isso restaura os 4 projetos para `fluxo='NAO_SUPER'`.

---

## Template para Futuras Correções

Ao aplicar correções de dados no futuro, documente aqui seguindo o template:

### Issue #XXX — Título da Correção (Data)

**Problema**: Descreva o problema encontrado

**Solução**: Descreva a abordagem

**Dados Afetados**: Liste tabelas/registros

**Migration**: `XXXX_nome_migration.py`

**Testes**: Localização e cobertura

**Arquivos Relacionados**: Liste arquivos criados/modificados

---

**Última atualização**: 2025-11-17 (Issue #152)
