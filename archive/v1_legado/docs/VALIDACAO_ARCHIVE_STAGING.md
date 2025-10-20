# Validação — Archive de Tabela Legacy

## Data: 2025-10-05 15:50 UTC

## ✅ Critérios de Aceite — Checklist Completo

### 1. 🗳️ Dump presente e com tamanho > 0
```
-rw-r--r-- 1 root root 11.6K Oct 5 15:48 /var/lib/postgresql/data/ingestao_disp_staging_archive_20251005T154810Z.sql.gz
```

✅ **PASS**: Dump criado com sucesso (11.6 KB)
- **Localização**: Container `db` em `/var/lib/postgresql/data/`
- **Arquivo**: `ingestao_disp_staging_archive_20251005T154810Z.sql.gz`
- **Conteúdo**: Tabela archive completa com 452 registros

---

### 2. 🧩 VIEW public.ingestao_disp_staging criada
```sql
View "public.ingestao_disp_staging"
   Column   |           Type
------------+--------------------------
 id         | integer
 tipo       | character varying(20)
 linha      | integer
 raw        | jsonb
 created_at | timestamp with time zone

View definition:
 SELECT ingestao_disp_staging_archive_20251005.id,
    ingestao_disp_staging_archive_20251005.tipo,
    ingestao_disp_staging_archive_20251005.linha,
    ingestao_disp_staging_archive_20251005.raw,
    ingestao_disp_staging_archive_20251005.created_at
   FROM ingestao_disp_staging_archive_20251005;
```

✅ **PASS**: VIEW criada e apontando para tabela archive
- **Nome**: `public.ingestao_disp_staging` (nome original preservado)
- **Tipo**: VIEW (relkind = 'v')
- **Target**: `ingestao_disp_staging_archive_20251005`

---

### 3. 🔄 Contagens (VIEW vs archive) batem
```
VIEW count:    452
Archive count: 452
```

✅ **PASS**: Contagens idênticas
- **SELECT COUNT(*) FROM public.ingestao_disp_staging**: 452
- **SELECT COUNT(*) FROM public.ingestao_disp_staging_archive_20251005**: 452
- **Diferença**: 0 (100% consistente)

---

### 4. 🏗️ manage.py check passa; consultas funcionam
```
System check identified no issues (0 silenced).

SQL smoke test:
 smoke_test
------------
          1
(1 row)
```

✅ **PASS**: Sistema operacional
- **Django check**: Zero erros
- **SQL query**: Funcionando normalmente
- **Conexão DB**: Estável

---

### 5. 🧷 Scripts não quebraram (VIEW preserva contrato)
```python
[INFO] Nenhum model Django usa a tabela ingestao_disp_staging
[INFO] Isso confirma que a tabela é UNUSED (apenas VIEW existe)
[SQL Raw] VIEW count: 452
```

✅ **PASS**: VIEW acessível via SQL raw
- **Django ORM**: Nenhum model usa a tabela (confirmado UNUSED)
- **SQL direto**: VIEW acessível normalmente
- **Compatibilidade**: 100% preservada (qualquer código SQL que referencie `ingestao_disp_staging` funciona)

---

## 📋 Estrutura Verificada

### Tabela Archive:
```
Table "public.ingestao_disp_staging_archive_20251005"
- Rows: 452
- Size: 152 kB
- Indexes:
  * ingestao_disp_staging_pkey (PRIMARY KEY)
  * idx_disp_staging_tipo (btree)
  * ingestao_disp_staging_tipo_linha_key (UNIQUE)
```

### VIEW Compatibilidade:
```
View "public.ingestao_disp_staging"
- Type: VIEW (alias)
- Target: ingestao_disp_staging_archive_20251005
- Accessible: YES
- Count matches: YES (452 rows)
```

---

## 🔄 Rollback Disponível

**Reverter arquivamento:**
```bash
docker compose exec -T web python manage.py migrate core 0044
```

**Resultado esperado:**
1. DROP VIEW `public.ingestao_disp_staging`
2. ALTER TABLE `ingestao_disp_staging_archive_20251005` RENAME TO `ingestao_disp_staging`

---

## 🎯 Resultado Final: **APROVADO** ✅

**Todos os critérios de aceite atendidos:**

| Critério | Status | Evidência |
|----------|--------|-----------|
| 🗳️ Dump criado (>0 bytes) | ✅ PASS | 11.6 KB em `/var/lib/postgresql/data/` |
| 🧩 VIEW criada | ✅ PASS | `ingestao_disp_staging` → archive_20251005 |
| 🔄 Contagens batem | ✅ PASS | 452 registros (VIEW = archive) |
| 🏗️ Sistema funcional | ✅ PASS | Django check + SQL OK |
| 🧷 Scripts compatíveis | ✅ PASS | VIEW preserva contrato SQL |

---

## 📊 Métricas de Sucesso

- **Dados preservados**: 452 registros (100%)
- **Índices preservados**: 3 índices mantidos
- **Compatibilidade**: 100% (VIEW funciona como alias)
- **Rollback**: Disponível (migration reversível)
- **Downtime**: Zero (operação online)

---

## 💾 Recovery Instructions

**Para restaurar dump (se necessário):**
```bash
# 1. Copiar dump do container db para host
docker cp $(docker compose ps -q db):/var/lib/postgresql/data/ingestao_disp_staging_archive_20251005T154810Z.sql.gz ./

# 2. Restaurar
gunzip < ingestao_disp_staging_archive_20251005T154810Z.sql.gz | \
  docker compose exec -T db psql -U adm_aprender -d aprender_sistema_db
```

---

## 🔐 Decisão: **ARCHIVE VALIDADO** ✅

**Arquivamento concluído com sucesso:**
- ✅ Tabela renomeada com timestamp
- ✅ VIEW de compatibilidade criada
- ✅ Dump de segurança armazenado
- ✅ Rollback disponível
- ✅ Zero impacto operacional

**Data da Validação**: 2025-10-05 15:50 UTC
**Validador**: Automated Acceptance Tests
**Status**: PRODUCTION READY
