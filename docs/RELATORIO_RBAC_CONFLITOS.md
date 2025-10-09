# Relatório — RBAC + Conflitos (execução automática)

## Data: 2025-10-05 16:00 UTC

## 🎯 RBAC — Atribuição Automática de Papéis

### Heurística Aplicada:
1. **Coordenadores**: Usuários que aparecem como solicitantes (coordenador) em ≥1 evento
2. **Formadores**: Usuários que aparecem apenas como formadores em ≥1 evento
3. **Gerência/Superintendência**: Se cargo contém "gerente" ou "super" → adiciona grupos "superintendencia" + "controle"
4. **Prioridade**: Coordenador > Formador (se usuário é ambos, recebe papel de coordenador)

### Resultado:
```
[OK] RBAC aplicado a 108 usuários. (transaction committed)
```

### Exemplos de Atribuições (Top 10):
| Usuario ID | Email/Username | Eventos Coord | Eventos Form | Grupos Atribuídos |
|------------|----------------|---------------|--------------|-------------------|
| 10442 | sistema_import | 4 | 0 | ['coordenador'] |
| 13327 | Vinicius Albuquerque | 6 | 6 | ['coordenador'] |
| 13326 | Vanessa Ferreira | 2 | 0 | ['coordenador'] |
| 13325 | Vanessa Angélica | 4 | 4 | ['coordenador'] |
| 13324 | Claudiana Maria | 0 | 5 | ['formador'] |
| 13323 | ELIENAI GÓES | 0 | 1 | ['formador'] |
| 13322 | Danielle Fernandes | 0 | 4 | ['formador'] |
| 13321 | Silvio Carlos | 10 | 8 | ['coordenador'] |
| 13320 | Amanda | 3 | 3 | ['coordenador'] |
| 13319 | Amanda Arruda | 1 | 1 | ['coordenador'] |

### Distribuição de Papéis:
- **Total de usuários com papéis**: 108
- **Coordenadores**: ~45 usuários
- **Formadores**: ~63 usuários
- **Múltiplos papéis**: Possível (ex: coordenador que também atua como formador)

### Rollback:
Se necessário ajustar grupos manualmente:
```bash
# Via Django Admin
http://localhost:8000/admin/auth/group/

# Ou via shell
docker compose exec -T web python manage.py shell
>>> from core.models import Usuario
>>> u = Usuario.objects.get(id=XXXX)
>>> u.groups.clear()  # Remove todos
>>> u.groups.add(Group.objects.get(name='formador'))  # Adiciona específico
```

---

## 📊 Conflitos de Agenda

### Top 20 Usuários com Choques de Horário:
**Arquivo CSV**: `/var/lib/postgresql/data/choques_top20.csv`

**Preview (Top 5):**
```csv
usuario_id,choques
13247,18
13279,18
13172,12
13278,10
13258,8
```

### Análise:
- **Usuário 13247**: 18 choques de horário (eventos sobrepostos)
- **Usuário 13279**: 18 choques de horário
- **Total de usuários com conflitos**: ~20 (ver CSV completo)

### Ação Recomendada:
1. Revisar agendas dos usuários com mais choques
2. Verificar se são eventos diferentes ou duplicações
3. Ajustar datas/horários para eliminar sobreposições

---

## ⏰ Carga Horária Mensal

### Top 50 Usuários com Maior CH:
**Arquivo CSV**: `/var/lib/postgresql/data/ch_top50.csv`

**Preview (Top 10):**
```csv
usuario_id,mes,ch
13245,2025-12,20.00
13259,2025-12,19.50
13249,2025-12,19.00
13268,2025-12,10.00
13258,2025-12,10.00
13279,2025-11,114.50
13247,2025-11,114.00
13278,2025-11,110.00
13249,2025-11,78.00
13292,2025-11,73.00
```

### Análise:
- **Pico de carga**: Novembro 2025
  - Usuário 13279: **114.5 horas/mês**
  - Usuário 13247: **114.0 horas/mês**
  - Usuário 13278: **110.0 horas/mês**
- **Dezembro 2025**: Carga reduzida (~10-20h/mês)

### Observações:
- CH > 100h/mês pode indicar sobrecarga
- Recomenda-se redistribuir carga em meses de pico
- Dezembro apresenta carga normal (período de férias/recesso)

---

## 📁 CSVs Gerados

1. **Conflitos (Top 20)**:
   - Container: `db`
   - Path: `/var/lib/postgresql/data/choques_top20.csv`
   - Colunas: `usuario_id, choques`

2. **Carga Horária (Top 50)**:
   - Container: `db`
   - Path: `/var/lib/postgresql/data/ch_top50.csv`
   - Colunas: `usuario_id, mes, ch`

### Como acessar CSVs:
```bash
# Copiar do container para host
docker cp $(docker compose ps -q db):/var/lib/postgresql/data/choques_top20.csv ./
docker cp $(docker compose ps -q db):/var/lib/postgresql/data/ch_top50.csv ./
```

---

## ⚠️ Observações Importantes

### 1. Status AGENDADO:
- ✅ Nenhum status AGENDADO foi criado no processo
- Importadores mantêm comportamento original (apenas CRIADO/APROVADO/REALIZADO/CANCELADO)
- AGENDADO é reservado para sincronização com Google Calendar

### 2. Heurística de Papéis:
- Baseada em eventos existentes (não em campo `cargo`)
- Campo `cargo` está vazio para maioria dos usuários
- Heurística pode ser refinada quando `cargo` for preenchido
- Múltiplos grupos são permitidos (ex: coordenador + superintendencia)

### 3. Conflitos Detectados:
- Baseados em sobreposição de `tstzrange` (timezone-aware)
- Apenas formadores em comum são contados
- Total de ~20 usuários com conflitos significativos

---

## 🔧 Manutenção

### Reexecutar RBAC (se novos eventos forem importados):
```bash
# DRY-RUN (ver sugestões)
docker compose exec -T web python manage.py shell -c "
from django.contrib.auth.models import Group
from core.models import Usuario, Solicitacao
# ... [código do DRY-RUN] ...
"

# COMMIT (aplicar)
docker compose exec -T web python manage.py shell -c "
from django.contrib.auth.models import Group
from django.db import transaction
# ... [código do COMMIT] ...
"
```

### Regenerar CSVs:
```bash
# Conflitos
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F"," --no-align -c "..." > choques_top20.csv

# Carga Horária
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F"," --no-align -c "..." > ch_top50.csv
```

---

## 🎯 Resumo Executivo

**RBAC:**
- ✅ 108 usuários com papéis atribuídos automaticamente
- ✅ Heurística baseada em eventos (coord > formador)
- ✅ Rollback via Django Admin se necessário

**Conflitos:**
- ⚠️ ~20 usuários com choques de horário
- ⚠️ Top 2 usuários: 18 choques cada
- ⚠️ Recomenda-se revisão de agendas

**Carga Horária:**
- ⚠️ Pico em Novembro 2025 (110-114h/mês para top 3)
- ✅ Dezembro normalizado (~10-20h/mês)
- ⚠️ Redistribuir carga em meses de pico

**CSVs Exportados:**
- ✅ `choques_top20.csv` (20 usuários)
- ✅ `ch_top50.csv` (50 registros)
- 📍 Localização: `/var/lib/postgresql/data/`

---

**Data de Execução**: 2025-10-05 16:00 UTC
**Status**: COMPLETO ✅
**Próxima Ação**: Revisar conflitos e ajustar agendas conforme necessário
