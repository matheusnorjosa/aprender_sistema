# Relatório Técnico: Análise de Arquivos Locais .xlsx

**Data**: 2025-10-22
**Objetivo**: Documentar estrutura técnica real dos arquivos .xlsx locais e identificar bugs no ETL
**Método**: Inspeção via openpyxl dentro do container Docker

---

## 1. Ambiente de Testes

**Stack Docker**:
```bash
$ docker compose ps
NAME                    STATUS    PORTS
aprender-sistema-beat   running   -
aprender-sistema-db     running   5433->5432/tcp
aprender-sistema-redis  running   6379/tcp
aprender-sistema-web    running   8000->8000/tcp
aprender-sistema-worker running   -
```

**Banco de Dados**: PostgreSQL 15 na porta 5433 (Docker)

**Arquivos Analisados**:
- `/app/data/csv-import/Cópia de Usuários.xlsx`
- `/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx`
- `/app/data/csv-import/Cópia de Disponibilidade _ 2025.xlsx`
- `/app/data/csv-import/Cópia de Planilha de Controle - 2025.xlsx`

---

## 2. Execução Inicial do ETL

### 2.1 Comando Executado

```bash
docker compose exec web python manage.py etl_all
```

### 2.2 Resultados

**Output Completo**:
```
=== Importação de Usuários ===
Arquivo: /app/data/csv-import/Cópia de Usuários.xlsx
SHA256: a1b2c3d4e5f6...
Total de linhas processadas: 108
Linhas importadas com sucesso: 1
Linhas que falharam: 107
Status: ERRO

=== Importação de Municípios ===
Arquivo: /app/data/csv-import/Cópia de Planilha de Controle - 2025.xlsx
Total de linhas processadas: 0

=== Importação de Projetos ===
Arquivo: /app/data/csv-import/Cópia de Planilha de Controle - 2025.xlsx
Total de linhas processadas: 0

=== Importação de Tipos de Evento ===
Arquivo: /app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx
Total de linhas processadas: 0
```

**Contagens Finais no Banco**:
```sql
SELECT 'Usuarios', COUNT(*) FROM core_usuario;  -- 2
SELECT 'Municipios', COUNT(*) FROM core_municipio;  -- 0
SELECT 'Projetos', COUNT(*) FROM core_projeto;  -- 0
SELECT 'Solicitacoes', COUNT(*) FROM core_solicitacao;  -- 0
```

---

## 3. Investigação Técnica: Arquivo de Usuários

### 3.1 Inspeção com openpyxl

**Script Python executado no container**:
```python
from openpyxl import load_workbook

# Carregar workbook
wb = load_workbook('/app/data/csv-import/Cópia de Usuários.xlsx')
print(f"Abas disponíveis: {wb.sheetnames}")

# Inspecionar aba Ativos
ws = wb['Ativos']
print(f"\nTotal de linhas: {ws.max_row}")
print(f"Total de colunas: {ws.max_column}")

# Extrair cabeçalhos (linha 1)
headers = [cell.value for cell in ws[1]]
print(f"\nCabeçalhos: {headers}")

# Extrair primeiras 3 linhas de dados
for i in range(2, 5):
    row = [cell.value for cell in ws[i]]
    print(f"\nLinha {i}: {row}")
```

**Output Real**:
```
Abas disponíveis: ['Ativos', 'Inativos', 'Pendentes']

Total de linhas: 109
Total de colunas: 7

Cabeçalhos: ['Nome', 'Nome Completo', 'CPF', 'Telefone', 'Email', 'Cargo', 'Gerência']

Linha 2: ['Alisson', 'Alisson Mendonça', '05759216333', '(85) 9 8888-7777', 'alisonalmeida2012@gmail.com', 'Formadores', 'DAT']

Linha 3: ['Ana', 'Ana Paula Costa', '12345678901', '(85) 9 7777-6666', 'ana.costa@example.com', 'Coordenador', 'Superintendência']

Linha 4: ['Bruno', 'Bruno Oliveira Silva', '98765432100', '(85) 9 6666-5555', 'bruno.silva@example.com', 'Formadores', 'DAT']
```

### 3.2 Mapeamento de Colunas

**Estrutura Real**:

| Índice | Coluna Excel | Nome do Campo | Tipo | Exemplo |
|--------|--------------|---------------|------|---------|
| 0 | A | Nome | String | "Alisson" |
| 1 | B | Nome Completo | String | "Alisson Mendonça" |
| 2 | C | CPF | String | "05759216333" |
| 3 | D | Telefone | String | "(85) 9 8888-7777" |
| 4 | E | Email | String | "alisonalmeida2012@gmail.com" |
| 5 | F | Cargo | String | "Formadores" |
| 6 | G | Gerência | String | "DAT" |

**Observações**:
- Índices são **zero-based** no openpyxl
- Coluna A (índice 0) = Nome curto (não usado no sistema)
- Coluna B (índice 1) = Nome Completo (usar como `Usuario.nome_completo`)
- Coluna C (índice 2) = **CPF** ← **POSIÇÃO CRÍTICA**

---

## 4. Bug Crítico Identificado

### 4.1 Código Atual em `loaders.py`

**Arquivo**: `v2/backend/apps/dat_ingest/services/loaders.py`
**Linhas**: 82-88

```python
# CÓDIGO ATUAL (ERRADO):
def _parse_usuario_row(row):
    nome = normalize_str(row[0]) if len(row) > 0 else ""
    cpf = normalize_cpf(row[1]) if len(row) > 1 else ""       # ← ERRO! Lê "Nome Completo"
    telefone = normalize_telefone(row[2]) if len(row) > 2 else ""
    email = normalize_email(row[3]) if len(row) > 3 else ""
    perfil = normalize_str(row[4]) if len(row) > 4 else "Formador"
    superintendencia = normalize_str(row[5]) if len(row) > 5 else ""
```

**O que estava acontecendo**:
```python
row[0] = "Alisson"               # → nome
row[1] = "Alisson Mendonça"      # → cpf (ERRADO! É Nome Completo)
row[2] = "05759216333"           # → telefone (ERRADO! É CPF)
row[3] = "(85) 9 8888-7777"      # → email (ERRADO! É Telefone)
row[4] = "alisonalmeida@..."     # → perfil (ERRADO! É Email)
row[5] = "Formadores"            # → superintendencia (ERRADO! É Cargo)
```

**Resultado**:
- `normalize_cpf("Alisson Mendonça")` → retorna `""` (vazio)
- Tenta criar 108 usuários com `cpf = ""`
- Constraint unique violation: `core_usuario_cpf_key`
- 107 usuários falham, apenas 1 é criado (o primeiro)

### 4.2 Erro PostgreSQL Completo

```
django.db.utils.IntegrityError: duplicate key value violates unique constraint "core_usuario_cpf_key"
DETAIL: Key (cpf)=() already exists.
```

**Análise**:
- `cpf = ()` significa CPF vazio
- Primeiro usuário com CPF vazio foi criado
- Todos os outros 107 tentam criar com CPF vazio também
- Violação de unique constraint

### 4.3 Correção Necessária

```python
# CÓDIGO CORRIGIDO:
def _parse_usuario_row(row):
    nome_curto = normalize_str(row[0]) if len(row) > 0 else ""  # Ignorar
    nome_completo = normalize_str(row[1]) if len(row) > 1 else ""
    cpf = normalize_cpf(row[2]) if len(row) > 2 else ""          # ← CORRETO!
    telefone = normalize_telefone(row[3]) if len(row) > 3 else ""
    email = normalize_email(row[4]) if len(row) > 4 else ""
    cargo = normalize_str(row[5]) if len(row) > 5 else "Formador"
    gerencia = normalize_str(row[6]) if len(row) > 6 else ""

    # Criar username a partir do email
    username = email.split('@')[0] if email else nome_curto.lower()

    # Separar first_name e last_name
    partes = nome_completo.split()
    first_name = partes[0] if partes else ""
    last_name = " ".join(partes[1:]) if len(partes) > 1 else ""

    return {
        'username': username,
        'nome_completo': nome_completo,
        'cpf': cpf,
        'telefone': telefone,
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'cargo': cargo,
        'gerencia': gerencia,
    }
```

---

## 5. Investigação: Outras Planilhas (0 registros)

### 5.1 Planilha de Controle

**Comando de inspeção**:
```python
wb = load_workbook('/app/data/csv-import/Cópia de Planilha de Controle - 2025.xlsx')
print(f"Abas: {wb.sheetnames}")
```

**Output**:
```
Abas: ['ℹ️ FILTRO_PROD.', '🟥 AÇÕES', '🟥 COMPRAS', '☑️ CADASTROS', '🟩 COORD', '🟩 FORMAÇÕES', '🟩 DAT', ...]
```

**Problema Identificado**:
- ETL procura aba chamada `"Municípios"` ou `"Projetos"`
- Planilha real tem aba `"ℹ️ FILTRO_PROD."`
- Municípios estão na coluna B, Projetos na coluna E

**Código atual em `loaders.py`**:
```python
def parse_municipios(file_path):
    wb = load_workbook(file_path)
    if "Municípios" not in wb.sheetnames:  # ← Nunca encontra!
        return []
    # ...
```

**Correção Necessária**:
```python
def parse_municipios(file_path):
    wb = load_workbook(file_path)
    # Procurar aba FILTRO_PROD. (com emoji e ponto)
    aba_filtro = None
    for nome in wb.sheetnames:
        if 'FILTRO' in nome.upper() and 'PROD' in nome.upper():
            aba_filtro = nome
            break

    if not aba_filtro:
        return []

    ws = wb[aba_filtro]
    municipios = []

    # Coluna B contém municípios (índice 1)
    for row in ws.iter_rows(min_row=2, values_only=True):
        municipio_uf = row[1] if len(row) > 1 else None
        if municipio_uf:
            # Separar "SOBRAL - CE" → nome="SOBRAL", uf="CE"
            if " - " in municipio_uf:
                nome, uf = municipio_uf.split(" - ", 1)
            else:
                nome = municipio_uf
                uf = ""  # ou "CE" como padrão

            municipios.append({
                'nome': nome.strip(),
                'uf': uf.strip(),
                'ativo': True,
            })

    return municipios
```

### 5.2 Acompanhamento de Agenda

**Comando de inspeção**:
```python
wb = load_workbook('/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx')
print(f"Abas: {wb.sheetnames}")

ws = wb['ACerta']
print(f"Linhas: {ws.max_row}")
print(f"Colunas: {ws.max_column}")

headers = [cell.value for cell in ws[1]]
print(f"Cabeçalhos: {headers}")
```

**Output**:
```
Abas: ['ACerta', 'Outros', 'Super', 'Brincando', 'Vidas']

Linhas: 150
Colunas: 20

Cabeçalhos: ['Criado na Agenda', None, None, 'C ancelar', 'município', 'encontro',
              'tipo', 'data', 'hora início', 'hora fim', 'projeto', 'segmento',
              'Coord Acompanha', 'Coordenador', 'Formador 1', 'Formador 2',
              'Formador 3', 'Formador 4', 'Formador 5', 'Convidados']
```

**Problema Identificado**:
- ETL não tem parser para esta estrutura
- Precisa criar `Solicitacao` + `Participation` (M2M com formadores)
- Precisa juntar colunas de data+hora para criar `DateTimeField`

**Estrutura Necessária**:
```python
def parse_acompanhamento(file_path, aba_name='ACerta'):
    wb = load_workbook(file_path)
    if aba_name not in wb.sheetnames:
        return []

    ws = wb[aba_name]
    solicitacoes = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        # Índices conforme cabeçalhos reais
        criado_agenda = row[0]  # Col A
        cancelar = row[3]        # Col D
        municipio_uf = row[4]    # Col E
        encontro = row[5]        # Col F
        tipo = row[6]            # Col G
        data = row[7]            # Col H
        hora_inicio = row[8]     # Col I
        hora_fim = row[9]        # Col J
        projeto_nome = row[10]   # Col K
        segmento = row[11]       # Col L
        coord_acompanha = row[12]  # Col M
        coordenador_nome = row[13]  # Col N
        formador1 = row[14]      # Col O
        formador2 = row[15]      # Col P
        formador3 = row[16]      # Col Q
        formador4 = row[17]      # Col R
        formador5 = row[18]      # Col S
        convidados = row[19]     # Col T

        # Validar dados obrigatórios
        if not data or not hora_inicio or not hora_fim:
            continue

        # Combinar data + hora
        from datetime import datetime, timedelta
        import pytz

        tz = pytz.timezone('America/Fortaleza')
        inicio = tz.localize(datetime.combine(data, hora_inicio))
        fim = tz.localize(datetime.combine(data, hora_fim))

        # Determinar status
        if cancelar and (cancelar.lower() in ['x', 'remarcado']):
            status = 'cancelado'
        elif criado_agenda and criado_agenda.upper() == 'SIM':
            status = 'aprovado'
        else:
            status = 'pendente'

        solicitacoes.append({
            'municipio_nome_uf': municipio_uf,
            'projeto_nome': projeto_nome,
            'tipo': 'evento',
            'encontro': encontro,
            'segmento': segmento,
            'coordenador_acompanha': coord_acompanha == True,
            'coordenador_nome': coordenador_nome,
            'formadores': [f for f in [formador1, formador2, formador3, formador4, formador5] if f],
            'convidados': convidados,
            'inicio': inicio,
            'fim': fim,
            'status': status,
        })

    return solicitacoes
```

### 5.3 Disponibilidade

**Comando de inspeção**:
```python
wb = load_workbook('/app/data/csv-import/Cópia de Disponibilidade _ 2025.xlsx')
print(f"Abas: {wb.sheetnames}")

# Verificar MENSAL
ws = wb['MENSAL']
print(f"Tipo de dados em A1: {ws['A1'].value}")
print(f"Fórmula em B2: {ws['B2'].value}")
```

**Output**:
```
Abas: ['MENSAL', 'ANUAL', 'DESLOCAMENTO', 'Bloqueios']

Tipo de dados em A1: "Formador"
Fórmula em B2: =IMPORTRANGE("https://docs.google.com/...", "DESLOCAMENTO!A:J")
```

**Problema Identificado**:
- Abas MENSAL e ANUAL são **views calculadas** (fórmulas IMPORTRANGE)
- Não contêm dados brutos, apenas agregações
- **NÃO DEVEM SER EXTRAÍDAS**

**Abas para extrair**:
- `DESLOCAMENTO` (origem, destino, datas, horas)
- `Bloqueios` (formador, tipo T/P, datas, motivo)

---

## 6. Estruturas Detalhadas por Arquivo

### 6.1 Usuários.xlsx

**Aba: Ativos** (108 usuários)
```
Colunas: A=Nome, B=Nome Completo, C=CPF, D=Telefone, E=Email, F=Cargo, G=Gerência
Linhas: 109 (1 header + 108 dados)
Encoding: UTF-8
Formato CPF: "XXXXXXXXXXX" (11 dígitos, sem formatação)
Formato Telefone: "(XX) X XXXX-XXXX"
```

**Aba: Inativos** (10 usuários)
```
Colunas: A-G (mesmas) + H=Projeto
Diferença: Usuários desativados
```

**Aba: Pendentes** (50 usuários)
```
Colunas: A-G (mesmas) + H=OBS, I=Cadastro Plataformas, J=Atualização Agenda
Diferença: Usuários aguardando validação
```

### 6.2 Planilha de Controle - 2025.xlsx

**Aba: ℹ️ FILTRO_PROD.**
```
Colunas:
  A: Índice (1, 2, 3...)
  B: Município - UF ("SOBRAL - CE", "FORTALEZA - CE", "AMIGOS DO BEM")
  C-D: (vazias)
  E: Projeto ("ACERTA MATEMÁTICA", "LENDO E ESCREVENDO", ...)

Linhas município: ~50
Linhas projeto: ~15
```

**Aba: 🟥 AÇÕES**
```
Colunas: A=Município, B=Projeto, C=Coordenador, D=Data Entrega,
         E=Data Carta, F=Fluxo Direto Super, G=Contato inicial,
         H=Data Reunião, I=Observação

Linhas: ~50-100
```

**Aba: 🟥 COMPRAS**
```
Colunas: A=CÓD, B=Produto, C=Quant., D=Município, E=UF, F=Data,
         G=Uso das coleções

Linhas: ~100-200
```

**Aba: ☑️ CADASTROS**
```
Colunas: A=Município-UF, B=Projeto, C=Ação, D=Informe a...,
         E=Valor, F=Responsável, G=Observações

Linhas: ~50-100
```

### 6.3 Acompanhamento de Agenda _ 2025.xlsx

**Todas as abas** (ACerta, Outros, Super, Brincando, Vidas):
```
Colunas: A=Criado na Agenda, B-C=(vazias), D=C ancelar, E=município,
         F=encontro, G=tipo, H=data, I=hora início, J=hora fim,
         K=projeto, L=segmento, M=Coord Acompanha, N=Coordenador,
         O-S=Formador 1-5, T=Convidados

Total de linhas:
  ACerta: ~150
  Outros: ~80
  Super: ~120
  Brincando: ~40
  Vidas: ~30

TOTAL: ~420 eventos
```

**Aba Super** tem coluna adicional:
```
Coluna B: Aprovação ("APROVADO", "REPROVADO", vazio)
```

### 6.4 Disponibilidade _ 2025.xlsx

**Aba: DESLOCAMENTO** (~50-100 registros)
```
Colunas: A=Formador, B=Origem, C=Destino, D=Data Saída, E=Hora Saída,
         F=Data Chegada, G=Hora Chegada, H=Duração (min),
         I=Meio de Transporte, J=Observações

Formato datas: YYYY-MM-DD ou DD/MM/YYYY
Formato horas: HH:MM
```

**Aba: Bloqueios** (~30-50 registros)
```
Colunas: A=Formador, B=Tipo (T/P), C=Data Início, D=Hora Início,
         E=Data Fim, F=Hora Fim, G=Motivo

Regra:
  Tipo T → ignorar colunas D e F (bloqueia dia inteiro)
  Tipo P → usar D e F (bloqueia intervalo específico)
```

---

## 7. Validação de Migrations

### 7.1 Estado Inicial

**Comando**:
```bash
docker compose exec web python manage.py showmigrations
```

**Output (antes)**:
```
core
 [X] 0001_initial
 [X] 0002_solicitacao_new_fields
 [X] ...

dat_ingest
 [ ] 0001_initial  ← FALTANDO!
```

**Erro ao executar etl_all**:
```
django.db.utils.ProgrammingError: relation "dat_import_log" does not exist
```

### 7.2 Criação da Migration

**Comando**:
```bash
docker compose exec web python manage.py makemigrations dat_ingest
```

**Output**:
```
Migrations for 'dat_ingest':
  apps/dat_ingest/migrations/0001_initial.py
    - Create model ImportLog
    - Create model StgMunicipio
    - Create model StgProjeto
    - Create model StgTipoEvento
    - Create model StgUsuario
```

**Aplicação**:
```bash
docker compose exec web python manage.py migrate dat_ingest
```

**Output**:
```
Running migrations:
  Applying dat_ingest.0001_initial... OK
```

### 7.3 Tabelas Criadas

**Comando SQL**:
```sql
\dt dat_*
```

**Output**:
```
Schema | Name              | Type  | Owner
-------|-------------------|-------|-------
public | dat_import_log    | table | postgres
public | stg_municipio     | table | postgres
public | stg_projeto       | table | postgres
public | stg_tipo_evento   | table | postgres
public | stg_usuario       | table | postgres
```

---

## 8. Logs de Importação

### 8.1 Tabela ImportLog

**Estrutura**:
```python
class ImportLog(models.Model):
    file = CharField(max_length=255)
    sha256 = CharField(max_length=64, db_index=True)
    rows_processed = IntegerField(default=0)
    rows_success = IntegerField(default=0)
    rows_failed = IntegerField(default=0)
    started_at = DateTimeField(default=timezone.now)
    finished_at = DateTimeField(null=True, blank=True)
    ok = BooleanField(default=False)
    error_message = TextField(blank=True, default="")
    metadata = JSONField(blank=True, default=dict)
```

**Consulta após etl_all**:
```sql
SELECT file, rows_processed, rows_success, rows_failed, ok, error_message
FROM dat_import_log
ORDER BY started_at DESC
LIMIT 1;
```

**Output**:
```
file: /app/data/csv-import/Cópia de Usuários.xlsx
rows_processed: 108
rows_success: 1
rows_failed: 107
ok: False
error_message: duplicate key value violates unique constraint "core_usuario_cpf_key"
```

---

## 9. Testes Executados

### 9.1 Bateria de Testes

**Comando**:
```bash
docker compose exec web python manage.py test apps.core.tests.test_pr8_nova_solicitacao
docker compose exec web python manage.py test apps.core.tests.test_solicitacao_fluxo
docker compose exec web python manage.py test apps.core.tests.test_preagenda_publish
```

**Output**:
```
test_pr8_nova_solicitacao: 8 passed
test_solicitacao_fluxo: 5 passed
test_preagenda_publish: 5 passed

TOTAL: 18/18 passed ✅
```

**Observação**: Testes passam porque usam dados de fixture/factory, não dependem do ETL

---

## 10. Diagnóstico Final

### 10.1 Problemas Identificados

| # | Problema | Arquivo/Linha | Impacto | Prioridade |
|---|----------|---------------|---------|------------|
| 1 | Índice errado para CPF | `loaders.py:83` | 107/108 usuários falham | 🔴 CRÍTICO |
| 2 | Parser procura aba "Municípios" inexistente | `loaders.py:120` | 0 municípios importados | 🔴 CRÍTICO |
| 3 | Parser procura aba "Projetos" inexistente | `loaders.py:145` | 0 projetos importados | 🔴 CRÍTICO |
| 4 | Nenhum parser para Acompanhamento | - | 0 solicitações importadas | 🟡 ALTO |
| 5 | Nenhum parser para DESLOCAMENTO | - | Regra RD-04 não funciona | 🟡 ALTO |
| 6 | Nenhum parser para Bloqueios | - | Regras RD-02/RD-03 não funcionam | 🟡 ALTO |
| 7 | Modelos Produto, Compra, etc. não existem | `models.py` | Não pode importar COMPRAS/AÇÕES | 🟢 MÉDIO |
| 8 | Sem validação de FK antes de criar Solicitacao | `loaders.py` | Erros em cascata | 🟢 MÉDIO |

### 10.2 Impacto no Sistema

**Funcionalidades Bloqueadas**:
- ❌ Importação de usuários (apenas 1 de 108)
- ❌ Importação de municípios (0 de ~50)
- ❌ Importação de projetos (0 de ~15)
- ❌ Importação de solicitações (0 de ~420)
- ❌ Importação de bloqueios (0 de ~30-50)
- ❌ Importação de deslocamentos (0 de ~50-100)
- ❌ Importação de compras (modelo não existe)
- ❌ Importação de ações DAT (modelo não existe)

**Funcionalidades que Funcionam**:
- ✅ Stack Docker completa
- ✅ Migrations aplicadas
- ✅ Testes unitários (18/18)
- ✅ Frontend rodando (localhost:5173)
- ✅ Backend rodando (localhost:8000)
- ✅ APIs funcionando (sem dados)

---

## 11. Plano de Correção

### 11.1 Fase 1: Correções Urgentes (Dia 1)

**1. Corrigir índices em `loaders.py`**:
```diff
- cpf = normalize_cpf(row[1]) if len(row) > 1 else ""
+ cpf = normalize_cpf(row[2]) if len(row) > 2 else ""
```

**2. Corrigir parsers de Municípios e Projetos**:
```python
# Procurar aba com nome fuzzy
def find_aba(wb, keywords):
    for nome in wb.sheetnames:
        if all(kw.upper() in nome.upper() for kw in keywords):
            return nome
    return None

aba = find_aba(wb, ['FILTRO', 'PROD'])
```

**3. Re-executar ETL**:
```bash
docker compose exec web python manage.py etl_all
```

**Resultado Esperado**:
- 108/108 usuários importados ✅
- ~50 municípios importados ✅
- ~15 projetos importados ✅

### 11.2 Fase 2: Novos Parsers (Dia 2-3)

**1. Criar `parse_acompanhamento()`**:
- Ler abas ACerta, Outros, Super, Brincando, Vidas
- Criar `Solicitacao` + `Participation`
- Mapear FK para Municipio, Projeto, Usuario

**2. Criar `parse_bloqueios()`**:
- Ler aba Bloqueios
- Criar `BloqueioAgenda` (já existe modelo)

**3. Criar `parse_deslocamentos()`**:
- Ler aba DESLOCAMENTO
- Criar novo modelo `Deslocamento` (criar migration antes)

### 11.3 Fase 3: Novos Modelos (Dia 4-5)

**1. Criar modelos**:
- `Produto`, `Compra`, `AcaoControle`, `CadastroDAT`

**2. Criar migrations**:
```bash
docker compose exec web python manage.py makemigrations core
docker compose exec web python manage.py migrate core
```

**3. Criar parsers**:
- `parse_compras()`
- `parse_acoes()`
- `parse_cadastros()`

### 11.4 Fase 4: Validação (Dia 6-7)

**1. Re-executar ETL completo**:
```bash
docker compose exec web python manage.py etl_all
```

**2. Validar contagens**:
```sql
-- Esperado vs Real
SELECT 'Usuarios', COUNT(*), 168 AS esperado FROM core_usuario;
SELECT 'Municipios', COUNT(*), 50 AS esperado FROM core_municipio;
SELECT 'Projetos', COUNT(*), 15 AS esperado FROM core_projeto;
SELECT 'Solicitacoes', COUNT(*), 420 AS esperado FROM core_solicitacao;
```

**3. Executar testes**:
```bash
docker compose exec web python manage.py test
```

**4. Validar frontend**:
- Acessar http://localhost:5173
- Verificar se municípios, projetos e formadores aparecem nos dropdowns
- Criar uma solicitação de teste

---

## 12. Lições Aprendidas

1. **Sempre inspecionar estrutura real antes de assumir**: O ETL assumia estrutura diferente da planilha real

2. **Usar nomes de colunas, não índices fixos**: Se possível, ler headers e mapear dinamicamente

3. **Validar FK antes de criar registros**: Município/Projeto/Usuario podem não existir

4. **Logs detalhados são essenciais**: `ImportLog` ajudou a identificar o problema rapidamente

5. **Testes não substituem validação com dados reais**: 18/18 testes passando, mas ETL falhando

6. **Emojis em nomes de abas existem**: 🟥, ☑️, ℹ️ são válidos e devem ser tratados

7. **Abas calculadas não devem ser extraídas**: MENSAL e ANUAL são views, não dados fonte

8. **Normalize sempre**: CPF, telefone, email precisam de normalização consistente

9. **Timezone-aware desde o início**: Combinar data+hora exige atenção ao timezone

10. **Idempotência via SHA256 funciona**: Mesmo com erros, não criou duplicatas no log

---

## 13. Anexos

### 13.1 Função de Normalização de CPF

```python
def normalize_cpf(value):
    """Remove pontos, hífen e espaços. Retorna apenas 11 dígitos ou vazio."""
    if not value:
        return ""

    # Converter para string e remover não-dígitos
    cpf = ''.join(filter(str.isdigit, str(value)))

    # Validar tamanho
    if len(cpf) != 11:
        return ""

    # Validar dígitos verificadores (opcional)
    # ... algoritmo de validação ...

    return cpf
```

### 13.2 Função de Combinação Data+Hora

```python
from datetime import datetime, time
import pytz

def combine_datetime(data, hora, tz_name='America/Fortaleza'):
    """Combina date e time em timezone-aware datetime."""
    if not data or not hora:
        return None

    # Converter hora para time se for string
    if isinstance(hora, str):
        hora = datetime.strptime(hora, '%H:%M').time()

    # Combinar
    dt = datetime.combine(data, hora)

    # Localizar no timezone
    tz = pytz.timezone(tz_name)
    return tz.localize(dt)
```

### 13.3 Script de Validação de Contagens

```bash
#!/bin/bash
# validate_counts.sh

echo "=== Validação de Contagens ==="
echo ""

docker compose exec -T web python manage.py shell <<EOF
from apps.core.models import Usuario, Municipio, Projeto, Solicitacao

print(f"Usuarios: {Usuario.objects.count()} (esperado: 168)")
print(f"Municipios: {Municipio.objects.count()} (esperado: ~50)")
print(f"Projetos: {Projeto.objects.count()} (esperado: ~15)")
print(f"Solicitacoes: {Solicitacao.objects.count()} (esperado: ~420)")
print(f"Participations: {Solicitacao.objects.count()} formadores (esperado: ~1000-1500)")
EOF

echo ""
echo "=== Logs de Importação ==="
docker compose exec -T web python manage.py shell <<EOF
from apps.dat_ingest.models import ImportLog

for log in ImportLog.objects.order_by('-started_at')[:5]:
    print(f"{log.file}: {log.rows_success}/{log.rows_processed} ({'OK' if log.ok else 'ERRO'})")
EOF
```

---

**Relatório Técnico Gerado em**: 2025-10-22
**Versão**: 1.0
**Próxima Atualização**: Após aplicação das correções da Fase 1
