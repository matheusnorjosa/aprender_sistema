# Compras (Regras de Negócio)

A lista de compras é **uma só**: `DATCompra`.

## COMPRA-01: Compra antiga (apagada)

A lista antiga `Compra` (tabela `core_compra`, histórico do ETL) saiu de uso no G29, etapa 1 (06/11/2026,
#2178), e foi apagada na etapa 2 (migration `0132_apaga_compra_antiga`), com a policy `import_compras`.
Não recrie: compra nova, regra da compra, Mapa e pendências leem `DATCompra`.

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
