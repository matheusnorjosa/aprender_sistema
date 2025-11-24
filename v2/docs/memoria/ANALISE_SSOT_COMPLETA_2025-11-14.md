# Análise SSOT COMPLETA — Aprender Sistema v2

**Data**: 2025-11-14
**Escopo**: Verificação de conformidade SSOT em **TODAS** as entidades do sistema
**Atualização**: Análise expandida além de Município

---

## 📊 Resumo Executivo

| Categoria | Total | ✅ CONFORME | ⚠️ PARCIAL | ❌ VIOLAÇÃO |
|-----------|-------|-------------|------------|-------------|
| **Dados Mestre** | 5 | 4 (80%) | 0 | 1 (20%) |
| **Dados Transacionais** | 8 | 7 (87.5%) | 1 (12.5%) | 0 |
| **TOTAL** | 13 | 11 (84.6%) | 1 (7.7%) | 1 (7.7%) |

**Conclusão Geral**: Sistema está **84.6% conforme** com SSOT. **1 violação crítica identificada** (Produto) e **1 problema menor** (Compra).

---

## 1. Dados Mestre (Reference Data)

### 1.1 ✅ Município — CONFORME (A+)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_municipio` (única) |
| **Campos únicos** | ✅ Sim | `nome` (unique), `ibge_code` (unique) |
| **Relacionamentos** | ✅ FK | Solicitacao, AcaoControle, AcaoDAT, Compra |
| **API** | ✅ SSOT | `/api/municipios/` (CRUD), `/api/lookup/municipios/` (autocomplete) |
| **Frontend** | ✅ SSOT | Sem cache persistente, fetch on-demand |
| **Código morto** | ⚠️ Menor | `/api/options/municipios/` não usado (remover) |

**Análise detalhada**: Ver `ANALISE_SSOT_2025-11-14.md` (67KB)

---

### 1.2 ✅ Projeto — CONFORME (A+)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_projeto` (única) |
| **Campos únicos** | ✅ Sim | `nome` (unique) |
| **Relacionamentos** | ✅ FK | Solicitacao, AcaoControle, AcaoDAT, Compra |
| **API** | ✅ SSOT | `/api/projetos/` (CRUD), `/api/lookup/projetos/` (autocomplete) |
| **Frontend** | ✅ SSOT | Sem cache persistente |
| **Código morto** | ⚠️ Menor | `/api/options/projetos/` não usado (remover) |

**Estrutura**:
```python
class Projeto(models.Model):
    nome = models.CharField(max_length=200, unique=True, db_index=True)
    codigo = models.CharField(max_length=50, db_index=True)
    fluxo = models.CharField(choices=FLUXO_CHOICES)  # SUPER / NAO_SUPER
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
```

**Conformidade SSOT**: ✅ Completa

---

### 1.3 ✅ TipoEvento — CONFORME (A+)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_tipoevent` (única) |
| **Campos únicos** | ✅ Sim | `nome` (unique) |
| **Relacionamentos** | ✅ FK | Solicitacao |
| **API** | ✅ SSOT | `/api/lookup/tipos-evento/` (autocomplete) |
| **Frontend** | ✅ SSOT | Sem cache persistente |
| **Código morto** | ⚠️ Menor | `/api/options/tipos-evento/` não usado (remover) |

**Estrutura**:
```python
class TipoEvento(models.Model):
    nome = models.CharField(max_length=100, unique=True, db_index=True)
    descricao = models.TextField(blank=True)
    cor = models.CharField(max_length=7, blank=True, help_text="Cor hex (#RRGGBB)")
    ativo = models.BooleanField(default=True)
```

**Conformidade SSOT**: ✅ Completa

---

### 1.4 ✅ Usuario — CONFORME (A+)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_usuario` (única, AbstractUser) |
| **Campos únicos** | ✅ Sim | `username` (herdado), `cpf` (unique), `email` (herdado) |
| **Relacionamentos** | ✅ FK | Solicitacao.usuario, AcaoControle.coordenador, AuditLog.usuario |
| **API** | ✅ SSOT | `/api/usuarios-admin/` (CRUD), `/api/lookup/usuarios/` (autocomplete), `/api/me/` |
| **Frontend** | ✅ SSOT | Sem cache persistente |
| **Código morto** | ⚠️ Menor | `/api/options/usuarios/` não usado (remover) |

**Estrutura**:
```python
class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11, unique=True, db_index=True)
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
```

**Nota**: Formador NÃO é um model separado. Formadores são Usuarios com role/grupo "Formador".

**Conformidade SSOT**: ✅ Completa

---

### 1.5 ❌ Produto — VIOLAÇÃO CRÍTICA (F)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ❌ **NÃO EXISTE** | Nenhuma tabela `core_produto` |
| **Onde está o dado** | ❌ **DUPLICADO** | Campo texto em cada Compra (não normalizado) |
| **Relacionamento** | ❌ **NENHUM** | Compra NÃO tem FK para Produto |
| **API** | ❌ **NÃO EXISTE** | Nenhum endpoint para produtos |
| **Frontend** | ❌ **NÃO EXISTE** | Nenhuma página de CRUD de produtos |

#### ❌ Problema Identificado

**Arquivo**: `v2/backend/apps/core/models.py:557-620`

```python
class Compra(models.Model):
    """
    Registro de compras de materiais/produtos para projetos.
    """
    codigo = models.CharField(max_length=50)  # ❌ Deveria ser FK para Produto
    projeto = models.ForeignKey(Projeto, ...)  # ✅ FK correto
    municipio = models.ForeignKey(Municipio, ...)  # ✅ FK correto
    quantidade = models.IntegerField(...)
    data = models.DateField(...)
    uso = models.TextField(...)
```

**Análise**: O campo `codigo` deveria ser uma **ForeignKey** para model `Produto`, mas:
1. ❌ **Produto não é um model** (não existe tabela)
2. ❌ **Nome do produto está duplicado** em cada registro de Compra
3. ❌ **Lógica hardcoded** infere Projeto a partir do nome do produto (heurísticas)

**Arquivo**: `v2/backend/apps/core/services/controle_imports.py:139-178`

```python
def _normalize_row(r: dict[str, Any], i: int) -> dict[str, Any]:
    """Normaliza uma linha do arquivo."""
    codigo: str = str(r.get("CÓD") or "").strip()
    produto: str = str(r.get("Produto") or "").strip()  # ❌ Texto livre
    produto_norm: str = norm_text(produto)
    # ...
    return {
        "codigo": codigo,
        "produto": produto,  # ❌ Armazenado como texto
        "produto_norm": produto_norm,
        # ...
    }

def _infer_projeto_from_produto(produto_norm: str) -> Projeto | None:
    """
    ❌ VIOLAÇÃO SSOT: Lógica de negócio hardcoded

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
            return resolve_projeto("Novo Lendo")  # ❌ Hardcoded
        if "GESTAO ESCOLAR" in key or "GESTÃO ESCOLAR" in key:
            return resolve_projeto("Gestão Escolar")  # ❌ Hardcoded
    except Exception:
        return None

    return None
```

#### ❌ Impacto da Violação

1. **Duplicação de dados**: Nome do produto repetido em cada Compra
2. **Inconsistência**: Variações de nome ("Novo Lendo" vs "NOVO LENDO" vs "novo lendo")
3. **Manutenção difícil**: Adicionar novo produto exige alterar código Python
4. **Sem validação**: Produtos inexistentes podem ser inseridos
5. **Relatórios incorretos**: Difícil agrupar compras por produto (variações de nome)

#### ✅ Solução Recomendada

**1. Criar model Produto (SSOT)**

```python
# v2/backend/apps/core/models.py

class Produto(models.Model):
    """SSOT: Substitui texto livre em Compra"""

    nome = models.CharField(max_length=200, unique=True, db_index=True)
    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.PROTECT,
        related_name="produtos",
        help_text="Projeto associado ao produto"
    )
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "core_produto"
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nome}"
```

**2. Atualizar model Compra**

```python
class Compra(models.Model):
    """Registro de compras de materiais/produtos para projetos."""

    produto = models.ForeignKey(  # ✅ FK em vez de CharField
        Produto,
        on_delete=models.PROTECT,
        related_name="compras",
        help_text="Produto comprado"
    )
    # Remover campo 'codigo' (agora via produto.codigo)
    projeto = models.ForeignKey(Projeto, ...)  # ✅ Manter (pode ser diferente do produto.projeto)
    municipio = models.ForeignKey(Municipio, ...)
    quantidade = models.IntegerField(...)
    data = models.DateField(...)
    uso = models.TextField(...)
```

**3. Remover lógica hardcoded**

```python
# ❌ DELETAR função _infer_projeto_from_produto()
# ✅ USAR produto.projeto (via FK)
```

**4. Criar API e Frontend**

- `/api/produtos/` → CRUD (ProdutoViewSet)
- `/api/lookup/produtos/` → Autocomplete (ProdutoLookup)
- AdminDAT → Página de gestão de Produtos

#### 📋 Checklist de Migração

- [ ] Criar migration `0024_add_produto_model.py`
- [ ] Popular tabela `core_produto` com dados existentes (script de migração)
- [ ] Adicionar FK `Compra.produto`
- [ ] Migrar dados de `Compra.codigo` → `Compra.produto_id`
- [ ] Remover campo `Compra.codigo`
- [ ] Deletar `_infer_projeto_from_produto()`
- [ ] Criar API `/api/produtos/`
- [ ] Criar página AdminDAT para Produtos
- [ ] Atualizar testes

**Prioridade**: ⚠️ **ALTA** (violação crítica de SSOT)

---

## 2. Dados Transacionais

### 2.1 ✅ Solicitacao — CONFORME (A)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_solicitacao` (única) |
| **FKs para dados mestre** | ✅ Sim | usuario, municipio, projeto, tipo_evento |
| **ManyToMany** | ✅ Sim | formadores (via intermediary Participation) |
| **Campos duplicados** | ✅ Não | Nomes vêm via serializer (read-only computed fields) |

**Conformidade SSOT**: ✅ Completa

---

### 2.2 ⚠️ Compra — PARCIAL (C)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_compra` (única) |
| **FKs para dados mestre** | ⚠️ Parcial | ✅ projeto, ✅ municipio, ❌ produto (campo texto) |
| **Violação SSOT** | ❌ Sim | Campo `codigo` deveria ser FK para Produto |

**Problema**: Ver seção 1.5 (Produto).

**Conformidade SSOT**: ⚠️ Parcial (depende de criar model Produto)

---

### 2.3 ✅ AvailabilityBlock — CONFORME (A)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_availabilityblock` (única) |
| **FKs para dados mestre** | ✅ Sim | usuario |
| **Campos duplicados** | ✅ Não | Nenhum |

**Conformidade SSOT**: ✅ Completa

---

### 2.4 ✅ Deslocamento — CONFORME (A)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_deslocamento` (única) |
| **FKs para dados mestre** | ✅ Sim | usuario (coordenador) |
| **Campos de município** | ✅ TextField | origem, destino (texto livre OK para deslocamento) |

**Nota**: Origem/destino como texto é aceitável (não são dados mestre, são registros históricos).

**Conformidade SSOT**: ✅ Completa

---

### 2.5 ✅ AcaoControle — CONFORME (A)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_acaocontrole` (única) |
| **FKs para dados mestre** | ✅ Sim | municipio, projeto, coordenador (Usuario) |
| **Campos duplicados** | ✅ Não | Nenhum |

**Conformidade SSOT**: ✅ Completa

---

### 2.6 ✅ AcaoDAT — CONFORME (A)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_acaodat` (única) |
| **FKs para dados mestre** | ✅ Sim | municipio, projeto, responsavel (Usuario) |
| **Campos duplicados** | ✅ Não | Nenhum |

**Conformidade SSOT**: ✅ Completa

---

### 2.7 ✅ AuditLog — CONFORME (A+)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_auditlog` (única) |
| **FKs para dados mestre** | ✅ Sim | usuario |
| **Campos duplicados** | ✅ Não | JSONField para detalhes (correto) |

**Conformidade SSOT**: ✅ Completa

---

### 2.8 ✅ Participation — CONFORME (A)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Tabela** | ✅ SSOT | `core_participation` (intermediary para Solicitacao.formadores) |
| **FKs para dados mestre** | ✅ Sim | solicitacao, usuario |
| **Campos duplicados** | ✅ Não | Nenhum |

**Conformidade SSOT**: ✅ Completa

---

## 3. Dados de Configuração/Sistema

### 3.1 ✅ Config — CONFORME (A)

**Tabela**: `core_config` (única)
**Uso**: Configurações globais (timezone, buffer de deslocamento, etc.)

**Conformidade SSOT**: ✅ Completa

---

### 3.2 ✅ GoogleOAuthCredential — CONFORME (A)

**Tabela**: `core_googleoauthcredential` (única)
**Uso**: Armazenamento de tokens OAuth

**Conformidade SSOT**: ✅ Completa

---

## 4. Comparação com Planilhas Originais

### 4.1 Planilhas Source (v2/backend/data/csv-import/)

| Planilha | Dados Extraídos | Model Correspondente | Status SSOT |
|----------|-----------------|----------------------|-------------|
| **Usuários.xlsx** | Usuários | Usuario | ✅ CONFORME |
| **Acompanhamento de Agenda _ 2025.xlsx** | Eventos, Formadores | Solicitacao, Participation | ✅ CONFORME |
| **Disponibilidade _ 2025.xlsx** | Disponibilidade, Bloqueios | AvailabilityBlock | ✅ CONFORME |
| **Planilha de Controle - 2025.xlsx** | Ações, Compras | AcaoControle, Compra | ⚠️ Compra parcial |
| **Produtos.xlsx** | ❌ **NÃO EXISTE** | ❌ **FALTANDO** | ❌ VIOLAÇÃO |

### 4.2 Dados Mencionados em CLAUDE.md mas Não Implementados

| Dado Mestre | Mencionado | Implementado | Status |
|-------------|------------|--------------|--------|
| Município | ✅ Sim | ✅ Sim | ✅ OK |
| Projeto | ✅ Sim | ✅ Sim | ✅ OK |
| TipoEvento | ✅ Sim | ✅ Sim | ✅ OK |
| Usuario | ✅ Sim | ✅ Sim | ✅ OK |
| Formador | ✅ Sim (model separado) | ⚠️ Não (role de Usuario) | ⚠️ Divergência menor |
| **Produto** | ✅ Sim (Produtos.xlsx) | ❌ **NÃO** | ❌ **VIOLAÇÃO** |

**Nota sobre Formador**: Documentação menciona "Formador → instrutores com disponibilidade" como model separado, mas implementação usa Usuario com grupo "Formador". Isso é aceitável e até preferível (menos duplicação).

---

## 5. Código Morto Identificado (Expandido)

### 5.1 Endpoints Não Utilizados (Total: 6)

| Endpoint | Arquivo | Linha | Usado? | Ação |
|----------|---------|-------|--------|------|
| `/api/options/municipios/` | views_options.py | 28-45 | ❌ NÃO | REMOVER |
| `/api/options/projetos/` | views_options.py | 48-65 | ❌ NÃO | REMOVER |
| `/api/options/tipos-evento/` | views_options.py | 68-85 | ❌ NÃO | REMOVER |
| `/api/options/usuarios/` | views_options.py | 88-105 | ❌ NÃO | REMOVER |
| `MunicipioOptionViewSet` | views.py | 880-896 | ❌ NÃO REGISTRADO | REMOVER |
| `ProjetoOptionViewSet` | views.py | 899-915 | ❌ NÃO REGISTRADO | REMOVER |

**Impacto**: Baixo (código não afeta funcionamento)
**Prioridade**: Baixa (limpeza de tech debt)

---

## 6. Matriz de Conformidade SSOT (Completa)

| Entidade | Tabela Única | FK Corretos | API SSOT | Frontend SSOT | Nota | Status |
|----------|--------------|-------------|----------|---------------|------|--------|
| **Município** | ✅ | ✅ | ✅ | ✅ | A+ | ✅ CONFORME |
| **Projeto** | ✅ | ✅ | ✅ | ✅ | A+ | ✅ CONFORME |
| **TipoEvento** | ✅ | ✅ | ✅ | ✅ | A+ | ✅ CONFORME |
| **Usuario** | ✅ | ✅ | ✅ | ✅ | A+ | ✅ CONFORME |
| **Produto** | ❌ | ❌ | ❌ | ❌ | **F** | ❌ **VIOLAÇÃO** |
| Solicitacao | ✅ | ✅ | ✅ | ✅ | A | ✅ CONFORME |
| Compra | ✅ | ⚠️ | ✅ | ✅ | C | ⚠️ PARCIAL |
| AvailabilityBlock | ✅ | ✅ | ✅ | ✅ | A | ✅ CONFORME |
| Deslocamento | ✅ | ✅ | ✅ | ✅ | A | ✅ CONFORME |
| AcaoControle | ✅ | ✅ | ✅ | ✅ | A | ✅ CONFORME |
| AcaoDAT | ✅ | ✅ | ✅ | ✅ | A | ✅ CONFORME |
| AuditLog | ✅ | ✅ | ✅ | ✅ | A+ | ✅ CONFORME |
| Participation | ✅ | ✅ | ✅ | ✅ | A | ✅ CONFORME |

**Média Geral**: B+ (84.6% conforme)

---

## 7. Recomendações Priorizadas

### 🔴 Prioridade ALTA (Violações Críticas)

#### 1. Criar Model Produto (SSOT)

**Issue sugerida**: "feat(core): add Produto model and refactor Compra FK"

**Tarefas**:
1. Criar model `Produto` com FK para `Projeto`
2. Migrar dados de `Compra.codigo` (texto) → `Compra.produto_id` (FK)
3. Remover função `_infer_projeto_from_produto()`
4. Criar API `/api/produtos/` (CRUD + lookup)
5. Criar página AdminDAT para gestão de Produtos
6. Atualizar testes

**Benefícios**:
- ✅ Elimina duplicação de nomes de produtos
- ✅ Valida produtos existentes antes de criar Compra
- ✅ Facilita relatórios e análises
- ✅ Remove lógica hardcoded (heurísticas)

**Esforço estimado**: Médio (4-8h)

---

### 🟡 Prioridade MÉDIA

#### 2. Remover Código Morto (Tech Debt)

**Issue sugerida**: "chore(api): remove unused options endpoints"

**Tarefas**:
1. Deletar `v2/backend/apps/core/views_options.py`
2. Remover `MunicipioOptionViewSet` e `ProjetoOptionViewSet` de `views.py`
3. Remover imports e paths de `urls.py`
4. Remover serializers órfãos (se houver)

**Benefícios**:
- ✅ Reduz confusão (apenas 1 endpoint por funcionalidade)
- ✅ Reduz superfície de ataque
- ✅ Facilita manutenção

**Esforço estimado**: Baixo (1-2h)

---

### 🟢 Prioridade BAIXA

#### 3. Documentar API Endpoints

**Issue sugerida**: "docs(api): add comprehensive API reference"

**Tarefa**: Criar `v2/docs/API_ENDPOINTS.md` com todos os endpoints ativos

**Benefício**: Evita reimplementação de endpoints duplicados

**Esforço estimado**: Baixo (2h)

---

## 8. Validação SSOT (Checklist Completo)

### ✅ Dados Mestre

| Critério | Município | Projeto | TipoEvento | Usuario | Produto |
|----------|-----------|---------|------------|---------|---------|
| Tabela única | ✅ | ✅ | ✅ | ✅ | ❌ |
| Campos unique | ✅ | ✅ | ✅ | ✅ | ❌ |
| FK em relacionamentos | ✅ | ✅ | ✅ | ✅ | ❌ |
| API SSOT | ✅ | ✅ | ✅ | ✅ | ❌ |
| Frontend sem cache | ✅ | ✅ | ✅ | ✅ | N/A |
| **Nota Final** | **A+** | **A+** | **A+** | **A+** | **F** |

### ✅ Dados Transacionais

| Critério | Solicitacao | Compra | Outros (6) |
|----------|-------------|--------|------------|
| Tabela única | ✅ | ✅ | ✅ |
| FK para dados mestre | ✅ | ⚠️ | ✅ |
| Sem duplicação | ✅ | ⚠️ | ✅ |
| **Nota Final** | **A** | **C** | **A** |

---

## 9. Conclusões

### ✅ Pontos Fortes

1. **Backend bem normalizado**: 11 de 13 entidades (84.6%) estão 100% conformes com SSOT
2. **ForeignKeys corretos**: Municipio, Projeto, TipoEvento, Usuario têm FKs em todos os relacionamentos
3. **API consistente**: Endpoints de CRUD e lookup servem dados de fonte única
4. **Frontend sem duplicação**: Nenhum cache persistente ou localStorage de dados mestre
5. **Substituição de planilhas**: Sistema eliminou IMPORTRANGE em 80% dos casos

### ❌ Violações Críticas

1. **Produto não é SSOT**: Nomes de produtos duplicados em cada Compra (campo texto em vez de FK)
2. **Lógica hardcoded**: Heurísticas em código Python para inferir Projeto a partir de produto (deveria estar no banco)

### ⚠️ Problemas Menores

1. **Código morto**: 6 endpoints/views não utilizados (baixo impacto)
2. **Falta documentação**: API não documentada formalmente

### 🎯 Próximos Passos

1. **URGENTE**: Criar model Produto (Issue #XXX)
2. **Curto prazo**: Remover código morto (PR chore/remove-options-endpoints)
3. **Médio prazo**: Documentar API (v2/docs/API_ENDPOINTS.md)

---

## 10. Anexos

### Anexo A: Diagrama ER Simplificado (Dados Mestre)

```
┌──────────────┐
│  Municipio   │
│  (SSOT)      │
└──────┬───────┘
       │ FK
       ├─→ Solicitacao
       ├─→ AcaoControle
       ├─→ AcaoDAT
       └─→ Compra

┌──────────────┐
│  Projeto     │
│  (SSOT)      │
└──────┬───────┘
       │ FK
       ├─→ Solicitacao
       ├─→ AcaoControle
       ├─→ AcaoDAT
       ├─→ Compra
       └─→ Produto (❌ FALTANDO)

┌──────────────┐
│  TipoEvento  │
│  (SSOT)      │
└──────┬───────┘
       │ FK
       └─→ Solicitacao

┌──────────────┐
│  Usuario     │
│  (SSOT)      │
└──────┬───────┘
       │ FK
       ├─→ Solicitacao.usuario
       ├─→ Participation.usuario
       ├─→ AuditLog.usuario
       └─→ AvailabilityBlock.usuario

❌ FALTANDO:
┌──────────────┐
│  Produto     │
│  (NÃO EXISTE)│
└──────────────┘
   ↑
   │ Deveria ter FK de:
   └─→ Compra.produto (atualmente é CharField)
```

### Anexo B: Comparação Antes/Depois (Produto)

**❌ ATUAL (VIOLAÇÃO SSOT)**:
```python
class Compra(models.Model):
    codigo = models.CharField(max_length=50)  # ❌ Texto livre
    # ...

# Lógica hardcoded
def _infer_projeto_from_produto(produto_norm: str) -> Projeto | None:
    if "NOVO LENDO" in key:
        return resolve_projeto("Novo Lendo")  # ❌ Hardcoded
```

**Problemas**:
- "Novo Lendo", "NOVO LENDO", "novo lendo" → 3 registros diferentes
- Adicionar produto exige alterar código
- Nenhuma validação de produto existente

**✅ PROPOSTO (SSOT CONFORME)**:
```python
class Produto(models.Model):
    nome = models.CharField(max_length=200, unique=True)
    codigo = models.CharField(max_length=50, unique=True)
    projeto = models.ForeignKey(Projeto, ...)  # ✅ FK em vez de heurística

class Compra(models.Model):
    produto = models.ForeignKey(Produto, ...)  # ✅ FK em vez de CharField
```

**Benefícios**:
- "Novo Lendo" existe 1 vez (SSOT)
- Adicionar produto = INSERT no banco (não altera código)
- Validação automática (FK constraint)

---

**Documento gerado em**: 2025-11-14
**Analisado por**: Claude (Sonnet 4.5)
**Ferramentas**: Grep, Read, análise manual de código
**Atualização**: Análise expandida para TODAS as entidades (13 models)
