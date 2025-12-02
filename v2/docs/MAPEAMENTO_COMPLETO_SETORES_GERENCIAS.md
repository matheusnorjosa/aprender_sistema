# 📊 Mapeamento Completo: Setores, Gerências, Projetos, Cargos e Pessoas

**Data Original**: 2025-11-14
**Última Atualização**: 2025-12-01 (estatísticas de usuários)
**Fontes**: Planilhas originais + Banco de dados PostgreSQL (v2)

> **📌 NOTA**: Para informações detalhadas sobre RBAC (grupos, permissões, páginas acessíveis), consulte [`docs/RBAC_COMPLETO.md`](./RBAC_COMPLETO.md)

---

## 🎯 Estrutura Hierárquica

```
GERÊNCIA (estrutura organizacional)
  └── SETOR (nome comercial/operacional)
      └── PROJETOS (produtos/coleções)
          └── PESSOAS
              ├── Gerente (1)
              ├── Coordenadores (N)
              └── Formadores (N)
```

---

## 📁 GERÊNCIAS → SETORES → PROJETOS

### SUPERINTENDENCIA

**Setor**: Super
**Fluxo**: SUPER (aprovação manual obrigatória)
**Pessoas na gerência**: 50 (segundo planilha Usuários)

| Projeto | Status no Sistema | Código |
|---------|-------------------|--------|
| CIRANDAR | ✅ Existe (SUPER) | - |
| LENDO E ESCREVENDO | ✅ Existe (SUPER) | - |
| LER, OUVIR E CONTAR | ✅ Existe (NAO_SUPER) | LER_OUVIR |
| NOVO LENDO | ✅ Existe (SUPER) | - |
| PROJETO AMMA | ✅ Existe (SUPER) | - |
| PROJETO CATAVENTO 2 | ✅ Existe (NAO_SUPER) | - |
| PROJETO CATAVENTO 3 | ✅ Existe (NAO_SUPER) | - |
| PROJETO MIUDEZAS E DESCOBERTAS | ✅ Existe (SUPER) | - |
| TEMA | ✅ Existe (SUPER) | - |

**Cargos**:
- 13 Gerentes (Superintendência)
- 37 Coordenadores/Formadores

---

### GERENCIA 2

**Setor**: Vidas
**Fluxo**: NAO_SUPER (auto-aprovado)
**Pessoas na gerência**: 25 (3 "Vidas" + 10 "Vidas L" + 9 "Vidas M" + 3 "Vidas C")

| Projeto | Status no Sistema | Observação |
|---------|-------------------|------------|
| VIDA E CIÊNCIAS | ✅ Existe (NAO_SUPER) | Vidas C = 3 pessoas |
| VIDA E LINGUAGEM | ✅ Existe (NAO_SUPER) | Vidas L = 10 pessoas |
| VIDA E MATEMÁTICA | ✅ Existe (NAO_SUPER) | Vidas M = 9 pessoas |

**Coordenadores Principais**:
- Elienai Oliveira Góes
- Socorro Aclécia Araújo Pereira Medeiros
- Patrícia Lemos
- (+2 outros)

---

### GERENCIA 3

**Setor**: Fluir
**Fluxo**: NAO_SUPER (auto-aprovado)
**Pessoas na gerência**: 2 (Daniel Gomes, Lázaro Teixeira)

| Projeto | Status no Sistema | Observação |
|---------|-------------------|------------|
| FLUIR DAS EMOÇÕES | ✅ Existe (NAO_SUPER) | Projeto principal |
| FLUIR DAS EMOÇÕES - 1 | ✅ Existe (NAO_SUPER) | Coleção 1 |
| FLUIR DAS EMOÇÕES - 2 | ✅ Existe (NAO_SUPER) | Coleção 2 |
| FLUIR DAS EMOÇÕES - 3 | ✅ Existe (NAO_SUPER) | Coleção 3 |

**Coordenador Principal**:
- Lázaro Júnior (aba COORD da Planilha de Controle)

**Formadores do Fluir** (planilha específica):
1. Adeliana Mówima Falcao Machado
2. Fernanda Matthews Jucá
3. Janaína Bezerra de Aquino Faria
4. Jennifer Kerolly de Oliveira Barros Bathaus
5. Juliana Cruz Maciel
6. Jéssica Nunes Apolonio
7. Natália de Araújo Loiola
8. Priscilla Laysa Mota Pereira
9. Talitha Lousada Teixeira

**Eventos Fluir 2025**:
- Total: 174 eventos
- Municípios: 6 (Araguari-MG, Cubatão-SP, Embu das Artes-SP, Rancharia-SP, Rio Verde do Mato Grosso-MS, Uiraúna-PB)
- ⚠️ **Nota**: Esses eventos NÃO estão na planilha "Acompanhamento de Agenda _ 2025.xlsx" principal

---

### GERENCIA 4

**Setor**: ACerta
**Fluxo**: NAO_SUPER (auto-aprovado)
**Pessoas na gerência**: 17

| Projeto | Status no Sistema | Observação |
|---------|-------------------|------------|
| ACERTA MATEMÁTICA | ✅ Existe (NAO_SUPER) | - |
| ACERTA PORTUGUÊS | ✅ Existe (NAO_SUPER) | - |
| ECS | ✅ Existe (NAO_SUPER) | Escrever Comunicar e Ser |
| LEIO, ESCREVO E CALCULO | ✅ Existe (NAO_SUPER) | Variantes: LEIO ESCREVO E CALCULO |
| SUPERATIVAR - LINGUAGENS | ✅ Existe (NAO_SUPER) | - |
| SUPERATIVAR - MATEMÁTICA | ✅ Existe (NAO_SUPER) | - |

**Coordenadores Principais**:
- Beatriz Helena Castelo de Andrade Furtado
- Ellen Damares Felipe de Queiroz
- (+1 outro)

---

### GERENCIA 5

**Setor**: Brincando
**Fluxo**: NAO_SUPER (auto-aprovado)
**Pessoas na gerência**: 15

| Projeto | Status no Sistema |
|---------|-------------------|
| BRINCANDO E APRENDENDO | ✅ Existe (NAO_SUPER) |

**Coordenadores Principais**:
- Leidiane de Sousa da Silva
- Ana Patrícia de Sousa Silva Martins

---

### GERENCIA 6

**Setor**: Sou da Paz
**Fluxo**: NAO_SUPER (auto-aprovado)
**Pessoas na gerência**: 1 (estimado)

| Projeto | Status no Sistema |
|---------|-------------------|
| SOU DA PAZ | ✅ Existe (NAO_SUPER) |

**Coordenador Principal**:
- Rafael Rabelo Cavalcanti

---

### GERENCIA INDIVIDUAL

**Setor**: Múltiplos (cada projeto = setor próprio)
**Fluxo**: NAO_SUPER (auto-aprovado)
**Característica**: Coordenador geralmente é também gerente e formador

| Projeto | Status no Sistema | Coordenador/Gerente |
|---------|-------------------|---------------------|
| A COR DA GENTE | ✅ Existe (NAO_SUPER) | Daniele Cristina Moreira Cruz |
| AVANÇANDO JUNTOS MATEMÁTICA | ✅ Existe (NAO_SUPER) | - |
| AVANÇANDO JUNTOS PORTUGUÊS | ✅ Existe (NAO_SUPER) | - |
| ED FINANCEIRA | ✅ Existe (NAO_SUPER) | Amanda Arruda |
| GESTÃO ESCOLAR (IDEB10) | ✅ Existe (NAO_SUPER) | Analine Parente |
| TRÂNSITO LEGAL | ✅ Existe (NAO_SUPER) | - |
| UNI DUNI TÊ | ✅ Existe (SUPER) | - |

**Pessoas por projeto**:
- A Cor da Gente: Daniele Cristina (coord)
- Avançando Juntos: 3 pessoas (Danielle Fernandes + 2)
- Ed Financeira: Amanda Arruda (coord)
- Gestão Escolar (IDEB 10): Analine Parente (coord) + Vinicius Albuquerque
- Outros: 4 pessoas (Amanda Arruda + 3)

---

## 👥 CARGOS (Planilha Usuários.xlsx)

| Cargo | Total de Pessoas | Observação |
|-------|------------------|------------|
| **Formadores** | 76 | Executam eventos |
| **Coordenadores** | 35 | Solicitam eventos |
| **Gerente** | 7 | Gerenciam setores |

**Total de usuários ativos**: 117

---

## 🏢 GRUPOS/PERFIS NO SISTEMA (Django)

⚠️ **ATUALIZADO**: 2025-12-01 (128 usuários totais)

| Grupo | Total no Banco | Permissões |
|-------|----------------|------------|
| Superintendência | 1 | Aprovar/reprovar solicitações SUPER |
| Formador | 90 | Bloquear agenda, participar de eventos |
| Coordenador | 37 | Criar solicitações |
| Controle | 2 | Publicar eventos no Google Calendar |
| DAT | 1 | CRUD usuários e municípios |
| Gerência | 0 | Visualizar solicitações ⚠️ (grupo existe mas sem usuários) |
| Superuser (flag) | 1 | Bypass total de permissões |

---

## 📋 PROJETOS NO SISTEMA (46 total)

### Projetos SUPER (9):
1. CIRANDAR
2. Cataventos
3. LENDO E ESCREVENDO
4. NOVO LENDO
5. PROJETO AMMA
6. PROJETO MIUDEZAS E DESCOBERTAS
7. TEMA
8. UNI DUNI TÊ
9. (+projetos de teste)

### Projetos NAO_SUPER (37):
- **Vidas**: VIDA E CIÊNCIAS, VIDA E LINGUAGEM, VIDA E MATEMÁTICA, Vidas
- **Fluir**: FLUIR DAS EMOÇÕES, FLUIR DAS EMOÇÕES - 1/2/3
- **ACerta**: ACERTA MATEMÁTICA, ACERTA PORTUGUÊS, ACerta, ECS, LEIO ESCREVO E CALCULO, SUPERATIVAR - LINGUAGENS, SUPERATIVAR - MATEMÁTICA
- **Brincando**: BRINCANDO E APRENDENDO, Brincando
- **Sou da Paz**: SOU DA PAZ
- **Gerência Individual**: A COR DA GENTE, AVANÇANDO JUNTOS MATEMÁTICA/PORTUGUÊS, ED FINANCEIRA, GESTÃO ESCOLAR (2x), Gestão Escolar, LER OUVIR E CONTAR, LER, OUVIR E CONTAR, PROJETO CATAVENTO 2/3, TRÂNSITO LEGAL
- **Teste**: SMOKE NAO_SUPER, Test Detail, Test Proj, Test Project, Teste Auto NAO_SUPER

---

## ⚠️ GAPS E INCONSISTÊNCIAS

### 1. **Setor não modelado no sistema**
- ❌ Não existe campo "setor" em `Projeto`
- ❌ Setor é apenas derivado da aba da planilha durante ETL
- ✅ Workaround: Usar filtro `sector` na API `/api/availability/monthly/`

### 2. **Gerência não modelada no sistema**
- ❌ Não existe modelo `Gerencia` ou campo `gerencia` em `Projeto`
- ❌ Mapeamento existe apenas na planilha de produtos
- ⚠️ Impacto: Impossível filtrar projetos por gerência no sistema

### 3. **Gerente modelado no sistema** ✅ RESOLVIDO (2025-11-17)
- ✅ Campo `gerente` FK existe em `Gerencia` (vincula Usuario)
- ✅ Grupo "Gerência" tem 7 usuários (seeded com `seed_gerentes`)
- ✅ 4 gerências com gerente vinculado (SUPERINTENDENCIA, GERENCIA 2, 4, 5)

### 4. **Duplicação de projetos**
- ⚠️ "LEIO ESCREVO E CALCULO" (com vírgulas) e "LEIO, ESCREVO E CALCULO" são 2 registros
- ⚠️ "GESTÃO ESCOLAR" (uppercase) e "Gestão Escolar" (title case) são 2 registros
- ⚠️ "LER OUVIR E CONTAR" e "LER, OUVIR E CONTAR" são 2 registros

### 5. **Projetos de teste não isolados**
- ⚠️ SMOKE SUPER, SMOKE NAO_SUPER, TESTE E2E, Test Detail, Test Proj, Test Project, Teste Auto SUPER/NAO_SUPER (8 projetos) poluem lista de produção

### 6. **Eventos Fluir em planilha separada**
- ⚠️ 174 eventos do Fluir em "Acompanhamento de Agenda _ Fluir (1).xlsx"
- ❌ NÃO estão na planilha principal "Acompanhamento de Agenda _ 2025.xlsx"
- ⚠️ Sistema NÃO importou esses eventos

### 7. **Fluxo incorreto de projetos SUPERINTENDENCIA**
- ⚠️ LER, OUVIR E CONTAR está como NAO_SUPER mas deveria ser SUPER (está na lista SUPERINTENDENCIA de produtos)
- ⚠️ PROJETO CATAVENTO 2/3 estão como NAO_SUPER mas deveriam ser SUPER

---

## ✅ RECOMENDAÇÕES

### 1. Modelar Gerência e Setor no sistema

**Sugestão de modelo**:

```python
class Gerencia(models.Model):
    nome = models.CharField(max_length=50, unique=True)  # GERENCIA 2, GERENCIA 3, etc.
    nome_setor = models.CharField(max_length=100)  # Vidas, ACerta, Fluir, etc.
    gerente = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)

class Projeto(models.Model):
    # ... campos existentes ...
    gerencia = models.ForeignKey(Gerencia, on_delete=models.PROTECT, null=True)
```

**Benefícios**:
- Filtrar projetos por gerência na API
- Atribuir gerentes aos setores
- Relatórios por gerência

### 2. Limpar duplicação de projetos

```bash
# Consolidar projetos duplicados
UPDATE core_projeto SET nome = 'LEIO, ESCREVO E CALCULO' WHERE nome = 'LEIO ESCREVO E CALCULO';
UPDATE core_projeto SET nome = 'GESTÃO ESCOLAR' WHERE nome = 'Gestão Escolar';
UPDATE core_projeto SET nome = 'LER, OUVIR E CONTAR' WHERE nome = 'LER OUVIR E CONTAR';
```

### 3. Marcar projetos de teste

```python
class Projeto(models.Model):
    # ... campos existentes ...
    is_test = models.BooleanField(default=False, help_text="Projeto de teste (não mostrar em produção)")
```

### 4. Importar eventos do Fluir

```bash
# Criar ETL para "Acompanhamento de Agenda _ Fluir (1).xlsx"
python manage.py etl_import_fluir --dry-run
python manage.py etl_import_fluir --apply
```

### 5. Corrigir fluxo de projetos SUPERINTENDENCIA

```sql
UPDATE core_projeto SET fluxo = 'SUPER' WHERE nome IN (
    'LER, OUVIR E CONTAR',
    'PROJETO CATAVENTO 2',
    'PROJETO CATAVENTO 3'
);
```

### 6. Usar grupo "Gerência"

```python
# Atribuir 7 gerentes ao grupo "Gerência"
# Atualizar permissions para esse grupo
```

---

## 📊 SUMÁRIO FINAL

| Conceito | Na Planilha | No Sistema | Status |
|----------|-------------|------------|--------|
| **Gerências** | 8 (SUPER, G2-G6, GINDIVIDUAL) | ❌ Não modelado | 🔴 GAP |
| **Setores** | 10 (Super, Vidas, Fluir, ACerta, Brincando, Sou da Paz, +individual) | ❌ Apenas em ETL | 🔴 GAP |
| **Projetos** | 31 únicos + variantes | ✅ 46 (incluindo 8 teste) | 🟡 Duplicação |
| **Cargos** | 3 (Formador, Coordenador, Gerente) | ✅ 6 grupos Django | ✅ OK |
| **Usuários** | 117 ativos (planilha) | ✅ **128** (90 Form + 37 Coord + 1 Super + outros) **[ATUALIZADO 01/12]** | ✅ OK |
| **Eventos Fluir** | 174 (planilha própria) | ❌ Não importados | 🔴 GAP |

---

**Gerado em**: 2025-11-14 20:45
**Fontes**:
- `Cópia de Usuários.xlsx` (117 usuários ativos)
- `Cópia de Planilha de Controle - 2025.xlsx` (aba COORD, FILTRO_PROD)
- `produtos.xlsx` (139 produtos, 31 projetos únicos)
- `Acompanhamento de Agenda _ Fluir (1).xlsx` (174 eventos)
- Banco PostgreSQL v2 (46 projetos, 85 usuários)
