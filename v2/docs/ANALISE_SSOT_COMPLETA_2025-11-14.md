# 🔍 Análise SSOT (Single Source of Truth) Completa

**Data**: 2025-11-14
**Objetivo**: Identificar gaps de modelagem entre planilhas originais e banco de dados PostgreSQL

---

## 📊 Conceito: SSOT (Single Source of Truth)

**Definição**: Sistema onde cada dado tem **uma única fonte autoritativa**, eliminando duplicação e inconsistências.

**Problema atual**: Dados críticos ainda dependem de planilhas Excel com lógica hardcoded no sistema, violando princípio SSOT.

---

## 🔴 GAP CRÍTICO: Modelo Produto Ausente

### Contexto

O sistema atual possui:
- ✅ **Projeto**: 46 projetos modelados no banco
- ✅ **Compra**: Registro de compras com `codigo` (string)
- ❌ **Produto**: **AUSENTE** - 139 produtos mapeados apenas em `produtos.xlsx`

### Fonte de Dados

**Planilha**: `v2/backend/data/csv-import/produtos.xlsx` (139 linhas)

**Estrutura identificada** (baseado em MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md):
- **Produto** (nome): Ex: "NOVO LENDO - Coleção 1", "GESTÃO ESCOLAR - Kit Básico"
- **Código**: Identificador único (ex: "NL-C1", "GE-KB")
- **Gerência**: FK para Gerencia (GERENCIA 2, GERENCIA 3, etc.)
- **Projeto**: FK para Projeto (NOVO LENDO, GESTÃO ESCOLAR, etc.)
- **Ativo**: Boolean (produto em uso)

### Problema Atual

#### 1. Compra.codigo é String (deveria ser FK)

**Arquivo**: `v2/backend/apps/core/models.py` (linhas 635-639)

```python
class Compra(models.Model):
    codigo = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Código da compra (ex: COMP-001)"
    )
    # ... resto do modelo ...
```

**Problema**:
- `codigo` é string livre, sem validação
- Não garante que produto existe em `produtos.xlsx`
- Impossível fazer JOIN direto com produtos
- Não aproveita constraints e índices do PostgreSQL

**Deveria ser**:
```python
class Compra(models.Model):
    produto = models.ForeignKey(
        "Produto",
        on_delete=models.PROTECT,
        related_name="compras",
        help_text="Produto comprado"
    )
    # codigo se torna Produto.codigo (unique)
```

#### 2. Lógica Hardcoded: `_infer_projeto_from_produto()`

**Arquivo**: `v2/backend/apps/core/services/controle_imports.py` (linhas 293-314)

```python
def _infer_projeto_from_produto(produto_norm: str) -> Projeto | None:
    """
    Infere projeto a partir do nome do produto normalizado.

    Heurísticas:
    - "NOVO LENDO" → resolve_projeto("Novo Lendo")
    - "GESTAO ESCOLAR" | "GESTÃO ESCOLAR" → resolve_projeto("Gestão Escolar")
    """
    if not produto_norm:
        return None

    key: str = produto_norm.upper()

    try:
        if "NOVO LENDO" in key:
            return resolve_projeto("Novo Lendo")
        if "GESTAO ESCOLAR" in key or "GESTÃO ESCOLAR" in key:
            return resolve_projeto("Gestão Escolar")
    except Exception:
        return None

    return None
```

**Problemas**:
- ❌ Apenas 2 produtos mapeados (de 139 totais)
- ❌ Heurística frágil (busca substring, não código exato)
- ❌ Quebra quando novo produto é adicionado (precisa alterar código)
- ❌ Sem garantia de consistência com `produtos.xlsx`
- ❌ Difícil manutenção e testes

**Deveria ser**:
```python
# Não precisa mais de inferência!
# Produto já tem FK para Projeto
compra.produto.projeto  # acesso direto via FK
```

#### 3. Cross-Reference Impossível

**Problema**: Sistema não valida se produtos em `Compras.xlsx` existem em `produtos.xlsx`.

**Cenário atual**:
1. ETL importa `Compras.xlsx`
2. Campo `codigo` é string livre
3. Se produto não existir em `produtos.xlsx` → **silenciosamente aceita código inválido**
4. Dados inconsistentes no banco

**Com modelo Produto**:
1. ETL importa `produtos.xlsx` primeiro
2. ETL importa `Compras.xlsx`
3. Tenta criar Compra com `produto_id` inexistente → **FK constraint FAIL**
4. Rejeita compra inválida → **qualidade de dados garantida**

---

## 🎯 Solução Proposta: Modelo Produto + Migration

### 1. Criar Modelo `Produto`

**Arquivo**: `v2/backend/apps/core/models.py`

```python
class Produto(models.Model):
    """
    SSOT: Produtos disponíveis para compra (substitui produtos.xlsx).

    Fonte: produtos.xlsx (139 produtos)

    Campos:
        - nome: Nome do produto (ex: "NOVO LENDO - Coleção 1")
        - codigo: Identificador único (ex: "NL-C1")
        - gerencia: FK para Gerencia (opcional)
        - projeto: FK para Projeto (obrigatório)
        - ativo: Boolean (produto disponível)

    Relacionamentos:
        - Produto → Gerencia (many-to-one, opcional)
        - Produto → Projeto (many-to-one, obrigatório)
        - Compra → Produto (many-to-one, obrigatório)
    """

    codigo = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Código único do produto (ex: NL-C1, GE-KB)"
    )
    nome = models.CharField(
        max_length=200,
        help_text="Nome completo do produto"
    )
    descricao = models.TextField(
        blank=True,
        help_text="Descrição detalhada do produto"
    )
    gerencia = models.ForeignKey(
        "Gerencia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produtos",
        help_text="Gerência responsável pelo produto"
    )
    projeto = models.ForeignKey(
        "Projeto",
        on_delete=models.PROTECT,
        related_name="produtos",
        help_text="Projeto ao qual o produto pertence"
    )
    ativo = models.BooleanField(
        default=True,
        help_text="Produto disponível para compra"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_produto"
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["codigo"]
        indexes = [
            models.Index(fields=["codigo", "ativo"]),
            models.Index(fields=["projeto", "gerencia"]),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nome}"
```

### 2. Migrar Compra.codigo → Compra.produto_id

**Migration 2-step** (sem perda de dados):

#### Step 1: Adicionar campo `produto` (nullable)

```python
# Migration 0037_add_produto_model_and_fk.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_mark_test_projects"),
    ]

    operations = [
        # 1. Criar modelo Produto
        migrations.CreateModel(
            name="Produto",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("codigo", models.CharField(max_length=50, unique=True, db_index=True)),
                ("nome", models.CharField(max_length=200)),
                ("descricao", models.TextField(blank=True)),
                ("gerencia", models.ForeignKey(..., null=True, blank=True)),
                ("projeto", models.ForeignKey(...)),
                ("ativo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),

        # 2. Adicionar Compra.produto (nullable temporariamente)
        migrations.AddField(
            model_name="compra",
            name="produto",
            field=models.ForeignKey(
                "Produto",
                on_delete=models.PROTECT,
                related_name="compras",
                null=True,  # Temporário!
                blank=True,
            ),
        ),
    ]
```

#### Step 2: Preencher `produto_id` a partir de `codigo`

```python
# Migration 0038_migrate_compra_codigo_to_produto.py

def migrate_compra_to_produto(apps, schema_editor):
    """
    Preenche Compra.produto_id baseado em Compra.codigo.

    Estratégia:
    1. Para cada Compra:
        a. Tentar match exato: Produto.codigo == Compra.codigo
        b. Se não houver match, criar Produto "orphan" (projeto genérico)
        c. Atualizar Compra.produto_id
    2. Depois que todas as Compras tiverem produto_id preenchido:
        a. Tornar Compra.produto NOT NULL
        b. Remover Compra.codigo (obsoleto)
    """
    Compra = apps.get_model("core", "Compra")
    Produto = apps.get_model("core", "Produto")
    Projeto = apps.get_model("core", "Projeto")

    # Projeto genérico para produtos órfãos
    projeto_generico, _ = Projeto.objects.get_or_create(
        nome="Produtos Diversos",
        defaults={"fluxo": "NAO_SUPER", "ativo": True}
    )

    compras_sem_produto = 0
    compras_migradas = 0

    for compra in Compra.objects.filter(produto__isnull=True):
        # Tentar encontrar produto existente
        produto = Produto.objects.filter(codigo=compra.codigo).first()

        if not produto:
            # Criar produto órfão
            produto = Produto.objects.create(
                codigo=compra.codigo,
                nome=f"Produto Legado {compra.codigo}",
                projeto=projeto_generico,
                ativo=False,  # Marcar como inativo (legado)
            )
            compras_sem_produto += 1

        # Atualizar FK
        compra.produto = produto
        compra.save(update_fields=["produto"])
        compras_migradas += 1

    print(f"✅ Migrated {compras_migradas} compras")
    print(f"⚠️  Created {compras_sem_produto} orphan produtos")

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0037_add_produto_model_and_fk"),
    ]

    operations = [
        migrations.RunPython(migrate_compra_to_produto, migrations.RunPython.noop),

        # Tornar produto obrigatório
        migrations.AlterField(
            model_name="compra",
            name="produto",
            field=models.ForeignKey(
                "Produto",
                on_delete=models.PROTECT,
                related_name="compras",
                null=False,  # Agora obrigatório!
            ),
        ),

        # Remover campo codigo (obsoleto)
        migrations.RemoveField(
            model_name="compra",
            name="codigo",
        ),
    ]
```

### 3. ETL para Importar produtos.xlsx

**Arquivo**: `v2/backend/apps/dat_ingest/management/commands/import_produtos.py`

```python
"""
ETL para importação de produtos.xlsx.

Usage:
    python manage.py import_produtos --dry-run  # Preview
    python manage.py import_produtos --apply    # Apply

Idempotence:
    - Upsert por Produto.codigo (unique constraint)
    - Atualiza nome, projeto, gerencia se mudarem

Quality Gates:
    - Min 100 produtos válidos (threshold configurável)
    - Todos os projetos referenciados devem existir
    - Todas as gerências referenciadas devem existir

Output:
    - Relatório JSON em out_etl/import_produtos_YYYYMMDD_HHMMSS.json
"""

class Command(BaseCommand):
    help = "Importa produtos.xlsx para modelo Produto"

    def handle(self, *args, **opts):
        # 1. Parse produtos.xlsx (139 linhas)
        # 2. Normalizar nomes de projetos e gerências
        # 3. Resolver FKs (Projeto, Gerencia)
        # 4. Quality gates
        # 5. Upsert Produto (get_or_create por codigo)
        # 6. Gerar relatório JSON
```

### 4. Eliminar `_infer_projeto_from_produto()`

**Antes** (`controle_imports.py:211`):
```python
proj_obj: Projeto | None = _infer_projeto_from_produto(r["produto_norm"])
if not proj_obj:
    stats.skipped += 1
    pendencias.projetos.append({"row": i, "produto": r["produto"]})
    continue
```

**Depois**:
```python
# Buscar produto por código
produto_obj = Produto.objects.filter(codigo=r["codigo"]).first()
if not produto_obj:
    stats.skipped += 1
    pendencias.produtos.append({"row": i, "codigo": r["codigo"]})
    continue

# Projeto vem direto do produto (FK)
proj_obj = produto_obj.projeto
```

---

## 📋 Checklist de Implementação

### Backend

- [ ] **Modelo `Produto`** (`apps/core/models.py`)
  - [ ] Campos: codigo (unique), nome, descricao, gerencia (FK), projeto (FK), ativo
  - [ ] Meta: db_table, ordering, indexes
  - [ ] `__str__()` method

- [ ] **Migration 0037**: Criar modelo Produto + adicionar Compra.produto (nullable)

- [ ] **Migration 0038**: Migrar Compra.codigo → Compra.produto_id + remover codigo
  - [ ] Data migration: preencher produto_id
  - [ ] Criar produtos órfãos para códigos sem match
  - [ ] AlterField: tornar produto obrigatório (NOT NULL)
  - [ ] RemoveField: remover Compra.codigo

- [ ] **Serializers** (`apps/core/serializers.py`)
  - [ ] `ProdutoSerializer` (fields: id, codigo, nome, descricao, gerencia, projeto, ativo)
  - [ ] Atualizar `CompraSerializer` (substituir codigo por produto nested)

- [ ] **Views** (`apps/core/views.py`)
  - [ ] `ProdutoViewSet` (CRUD, filtros por projeto/gerencia/ativo)
  - [ ] Permissões: DAT pode criar/editar, outros readonly

- [ ] **URLs** (`apps/core/urls.py`)
  - [ ] `router.register(r"produtos", ProdutoViewSet)`

- [ ] **ETL**: `import_produtos` command
  - [ ] Parser para produtos.xlsx (139 linhas)
  - [ ] Resolver FKs (Projeto, Gerencia)
  - [ ] Quality gates (min 100 produtos, projetos existem)
  - [ ] Upsert por codigo (idempotente)
  - [ ] Relatório JSON

- [ ] **Remover lógica hardcoded**
  - [ ] Deletar função `_infer_projeto_from_produto()` (controle_imports.py:293-314)
  - [ ] Atualizar `import_acoes_controle()` para usar `Produto.objects.get(codigo=...)`

### Testes

- [ ] **Model tests** (`test_produto_model.py`)
  - [ ] `test_produto_creation`
  - [ ] `test_produto_codigo_unique_constraint`
  - [ ] `test_produto_projeto_relationship`
  - [ ] `test_compra_requires_produto` (FK constraint)

- [ ] **API tests** (`test_produto_api.py`)
  - [ ] `test_list_produtos`
  - [ ] `test_filter_produtos_by_projeto`
  - [ ] `test_dat_can_create_produto`
  - [ ] `test_coordenador_cannot_create_produto`

- [ ] **Migration tests** (`test_migrate_compra_to_produto.py`)
  - [ ] `test_migration_preserves_all_compras`
  - [ ] `test_migration_creates_orphan_produtos`
  - [ ] `test_compra_codigo_field_removed`

- [ ] **ETL tests** (`test_import_produtos_command.py`)
  - [ ] `test_import_produtos_dry_run`
  - [ ] `test_import_produtos_apply_creates_139`
  - [ ] `test_import_produtos_idempotence`
  - [ ] `test_import_produtos_quality_gates`

### Documentação

- [ ] Atualizar `PLANO_GERENCIAS_SETORES.md` (adicionar Task 7)
- [ ] Atualizar `CLAUDE.md` (remover menção a `_infer_projeto_from_produto`)
- [ ] Criar `ANALISE_SSOT_COMPLETA_2025-11-14.md` (este documento)

---

## 🎯 Benefícios Esperados

### 1. Integridade de Dados (Database-Level)
- ✅ FK constraints impedem compras com produtos inexistentes
- ✅ Unique constraint em Produto.codigo evita duplicação
- ✅ PROTECT impede deletar produtos com compras vinculadas

### 2. Eliminação de Hardcoded Logic
- ✅ Sem mais `_infer_projeto_from_produto()` (2 produtos → 139 produtos)
- ✅ Mapeamento produto→projeto no banco (não no código)
- ✅ Fácil adicionar novos produtos (INSERT, não deploy)

### 3. Queries Otimizadas
- ✅ JOIN direto: `Compra.objects.select_related('produto__projeto')`
- ✅ Filtros eficientes: `Compra.objects.filter(produto__gerencia__nome='GERENCIA 2')`
- ✅ Índices PostgreSQL em FKs (performance)

### 4. Auditoria e Relatórios
- ✅ "Quais produtos mais comprados por gerência?"
  ```sql
  SELECT g.nome_setor, p.nome, COUNT(c.id)
  FROM core_compra c
  JOIN core_produto p ON c.produto_id = p.id
  JOIN core_gerencia g ON p.gerencia_id = g.id
  GROUP BY g.nome_setor, p.nome
  ORDER BY COUNT(c.id) DESC
  ```

### 5. Cross-Reference Automático
- ✅ ETL valida produtos em Compras.xlsx contra produtos.xlsx
- ✅ Rejeita compras com códigos inválidos (qualidade de dados)
- ✅ Relatório de produtos órfãos (não mapeados em produtos.xlsx)

---

## ⚠️ Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Compras.xlsx tem códigos não em produtos.xlsx | Alta | Médio | Migration cria produtos órfãos (ativo=False) |
| produtos.xlsx tem projetos não no banco | Baixa | Alto | Quality gate em ETL rejeita linha inválida |
| Migration 0038 falha com dados grandes | Baixa | Alto | Testar com backup, rollback automático |
| Performance de JOIN produto→projeto | Baixa | Baixo | Índices em FKs, select_related() |

---

## 📊 Impacto Estimado

**Arquivos modificados**: 12
**Linhas de código**: ~800
**Migrations**: 2 (0037 schema, 0038 data)
**Testes**: 15+
**Tempo estimado**: 6-8 horas

**Prioridade**: **P0 (Crítico)** - Bloqueia consolidação de Compras + elimina hardcoded logic

---

## 🔗 Referências

- **produtos.xlsx**: 139 produtos mapeados a projetos e gerências
- **Compras.xlsx**: ~200 compras referenciando produtos por código
- **MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md**: Análise de gerências e projetos
- **PLANO_GERENCIAS_SETORES.md**: Plano geral de implementação (Tasks 1-6)

---

**Gerado em**: 2025-11-14 21:15
**Responsável**: Claude Code (Automated Analysis)
**Status**: 🔴 GAP CRÍTICO - Aguardando implementação
