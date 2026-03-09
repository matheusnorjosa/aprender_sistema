# Análise Completa das Planilhas → Modelos Django

**Data**: 2026-01-26

---

## Resumo Executivo

| Planilha | Modelo Destino | Registros | Prioridade | ETL Existe? |
|----------|----------------|-----------|------------|-------------|
| **Usuários.xlsx** | `Usuario` | 154 | 🔴 Alta | ✅ `import_usuarios_from_csv` |
| **todososusuarios.xlsx** | `Usuario` | 120 | 🟡 Média | ✅ Mesmo ETL |
| **gerentes_coord...xlsx** | `EquipeGerencia` + `Gerencia` | ~100 | 🔴 Alta | ❌ Criar |
| **Acompanhamento 2026** | `Solicitacao` + `Participation` | 99 | ✅ Feito | ✅ `etl_upsert_acompanhamento` |
| **Acompanhamento 2025** | `Solicitacao` + `Participation` | ~5000 | 🟡 Média | ✅ Mesmo ETL |
| **Acompanhamento Fluir** | `Solicitacao` + `Participation` | 419 | 🟡 Média | ⚠️ Adaptar |
| **Disponibilidade 2026** | `Deslocamento` + `AvailabilityBlock` | 16 | 🟡 Média | ✅ Criado |
| **Disponibilidade 2025** | `Deslocamento` + `AvailabilityBlock` | 549 | 🟡 Média | ✅ Criado |
| **Planilha Controle 2026** | `Compra` + `AcaoControle` + `DATCadastro` | ~1385 | 🟡 Média | ✅ Parcial |
| **produtos.xlsx** | `Produto` | 138 | 🔴 Alta | ❌ Criar |
| **Compras.xlsx** | `Compra` (formato diferente) | 1725 | 🟢 Baixa | ⚠️ Verificar duplicados |
| **formadores_fluir.xlsx** | `Usuario` (setor Fluir) | 9 | 🟢 Baixa | ✅ `seed_formadores_fluir` |
| **usuarios_vinculados_acerta** | `Usuario` (setor ACerta) | 17 | 🟢 Baixa | ⚠️ Verificar duplicados |
| **todos_os_dados_super** | `Usuario` + `EquipeGerencia` | 50 | 🟡 Média | ❌ Criar |

---

## 1. USUÁRIOS

### 1.1 Usuários.xlsx (Principal)
**Modelo**: `Usuario`

| Coluna Planilha | Campo Modelo | Observação |
|-----------------|--------------|------------|
| Nome | `first_name` | Nome curto |
| Nome Completo | `nome` (campo custom) | Nome completo |
| CPF | `cpf` | Precisa criar campo? |
| Telefone | `telefone` | Precisa criar campo? |
| Email | `email` + `username` | Chave única |
| Cargo | `funcao` via `EquipeGerencia.papel` | FORMADOR/COORDENADOR/etc |
| Gerência | `EquipeGerencia.gerencia` | FK para Gerencia |

**Abas**:
- `Ativos`: 126 usuários ativos
- `Inativos`: 7 usuários (`is_active=False`)
- `Pendentes`: 21 usuários (verificar antes de criar)

**ETL**: `import_usuarios_from_csv` (já existe, pode precisar ajustes)

---

### 1.2 todososusuarios.xlsx
**Modelo**: `Usuario`

Mesma estrutura de Usuários.xlsx. **Verificar duplicados** antes de importar.

---

### 1.3 gerentes_coordenadores_apoio_formadores_setores.xlsx
**Modelo**: `EquipeGerencia` + `Gerencia`

| Aba | Dados |
|-----|-------|
| Superintendência | 27 pessoas (Gerentes, Coord, Apoio, Formadores) |
| Brincando e Aprendendo | 10 pessoas |
| ACerta | 15 pessoas |
| Fluir das Emoções | 10 pessoas |
| Vidas | 20 pessoas |
| A Cor da Gente | ? |
| Sou da Paz | ? |
| Educação Financeira | ? |
| Ler, Ouvir e Contar | ? |
| Avançando Juntos | ? |
| IDEB10 | ? |
| My Companion | ? |

**Mapeamento**:
| Coluna | Campo |
|--------|-------|
| Aba (nome) | `Gerencia.nome_setor` |
| Gerentes | `Usuario` + `EquipeGerencia(papel='GERENTE')` |
| Coordenadores | `Usuario` + `EquipeGerencia(papel='COORDENADOR')` |
| Apoio de Coordenação | `Usuario` + `EquipeGerencia(papel='APOIO')` |
| Formadores | `Usuario` + `EquipeGerencia(papel='FORMADOR')` |

**ETL**: ❌ **Precisa criar** `etl_import_equipe_gerencia.py`

---

### 1.4 todos_os_dados_superintendencia.xlsx
**Modelo**: `Usuario` + `EquipeGerencia`

| Coluna | Campo |
|--------|-------|
| Formador | `Usuario.nome` (papel=FORMADOR) |
| Email | `Usuario.email` |
| Coordenador | `Usuario.nome` (papel=COORDENADOR) |
| Gerente | `Usuario.nome` (papel=GERENTE) |

50 registros de hierarquia Formador → Coordenador → Gerente.

**ETL**: Pode usar mesmo ETL de gerentes_coordenadores.

---

## 2. EVENTOS/SOLICITAÇÕES

### 2.1 Acompanhamento de Agenda _ Fluir (1).xlsx
**Modelo**: `Solicitacao` + `Participation`

| Coluna | Campo Modelo |
|--------|--------------|
| município | `Solicitacao.municipio` |
| turma | `Solicitacao.segmento` ou custom |
| encontro | `Solicitacao.encontro` |
| presencial | `Solicitacao.is_online` (inverso) |
| data | `Solicitacao.inicio` (date part) |
| hora início | `Solicitacao.inicio` (time part) |
| tema | `Solicitacao.observacoes` |

**419 eventos** do projeto Fluir.

**ETL**: `etl_upsert_acompanhamento` precisa ser **adaptado** para ler este formato diferente.

---

## 3. PRODUTOS

### 3.1 produtos.xlsx
**Modelo**: `Produto`

| Coluna | Campo Modelo |
|--------|--------------|
| id_produto | `Produto.codigo` |
| nome_produto | `Produto.nome` |
| nome_colecao | `Produto.descricao` |
| nome_projeto | `Produto.projeto` (FK) |
| tipo_produto | Campo custom? (Aluno/Professor) |
| tipo_gerência | Via `Projeto.gerencia` |

**138 produtos** - catálogo completo.

**ETL**: ❌ **Precisa criar** `etl_import_produtos.py`

---

## 4. COMPRAS

### 4.1 Compras.xlsx (Arquivo separado)
**Modelo**: `Compra`

| Coluna | Campo Modelo |
|--------|--------------|
| municipio_uf | `Compra.municipio` (parse "CIDADE - UF") |
| regiao | Não usado |
| tipo | Não usado (Aluno/Professor) |
| nome_projeto | `Compra.projeto` (FK) |
| nome_produto | `Compra.produto` (FK) ou `codigo` |
| gerencia | Via `Projeto.gerencia` |
| quantidade | `Compra.quantidade` |

**1725 registros** - formato diferente da Planilha de Controle.

**⚠️ Verificar**: Pode ter duplicados com Planilha de Controle.

---

## 5. RESUMO DE AÇÕES NECESSÁRIAS

### Alta Prioridade (Dados de Referência)
1. ✅ Municípios - Importados (50)
2. ❌ **Produtos** - Criar ETL para `produtos.xlsx` (138 produtos)
3. ❌ **Equipe/Gerência** - Criar ETL para `gerentes_coordenadores...xlsx`

### Média Prioridade (Dados Operacionais 2026)
4. ✅ Solicitações 2026 - Importadas (92)
5. 📋 COMPRAS 2026 - Pronto para importar (923)
6. 📋 Deslocamentos 2026 - ETL criado
7. 📋 Ações Controle 2026 - ETL existe

### Baixa Prioridade (Dados Históricos/Complementares)
8. 📋 Acompanhamento Fluir - Adaptar ETL
9. 📋 Todos os dados 2025 - Volume maior
10. 📋 Usuários pendentes/duplicados - Verificar

---

## 6. ETLS A CRIAR

### 6.1 etl_import_produtos.py
```python
# Mapeia produtos.xlsx → Produto
# Campos: codigo, nome, descricao, projeto (FK)
```

### 6.2 etl_import_equipe_gerencia.py
```python
# Mapeia gerentes_coordenadores...xlsx → EquipeGerencia
# Cria Gerencia se não existir
# Associa Usuario com papel (GERENTE/COORDENADOR/APOIO/FORMADOR)
```

### 6.3 Adaptar etl_upsert_acompanhamento.py
```python
# Adicionar suporte para formato Fluir:
# - município, turma, encontro, presencial, data, hora início, tema
```

---

## 7. ORDEM DE IMPORTAÇÃO RECOMENDADA

```
1. Produtos (produtos.xlsx)           → Base para Compras
2. Gerências/Equipes                  → Estrutura organizacional
3. Usuários completos                 → Todos os usuários
4. COMPRAS 2026                       → Dados operacionais
5. Deslocamentos 2026                 → Dados operacionais
6. Ações Controle 2026                → Dados operacionais
7. Acompanhamento Fluir               → Eventos adicionais
8. Dados 2025 (histórico)             → Opcional
```
