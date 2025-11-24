# Análise: produtos.xlsx — Brainstorm SSOT

**Data**: 2025-11-14
**Arquivo**: `C:\Users\datsu\OneDrive\Área de Trabalho\produtos.xlsx`
**Objetivo**: Avaliar viabilidade de usar este arquivo como SSOT para Produtos

---

## 📊 Resumo Executivo

| Métrica | Valor | Status |
|---------|-------|--------|
| **Total de produtos** | 138 | ✅ Boa quantidade |
| **Projetos únicos** | 31 | ✅ Bem distribuído |
| **Coleções únicas** | 79 | ✅ Organizado |
| **Campos** | 6 | ✅ Estrutura completa |
| **IDs duplicados** | 0 | ✅ **SEM DUPLICADOS** |
| **Nomes similares** | 4 pares (Aluno/Professor) | ✅ Produtos distintos |
| **Valores nulos** | 0 | ✅ Dados completos |

**Conclusão**: ✅ **Arquivo EXCELENTE para ser SSOT**. Estrutura limpa, sem nulos, IDs únicos.

---

## 1. Estrutura do Arquivo

### 1.1 Colunas (6 campos)

| # | Nome | Tipo | Exemplo | Observação |
|---|------|------|---------|------------|
| 1 | `id_produto` | int64 | 1, 2, 425 | ✅ ID único (PK) |
| 2 | `nome_produto` | object (str) | "A COR DA GENTE 1º ANO ALUNO" | ⚠️ 4 duplicados (Aluno/Prof) |
| 3 | `nome_colecao` | object (str) | "A COR DA GENTE 1" | 79 coleções |
| 4 | `nome_projeto` | object (str) | "A COR DA GENTE" | ✅ FK para Projeto |
| 5 | `tipo_produto` | object (str) | "Aluno" ou "Professor" | 2 valores |
| 6 | `tipo_gerência` | object (str) | "GERENCIA 4", "SUPERINTENDENCIA" | 7 valores |

### 1.2 Primeiras 10 Linhas

```
id  nome_produto                        nome_colecao          nome_projeto     tipo      tipo_gerência
1   A COR DA GENTE 1º ANO ALUNO         A COR DA GENTE 1      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
2   A COR DA GENTE 2º ANO ALUNO         A COR DA GENTE 2      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
3   A COR DA GENTE 3º ANO ALUNO         A COR DA GENTE 3      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
4   A COR DA GENTE 4º ANO ALUNO         A COR DA GENTE 4      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
5   A COR DA GENTE 5º ANO ALUNO         A COR DA GENTE 5      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
6   A COR DA GENTE 6º ANO ALUNO         A COR DA GENTE 6      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
7   A COR DA GENTE 7º ANO ALUNO         A COR DA GENTE 7      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
8   A COR DA GENTE 8º ANO ALUNO         A COR DA GENTE 8      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
9   A COR DA GENTE 9º ANO ALUNO         A COR DA GENTE 9      A COR DA GENTE   Aluno     GERENCIA INDIVIDUAL
12  ACERTA BRASIL MATEMATICA KIT ALUNO  ACERTA BRASIL MAT...  ACERTA MATEMATICA Aluno    GERENCIA 4
```

---

## 2. Análise de Valores Únicos

### 2.1 tipo_produto (2 valores)

```
Aluno        77 produtos
Professor    61 produtos
```

**Observação**: Este campo diferencia material de aluno vs professor. Explica os "duplicados".

### 2.2 tipo_gerência (7 valores)

```
SUPERINTENDENCIA       36 produtos
GERENCIA 4             29 produtos
GERENCIA INDIVIDUAL    29 produtos
GERENCIA 2             24 produtos
GERENCIA 5              8 produtos
GERENCIA 6              8 produtos
GERENCIA 3              4 produtos
```

**Análise**: Parece ser hierarquia/nível de gerência que autoriza o produto. Relacionado ao fluxo de aprovação?

### 2.3 nome_projeto (31 únicos)

**Top 10 projetos com mais produtos**:
```
1.  LEIO, ESCREVO E CALCULO           ( 10 produtos)
2.  A COR DA GENTE                    (  9 produtos)
3.  BRINCANDO E APRENDENDO            (  8 produtos)
4.  VIDA E LINGUAGEM                  (  8 produtos)
5.  VIDA E CIÊNCIAS                   (  8 produtos)
6.  VIDA E MATEMÁTICA                 (  8 produtos)
7.  SOU DA PAZ                        (  8 produtos)
8.  ECS                               (  7 produtos)
9.  NOVO LENDO                        (  6 produtos)
10. LENDO E ESCREVENDO                (  6 produtos)
```

**Lista completa (31 projetos)**:
1. A COR DA GENTE
2. ACERTA MATEMATICA
3. ACERTA PORTUGUES
4. AVANÇANDO JUNTOS MATEMÁTICA
5. AVANÇANDO JUNTOS PORTUGUÊS
6. BRINCANDO E APRENDENDO
7. CIRANDAR
8. ECS
9. ED FINANCEIRA
10. FLUIR DAS EMOÇÕES (4 variantes)
11. GESTÃO ESCOLAR
12. LEIO, ESCREVO E CALCULO
13. LENDO E ESCREVENDO
14. LER, OUVIR E CONTAR
15. NOVO LENDO
16. PROJETO AMMA
17. PROJETO CATAVENTO 2
18. PROJETO CATAVENTO 3
19. PROJETO MIUDEZAS E DESCOBERTAS
20. SOU DA PAZ
21. SUPERATIVAR - LINGUAGENS
22. SUPERATIVAR - MATEMÁTICA
23. TEMA
24. TRÂNSITO LEGAL
25. UNI DUNI TÊ
26. VIDA E CIÊNCIAS
27. VIDA E LINGUAGEM
28. VIDA E MATEMÁTICA

---

## 3. Verificação de Duplicados

### 3.1 IDs Duplicados

✅ **0 duplicados** - Campo `id_produto` é **único** (pode ser PK)

### 3.2 Nomes Similares (NÃO são duplicados)

✅ **0 duplicados** - Os 4 produtos com nomes similares têm **IDs diferentes** (são produtos distintos):

| ID  | Nome Produto | Coleção | Projeto | Tipo | Gerência |
|-----|--------------|---------|---------|------|----------|
| 425 | GESTÃO ESCOLAR - AVALIAR 2º ANO - LÍNGUA PORTUGUESA | GESTÃO ESCOLAR | GESTÃO ESCOLAR | **Aluno** | GERENCIA INDIVIDUAL |
| 426 | GESTÃO ESCOLAR - AVALIAR 2º ANO - LÍNGUA PORTUGUESA | GESTÃO ESCOLAR | GESTÃO ESCOLAR | **Professor** | GERENCIA INDIVIDUAL |
| 398 | PROJETO CATAVENTO 2 | PROJETO CATAVENTO 2 | PROJETO CATAVENTO 2 | **Aluno** | SUPERINTENDENCIA |
| 399 | PROJETO CATAVENTO 2 | PROJETO CATAVENTO 2 | PROJETO CATAVENTO 2 | **Professor** | SUPERINTENDENCIA |
| 400 | PROJETO CATAVENTO 3 | PROJETO CATAVENTO 3 | PROJETO CATAVENTO 3 | **Aluno** | SUPERINTENDENCIA |
| 401 | PROJETO CATAVENTO 3 | PROJETO CATAVENTO 3 | PROJETO CATAVENTO 3 | **Professor** | SUPERINTENDENCIA |
| 396 | PROJETO MIUDEZAS E DESCOBERTAS | PROJETO MIUDEZAS E DESCOBERTAS | PROJETO MIUDEZAS E DESCOBERTAS | **Aluno** | SUPERINTENDENCIA |
| 397 | PROJETO MIUDEZAS E DESCOBERTAS | PROJETO MIUDEZAS E DESCOBERTAS | PROJETO MIUDEZAS E DESCOBERTAS | **Professor** | SUPERINTENDENCIA |

**Conclusão**: ✅ **NÃO SÃO DUPLICADOS**. São produtos **distintos** (IDs únicos). O fato de terem nomes similares está correto (versões Aluno/Professor do mesmo material).

---

## 4. Compatibilidade com Sistema Atual

### 4.1 Comparação com CLAUDE.md

**CLAUDE.md menciona** (linha 200):
> **Planilha de Controle - 2025.xlsx**
> - Aba "COMPRAS": CÓD, **Produto**, Quant., Município, UF, Data, Uso das coleções

**Análise**: Campo "Produto" da planilha de compras **deveria ser FK** para esta tabela de produtos.

### 4.2 Comparação com Compra Atual

**Model atual** (`v2/backend/apps/core/models.py:557-620`):
```python
class Compra(models.Model):
    codigo = models.CharField(max_length=50)  # ❌ Texto livre
    projeto = models.ForeignKey(Projeto, ...)
    municipio = models.ForeignKey(Municipio, ...)
    quantidade = models.IntegerField(...)
    data = models.DateField(...)
    uso = models.TextField(...)
```

**Problema identificado**:
- `Compra.codigo` é CharField (texto livre)
- Deveria ser FK para `Produto.id_produto`

### 4.3 Inferência de Projeto Hardcoded

**Código atual** (`v2/backend/apps/core/services/controle_imports.py:293-314`):
```python
def _infer_projeto_from_produto(produto_norm: str) -> Projeto | None:
    """❌ VIOLAÇÃO SSOT: Lógica hardcoded"""
    if "NOVO LENDO" in key:
        return resolve_projeto("Novo Lendo")
    if "GESTAO ESCOLAR" in key:
        return resolve_projeto("Gestão Escolar")
```

**Solução com arquivo**: ✅ Usar `produtos.xlsx` como lookup (nome_projeto → FK)

---

## 5. Proposta de Model Produto

### 5.1 Estrutura Sugerida

```python
class Produto(models.Model):
    """SSOT: Substitui texto livre em Compra"""

    # PK (usar id do arquivo)
    id = models.IntegerField(primary_key=True, help_text="ID original do arquivo produtos.xlsx")

    # Campos principais
    nome = models.CharField(max_length=200, db_index=True, help_text="Nome completo do produto")
    colecao = models.CharField(max_length=200, help_text="Nome da coleção")

    # FK para Projeto (SSOT)
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.PROTECT,
        related_name="produtos",
        help_text="Projeto associado ao produto"
    )

    # Classificação
    tipo_produto = models.CharField(
        max_length=20,
        choices=[('Aluno', 'Aluno'), ('Professor', 'Professor')],
        help_text="Material de aluno ou professor"
    )

    tipo_gerencia = models.CharField(
        max_length=50,
        help_text="Nível de gerência que autoriza (SUPERINTENDENCIA, GERENCIA 4, etc.)"
    )

    # Controle
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_produto"
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["projeto", "tipo_produto"]),
            models.Index(fields=["colecao"]),
        ]
        # Sem constraint de unique em nome (produtos podem ter nomes similares)
        # ID é suficiente como PK

    def __str__(self) -> str:
        return f"{self.nome} ({self.tipo_produto})"
```

### 5.2 Atualizar Compra

```python
class Compra(models.Model):
    """Registro de compras de materiais/produtos para projetos."""

    # ✅ FK em vez de CharField
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="compras",
        help_text="Produto comprado"
    )

    # Remover campo 'codigo' (agora via produto.id ou produto.nome)

    projeto = models.ForeignKey(Projeto, ...)  # ✅ Manter (pode divergir de produto.projeto)
    municipio = models.ForeignKey(Municipio, ...)
    quantidade = models.IntegerField(...)
    data = models.DateField(...)
    uso = models.TextField(...)
    external_hash = models.CharField(...)
```

---

## 6. Estratégia de Migração

### 6.1 Opções de Migração

#### **Opção A: Arquivo como Seed Inicial (Recomendado)**

**Fluxo**:
1. Criar model `Produto`
2. Migration importa `produtos.xlsx` automaticamente (seed inicial)
3. Após seed, produtos são gerenciados via AdminDAT (CRUD normal)
4. Arquivo serve apenas como **histórico/referência**

**Prós**:
- ✅ Simplicidade (seed único)
- ✅ Sistema autônomo após seed
- ✅ Permite adicionar produtos via interface

**Contras**:
- ⚠️ Arquivo não sincroniza automaticamente (divergência possível)

---

#### **Opção B: Arquivo como SSOT Permanente (ETL Periódico)**

**Fluxo**:
1. Criar model `Produto`
2. Criar ETL `import_produtos` (similar a `import_compras`)
3. Rodar ETL periodicamente (sincroniza produtos)
4. AdminDAT pode **visualizar** produtos, mas **não editar** (read-only)

**Prós**:
- ✅ Arquivo sempre é a verdade (SSOT externo)
- ✅ Mudanças no arquivo refletem no sistema

**Contras**:
- ⚠️ Requer manutenção do arquivo Excel
- ⚠️ Complexidade maior (ETL + sincronização)

---

### 6.2 Recomendação

**Escolha**: **Opção A (Seed Inicial)**

**Razão**:
- Produtos parecem ser **relativamente estáveis** (não mudam toda semana)
- 138 produtos é quantidade **gerenciável** via AdminDAT
- Sistema fica **autônomo** (não depende de arquivo externo)
- Arquivo serve como **documentação histórica**

---

## 7. Passos de Implementação (Opção A)

### 7.1 Fase 1: Criar Model Produto

**Arquivo**: `v2/backend/apps/core/models.py`

**Tarefas**:
1. Adicionar model `Produto` (estrutura acima)
2. Criar migration `0024_add_produto_model.py`
3. Testar migration em ambiente local

### 7.2 Fase 2: Seed Inicial (Data Migration)

**Arquivo**: `v2/backend/apps/core/migrations/0025_seed_produtos.py`

**Código sugerido**:
```python
from django.db import migrations
import pandas as pd
from pathlib import Path

def seed_produtos(apps, schema_editor):
    Produto = apps.get_model('core', 'Produto')
    Projeto = apps.get_model('core', 'Projeto')

    # Ler arquivo produtos.xlsx
    arquivo = Path(__file__).parent.parent.parent.parent / 'data' / 'csv-import' / 'produtos.xlsx'
    df = pd.read_excel(arquivo)

    for _, row in df.iterrows():
        # Resolver projeto (FK)
        try:
            projeto = Projeto.objects.get(nome=row['nome_projeto'])
        except Projeto.DoesNotExist:
            print(f"AVISO: Projeto '{row['nome_projeto']}' não existe. Pulando produto {row['id_produto']}.")
            continue

        # Criar produto
        Produto.objects.update_or_create(
            id=row['id_produto'],
            defaults={
                'nome': row['nome_produto'],
                'colecao': row['nome_colecao'],
                'projeto': projeto,
                'tipo_produto': row['tipo_produto'],
                'tipo_gerencia': row['tipo_gerência'],
                'ativo': True,
            }
        )

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0024_add_produto_model'),
    ]

    operations = [
        migrations.RunPython(seed_produtos, reverse_code=migrations.RunPython.noop),
    ]
```

### 7.3 Fase 3: Migrar Compra

**Desafio**: Compra atual tem `codigo` (CharField). Precisamos fazer lookup para `produto_id`.

**Estratégia**:
1. Adicionar campo `Compra.produto` (FK, nullable temporariamente)
2. Data migration: popular `produto` via lookup em `codigo`
3. Validar: todas as Compras têm `produto` válido
4. Remover campo `codigo`
5. Tornar `produto` obrigatório (NOT NULL)

**Migration sugerida**: `0026_migrate_compra_to_produto_fk.py`

### 7.4 Fase 4: Remover Lógica Hardcoded

**Arquivo**: `v2/backend/apps/core/services/controle_imports.py`

**Tarefas**:
1. ❌ **DELETAR** função `_infer_projeto_from_produto()`
2. ✅ **USAR** `produto.projeto` (via FK)

### 7.5 Fase 5: API e Frontend

**Backend**:
- Criar `ProdutoViewSet` (CRUD)
- Criar `ProdutoLookup` (autocomplete)
- Serializer `ProdutoSerializer`

**Frontend**:
- Página `AdminDAT/ProdutosPage.jsx` (lista + CRUD)
- Autocomplete em formulários de Compra

---

## 8. Checklist Pré-Migração

Antes de implementar, verificar:

### 8.1 Projetos no Arquivo vs Banco

**Ação**: Rodar query para verificar se todos os 31 projetos do arquivo **existem** no banco.

```bash
# Lista de projetos do arquivo (copiar da análise acima)
# Verificar no banco: SELECT nome FROM core_projeto WHERE nome IN (...)
```

**Risco**: Se algum projeto do arquivo **não existir** no banco, seed falhará.

**Solução**: Criar projetos faltantes antes de rodar seed.

### 8.2 Compras Existentes

**Ação**: Verificar quantas Compras existem e se `codigo` delas **bate** com algum produto do arquivo.

```sql
SELECT COUNT(*) FROM core_compra;
SELECT DISTINCT codigo FROM core_compra ORDER BY codigo;
```

**Questão**: O campo `codigo` em Compra é o nome do produto? Ou é um código diferente?

**Risco**: Se `codigo` em Compra **não for** o nome do produto, lookup falhará.

---

## 9. Perguntas para o Brainstorm

### 9.1 Gestão Futura de Produtos

**Pergunta**: Como você quer adicionar **novos produtos** no futuro?

**Opções**:
- **A**: Via AdminDAT (interface web)
- **B**: Atualizando o arquivo Excel e rodando ETL
- **C**: Ambos (híbrido)

**Minha recomendação**: **Opção A** (AdminDAT). Arquivo serve apenas para seed inicial.

---

### 9.2 Relacionamento Produto → Projeto

**Observação**: Arquivo tem `nome_projeto` para cada produto.

**Pergunta**: Este relacionamento é **fixo**? (Um produto sempre pertence a um único projeto?)

**Implicação**:
- Se SIM → FK `produto.projeto` está correto
- Se NÃO → Produtos podem ser usados em múltiplos projetos (ManyToMany?)

**Análise preliminar**: Parece que produtos são **específicos de projeto** (ex: "A COR DA GENTE 1º ANO ALUNO" só faz sentido no projeto "A COR DA GENTE"). Então FK está correto.

---

### 9.3 Campo "tipo_gerência"

**Pergunta**: O que significa `tipo_gerência`?

**Valores**:
- SUPERINTENDENCIA
- GERENCIA 4, GERENCIA 2, GERENCIA 3, GERENCIA 5, GERENCIA 6
- GERENCIA INDIVIDUAL

**Hipóteses**:
1. **Nível de autorização**: Quem pode aprovar compras deste produto?
2. **Hierarquia organizacional**: Qual gerência cuida do produto?
3. **Fluxo de aprovação**: Similar a `projeto.fluxo` (SUPER vs NAO_SUPER)?

**Ação**: Esclarecer este campo para modelar corretamente.

---

### 9.4 Compra.codigo vs Produto

**Pergunta**: O campo `codigo` em Compra é:
- **A**: Nome do produto (string livre)?
- **B**: ID do produto (número)?
- **C**: Código interno diferente?

**Ação**: Ver exemplo de dados reais de Compra para entender formato.

---

## 10. Próximos Passos (Brainstorm)

### 10.1 Validação de Projetos

**Tarefa**: Verificar se todos os 31 projetos do arquivo existem no banco.

**Comando sugerido**:
```bash
# Docker
docker exec -it aprender_v2-web-1 python manage.py shell

# Shell
from apps.core.models import Projeto
projetos_existentes = set(Projeto.objects.values_list('nome', flat=True))

# Comparar com lista de produtos.xlsx
```

### 10.2 Análise de Compras Existentes

**Tarefa**: Ver exemplos de `Compra.codigo` para entender formato.

**Comando sugerido**:
```bash
# Docker
docker exec -it aprender_v2-web-1 python manage.py shell

# Shell
from apps.core.models import Compra
for compra in Compra.objects.all()[:10]:
    print(f"{compra.id}: codigo={compra.codigo}, projeto={compra.projeto.nome}")
```

### 10.3 Decisões de Design

**Pendente**:
1. Confirmar: Arquivo é **seed inicial** ou **SSOT permanente**?
2. Esclarecer: Significado de `tipo_gerência`
3. Validar: `Compra.codigo` é nome do produto?

---

## 11. Conclusões do Brainstorm

### ✅ Pontos Positivos

1. **Arquivo excelente**: Estrutura limpa, sem nulos, IDs únicos
2. **Dados completos**: 138 produtos, 31 projetos, bem distribuídos
3. **Viável como SSOT**: Pode ser usado como seed inicial ou ETL periódico
4. **Resolve problema atual**: Elimina lógica hardcoded `_infer_projeto_from_produto()`

### ⚠️ Pontos de Atenção

1. **Validar projetos**: 31 projetos do arquivo precisam existir no banco
2. **Entender tipo_gerência**: Significado não está claro
3. **Compra.codigo**: Precisa confirmar formato/conteúdo

### 🎯 Recomendação Final

**Implementar**: ✅ **SIM**, arquivo é **excelente para SSOT**

**Abordagem sugerida**: **Opção A (Seed Inicial)**
- Migration importa arquivo automaticamente
- Produtos gerenciados via AdminDAT após seed
- Arquivo serve como documentação histórica

**Próximos passos**:
1. Validar projetos existentes no banco
2. Analisar dados de Compra.codigo
3. Esclarecer tipo_gerência
4. Implementar model + migrations

---

**Documento gerado em**: 2025-11-14
**Analisado por**: Claude (Sonnet 4.5) usando pandas 2.3.3
**Ambiente**: Python 3.13.7 (.venv local)
**Ferramentas**: pandas, openpyxl, análise exploratória de dados
