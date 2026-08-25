# Compras (Regras de Negócio)

O sistema possui **dois models de compra** com propósitos distintos.

## COMPRA-01: Compra (Histórico ETL)

**Model**: `Compra` (`apps/core/models/compra.py`)
**Propósito**: Importação histórica de compras da planilha original
**Chave natural**: `(codigo + municipio + projeto + data)`

**Campos**:
- `codigo`: CharField (DEPRECATED - usar FK produto)
- `produto`: FK → Produto
- `projeto`: FK → Projeto
- `municipio`: FK → Municipio
- `quantidade`: IntegerField
- `data`: DateField
- `uso`: TextField (finalidade da compra)
- `external_hash`: SHA256 para idempotência de import

## COMPRA-02: DATCompra (Gestão Operacional)

**Model**: `DATCompra` (`apps/core/models/dat_compra.py`)
**Propósito**: Gestão operacional de materiais pelo setor DAT

**Campos**:
- `municipio`: FK → Municipio
- `projeto`: FK → Projeto
- `produto`: FK → Produto (nullable)
- `descricao_produto`: CharField (alternativa ao FK)
- `quantidade`: PositiveIntegerField (quantidade adquirida)
- `quantidade_utilizada`: PositiveIntegerField
- `valor_unitario`: DecimalField
- `ano_uso`: PositiveSmallIntegerField
- `data_compra`: DateField
- `status_uso`: Enum (disponivel, em_uso, esgotado, devolvido)

**Properties**:
- `disponivel`: quantidade - quantidade_utilizada
- `valor_total`: quantidade × valor_unitario

**Auto-cálculo em save()**:
```python
if quantidade_utilizada >= quantidade:
    status_uso = ESGOTADO
elif quantidade_utilizada > 0:
    status_uso = EM_USO
else:
    status_uso = DISPONIVEL
```

## COMPRA-03: Produtos

**Model**: `Produto` (`apps/core/models/organizacao.py`)
**Fonte**: produtos.xlsx

**Campos**:
- `codigo`: CharField (único)
- `nome`: CharField
- `projeto`: FK → Projeto (obrigatório)

**Exemplo**: `NL-C1` → "Novo Lendo - Coleção 1" → Projeto "Novo Lendo"
