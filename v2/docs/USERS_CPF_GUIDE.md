# Guia: Auditoria e Atribuição de CPF

Este guia documenta as ferramentas para auditar e atribuir CPFs aos usuários do sistema baseado em planilhas Excel.

## Visão Geral

**Comandos disponíveis**:
1. `audit_agenda_users` — Auditoria read-only (cross-check entre cadastro e agenda)
2. `assign_cpf_from_excel` — Atribuição de CPFs (DRY-RUN → APPLY)

**Admin Django**:
- Filtro: CPF "Ausente" / "Preenchido"
- Ação: Exportar usuários sem CPF (CSV)

---

## Configuração de Diretórios

**Diretórios ETL configuráveis via variáveis de ambiente** (PR #53):

- **ETL_OUTPUT_DIR**: Diretório para relatórios gerados (JSON, CSV)
  - Default: `{BASE_DIR}/out_etl` (ex: `/app/out_etl` no Docker)
  - Customizar: `export ETL_OUTPUT_DIR=/custom/path`

- **ETL_DATA_DIR**: Diretório base para importação de planilhas
  - Default: `{BASE_DIR}/data/csv-import`
  - Customizar: `export ETL_DATA_DIR=/custom/data`

**Veja**: `v2/docs/ENV_VARS_ETL.md` para detalhes completos e exemplos de uso.

---

## 1. audit_agenda_users (Read-Only)

### Propósito

Faz cross-check entre:
- **Planilha de Usuários** (`Cópia de Usuários.xlsx`)
- **Planilha de Agenda** (`Cópia de Acompanhamento de Agenda _ 2025.xlsx`)

Identifica:
- Usuários cadastrados que aparecem na agenda
- Usuários **não cadastrados** que aparecem na agenda
- Usuários que aparecem em **múltiplos setores** (abas)
- **Duplicados** na mesma aba

### Estrutura das Planilhas

**Planilha de Usuários** (`Cópia de Usuários.xlsx`):
- Aba: `Ativos`
- Colunas: `Nome`, `Nome Completo`, `Email`, `CPF`

**Planilha de Agenda** (`Cópia de Acompanhamento de Agenda _ 2025.xlsx`):
- Abas: `ACerta`, `Super`, `Brincando`, `Vidas`, `Outros`
- Colunas:
  - Coluna **N**: Coordenador
  - Colunas **O-S**: Formador 1, Formador 2, ..., Formador 5
  - Coluna **T**: Convidados (emails separados por vírgula/ponto-e-vírgula)

### Lógica de Matching

**Por Nome** (Coordenador + Formadores):
- Normalização NFKD (remove acentos)
- Heurísticas:
  1. Exact match
  2. Subset tokens (qualquer direção)
  3. First + Last name match
  4. Jaccard similarity ≥ 0.6
- **Exclui** coluna "Convidados" do matching por nome

**Por Email** (Convidados):
- Normalização lowercase
- Match exato
- **Inclui** coluna "Convidados"

### Uso

```bash
# Docker
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \\
  python manage.py audit_agenda_users \\
    --users "/app/data/csv-import/Cópia de Usuários.xlsx" \\
    --agenda "/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx" \\
    --sheet-users "Ativos" \\
    --out "/app/out_etl"
```

### Saída

**Arquivos gerados** (em `/app/out_etl`):
1. `audit_users_crosscheck_report.json` — Relatório básico
2. `audit_users_crosscheck_enhanced.json` — Relatório com totals
3. `audit_users_encontrados_por_aba.csv` — Multi-setor (nome → abas)

**Estrutura do JSON**:
```json
{
  "abas_processadas": 5,
  "duplicados_por_aba": {
    "ACerta": 2,
    "Super": 0,
    ...
  },
  "encontrados_por_aba": {
    "ACerta": 45,
    "Super": 32,
    ...
  },
  "usuarios_nao_encontrados": {
    "ACerta": ["fulano silva", "ciclano santos"],
    "Super": ["beltrano costa"],
    ...
  },
  "multi_setor": {
    "joao silva": ["ACerta", "Super"],
    "maria santos": ["Brincando", "Vidas"],
    ...
  },
  "nomes_na_agenda_nao_cadastrados": {
    "top_20": [
      {"nome": "fulano silva", "freq": 10},
      {"nome": "ciclano santos", "freq": 5},
      ...
    ],
    "total_unique": 42
  },
  "totals": {
    "abas": 5,
    "multi_setor_count": 8,
    "nao_cadastrados_unique": 42
  }
}
```

---

## 2. assign_cpf_from_excel (DRY-RUN/APPLY)

### Propósito

Atribui CPFs aos usuários do sistema baseado em planilha Excel.

**Workflow recomendado**:
1. **DRY-RUN** primeiro (default) → relata sem persistir
2. Revisar relatório (`assign_cpf_report.json`)
3. **APPLY** → persiste no banco

### Estrutura da Planilha

**Planilha de Usuários** (`Cópia de Usuários.xlsx`):
- Aba: `Ativos` (default, configurável)
- Colunas: `Nome`, `Nome Completo`, `Email`, `CPF`

### Lógica de Matching

**Preferência de Match**:
1. **Email** (preferencial, 1:1)
2. **Nome normalizado** (fallback, 1:1)

**Validações**:
- CPF: remove máscara e valida 11 dígitos
- Duplicidade de CPF na planilha → **conflicts**
- Email/nome ambíguo (múltiplos usuários) → **conflicts**
- CPF divergente (banco != planilha) → **conflicts**
- CPF inválido/ausente → **skipped**
- Usuário não encontrado → **skipped**
- **CPF placeholder (000000000XX)** → tratado como "ausente" (ver seção 9)

**Nota sobre CPF placeholder**:
O comando reconhece CPFs que começam com 9 zeros seguidos de 1-3 dígitos (ex: `00000000001`, `00000000099`) como "CPF ausente". Esses placeholders são usados **apenas em testes** devido às constraints do schema (`cpf` campo com `NOT NULL + UNIQUE`). Ver seção 9 para detalhes.

### Uso

#### DRY-RUN (não persiste)

```bash
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \\
  python manage.py assign_cpf_from_excel \\
    --path "/app/data/csv-import/Cópia de Usuários.xlsx" \\
    --sheet "Ativos"
```

#### APPLY (persiste)

```bash
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \\
  python manage.py assign_cpf_from_excel \\
    --path "/app/data/csv-import/Cópia de Usuários.xlsx" \\
    --sheet "Ativos" \\
    --apply
```

### Saída

**Arquivo gerado**: `/app/out_etl/assign_cpf_report.json`

**Estrutura do JSON**:
```json
{
  "mode": "DRY-RUN",  // ou "APPLY"
  "updated": [
    {
      "username": "joao_silva",
      "nome": "João Silva",
      "email": "joao@example.com",
      "cpf": "12345678901",
      "prev_cpf": "(vazio)",
      "match_method": "email"
    },
    ...
  ],
  "skipped": [
    {
      "nome": "Fulano Costa",
      "email": "fulano@example.com",
      "reason": "Usuário não encontrado no banco"
    },
    ...
  ],
  "conflicts": [
    {
      "nome": "Pedro Santos",
      "email": "pedro@example.com",
      "cpf": "11111111111",
      "reason": "CPF duplicado na planilha",
      "duplicados": ["Pedro Santos", "Pedro Santos Júnior"]
    },
    ...
  ],
  "totals": {
    "updated": 45,
    "skipped": 3,
    "conflicts": 2
  }
}
```

### Idempotência

**Re-run com --apply**: Não altera registros já atualizados (CPF banco == CPF planilha).

---

## 3. Admin Django — Filtro e Ação

### Filtro "CPF"

**Acesso**: Django Admin → Usuários → Filtro lateral

**Opções**:
- **Ausente**: Lista usuários com `cpf IS NULL` ou `cpf = ""`
- **Preenchido**: Lista usuários com CPF válido

### Ação "Exportar usuários sem CPF"

**Uso**:
1. Django Admin → Usuários
2. (Opcional) Aplicar filtro CPF: Ausente
3. Selecionar usuários
4. Ação: "Exportar usuários sem CPF (CSV)"
5. Download: `usuarios_sem_cpf.csv`

**Arquivos gerados**:
- HTTP download: `usuarios_sem_cpf.csv`
- Auditoria: `/app/out_etl/usuarios_sem_cpf.csv`

**Estrutura do CSV**:
```csv
Username,Email,Nome Completo,CPF,Cargo,Ativo
joao_silva,joao@example.com,João Silva,,Coordenador,Sim
maria_santos,maria@example.com,Maria Santos,,Formador,Sim
```

---

## 4. Cuidados com PII (Dados Pessoais)

**Informações sensíveis**: CPF, email, nome completo

**Recomendações**:
- ✅ Logs contêm apenas **contagens** (não mostram CPFs/nomes)
- ✅ Relatórios JSON/CSV mantidos em `/app/out_etl` (não comitados no Git)
- ✅ Revisar `conflicts` antes de APPLY (detectar divergências)
- ⚠️ Não compartilhar relatórios JSON/CSV publicamente
- ⚠️ Usar `--apply` apenas após revisão de DRY-RUN

---

## 5. Workflow Recomendado

### Cenário 1: Primeira Atribuição de CPFs

```bash
# 1. Auditoria: identificar não cadastrados
docker compose exec web python manage.py audit_agenda_users \\
  --users "/app/data/csv-import/Cópia de Usuários.xlsx" \\
  --agenda "/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx"

# 2. Revisar: out_etl/audit_users_crosscheck_enhanced.json
# Verificar: nao_cadastrados_unique, multi_setor

# 3. DRY-RUN: simular atribuição de CPFs
docker compose exec web python manage.py assign_cpf_from_excel \\
  --path "/app/data/csv-import/Cópia de Usuários.xlsx"

# 4. Revisar: out_etl/assign_cpf_report.json
# Verificar: conflicts (duplicados, divergências), skipped (inválidos)

# 5. APPLY: persistir CPFs
docker compose exec web python manage.py assign_cpf_from_excel \\
  --path "/app/data/csv-import/Cópia de Usuários.xlsx" \\
  --apply

# 6. Verificar: Admin → Filtro CPF: Ausente (deve reduzir)
```

### Cenário 2: Atualização Periódica

```bash
# 1. DRY-RUN: verificar mudanças
docker compose exec web python manage.py assign_cpf_from_excel \\
  --path "/app/data/csv-import/Cópia de Usuários.xlsx"

# 2. Revisar: out_etl/assign_cpf_report.json
# Focar em: conflicts (CPF divergente banco != planilha)

# 3. Se conflicts.length > 0: resolver manualmente antes de APPLY

# 4. APPLY: atualizar apenas novos
docker compose exec web python manage.py assign_cpf_from_excel \\
  --path "/app/data/csv-import/Cópia de Usuários.xlsx" \\
  --apply
```

### Cenário 3: Exportar Usuários sem CPF

```bash
# Admin Django
# 1. Usuários → Filtro: CPF = Ausente
# 2. Selecionar todos
# 3. Ação: Exportar usuários sem CPF (CSV)
# 4. Revisar: usuarios_sem_cpf.csv

# Alternativamente: via comando audit (mostra contexto de agenda)
docker compose exec web python manage.py audit_agenda_users \\
  --users "/app/data/csv-import/Cópia de Usuários.xlsx" \\
  --agenda "/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx"
```

---

## 6. Resolução de Conflitos

### Conflito: CPF duplicado na planilha

**Problema**: Dois usuários com mesmo CPF na planilha.

**Solução**:
1. Revisar planilha original
2. Corrigir erro de digitação ou identificar duplicata real
3. Atualizar planilha e re-rodar DRY-RUN

### Conflito: Email ambíguo (múltiplos usuários)

**Problema**: Dois usuários no banco com mesmo email.

**Solução**:
1. Revisar banco: `User.objects.filter(email="ambiguo@example.com")`
2. Corrigir email duplicado (manter apenas 1 ou diferenciar)
3. Re-rodar DRY-RUN

### Conflito: CPF divergente (banco != planilha)

**Problema**: Usuário já tem CPF no banco, mas planilha tem CPF diferente.

**Solução**:
1. Verificar qual CPF está correto (banco ou planilha)
2. Se planilha estiver correta: atualizar manualmente no Django Admin
3. Se banco estiver correto: atualizar planilha
4. Re-rodar DRY-RUN

---

## 7. Perguntas Frequentes

**Q: O comando `assign_cpf_from_excel` cria migrations?**
A: Não. Apenas atualiza o campo `cpf` de usuários existentes via `save(update_fields=["cpf"])`.

**Q: Posso reverter APPLY?**
A: Sim. A implementação é reversível:
1. Restaurar backup do banco (se disponível)
2. Ou atualizar CPFs manualmente via Django Admin
3. Ou re-rodar `assign_cpf_from_excel` com planilha anterior

**Q: O que acontece se rodar APPLY duas vezes?**
A: Idempotente. Segunda rodada detecta que CPF banco == CPF planilha e não altera.

**Q: Como testar sem afetar produção?**
A: Use DRY-RUN (default). Gera relatório completo sem persistir no banco.

**Q: Onde ficam os relatórios?**
A: `/app/out_etl` (não comitados no Git). Dentro do container Docker.

**Q: Como acessar relatórios fora do container?**
A: `docker compose cp aprender_v2-web-1:/app/out_etl ./local_out_etl`

---

## 8. CPF Placeholder (Apenas para Testes)

### Contexto

O campo `Usuario.cpf` possui as seguintes constraints no schema:
- `NOT NULL` — Não aceita NULL
- `UNIQUE` — Não aceita duplicatas

Isso impede que múltiplos usuários tenham `cpf=""` (string vazia) em testes, pois violaria a constraint `UNIQUE`.

### Solução: Padrão de Placeholder

O comando `assign_cpf_from_excel` reconhece CPFs que começam com **9 zeros seguidos de 1-3 dígitos** como "CPF ausente":

**Padrão**: `000000000XX` (onde XX = 01-99 ou 001-999)

**Exemplos**:
- `00000000001` → tratado como "ausente"
- `00000000002` → tratado como "ausente"
- `00000000099` → tratado como "ausente"

**Função de detecção** (`assign_cpf_from_excel.py`):
```python
def is_placeholder_cpf(cpf):
    """
    Detecta se um CPF é um placeholder (ex: 00000000001, 00000000002).

    Placeholders são CPFs que começam com 9 zeros seguidos de 1-3 dígitos.
    Usados em testes quando o schema não permite CPF ausente (NOT NULL + UNIQUE).

    Retorna: True se for placeholder, False caso contrário
    """
    if not cpf or len(cpf) != 11:
        return False

    # Padrão: 000000000XX (9 zeros + até 3 dígitos)
    return cpf.startswith('000000000')
```

### Uso Restrito

⚠️ **ATENÇÃO**: Placeholders devem ser usados **APENAS em testes**. Nunca em produção.

**Casos de uso válidos**:
- ✅ Testes unitários (`test_assign_cpf_command.py`)
- ✅ Fixtures de testes (`users_db` fixture)

**Casos de uso inválidos**:
- ❌ Usuários reais no banco de produção
- ❌ Planilhas de importação reais
- ❌ Qualquer ambiente de staging/produção

### Alternativas para Produção

Se precisar de "CPF ausente" em produção, considere:
1. **Migration** para alterar schema (`null=True, blank=True`)
2. **Valor sentinela** único por usuário (ex: `"AUSENTE_{user_id}"`)
3. **Campo separado** `cpf_verified` (BooleanField)

---

## 9. Referências

- **Comando audit_agenda_users**: `v2/backend/apps/dat_ingest/management/commands/audit_agenda_users.py`
- **Comando assign_cpf_from_excel**: `v2/backend/apps/dat_ingest/management/commands/assign_cpf_from_excel.py`
- **Admin CPF Filter**: `v2/backend/apps/core/admin.py` (classe `CPFFilter`)
- **Testes**: `v2/backend/apps/core/tests/test_assign_cpf_command.py`, `v2/backend/apps/dat_ingest/tests/test_audit_agenda_users.py`
- **Release Notes**: `docs/RELEASE_NOTES.md`
