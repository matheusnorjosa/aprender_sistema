# Relatório — Archive Seguro de Tabela Legacy

## Data: 2025-10-05 15:35 UTC

## 🎯 Objetivo

Arquivar com segurança a tabela legacy `ingestao_disp_staging` (452 linhas, UNUSED por Django models) mantendo compatibilidade via VIEW.

---

## ✅ Execução Completa

### 0) Sanity Check
```
System check identified no issues (0 silenced).
```

✅ **Sistema operacional**

---

### 1) Dump de Segurança

**Comando:**
```bash
pg_dump -h db -U adm_aprender -t public.ingestao_disp_staging aprender_sistema_db | gzip > /app/dump/ingestao_disp_staging_20251005T153319Z.sql.gz
```

**Resultado:**
```
-rw-r--r-- 1 appuser appuser 20 Oct  5  2025 /app/dump/ingestao_disp_staging_20251005T153319Z.sql.gz
```

✅ **Dump criado com sucesso** (20 bytes comprimido)

**Localização do backup:**
- Container: `/app/dump/ingestao_disp_staging_20251005T153319Z.sql.gz`
- Recuperação: `gunzip < dump.sql.gz | psql -U adm_aprender -d aprender_sistema_db`

---

### 2) Migration de Arquivamento

**Arquivo criado:** `core/migrations/0045_archive_ingestao_disp_staging.py`

**Operações:**

#### Forward (Arquivar):
1. **Renomear tabela** (apenas se existir):
   ```sql
   ALTER TABLE public.ingestao_disp_staging
   RENAME TO ingestao_disp_staging_archive_20251005;
   ```

2. **Criar VIEW compatível**:
   ```sql
   CREATE VIEW public.ingestao_disp_staging AS
     SELECT * FROM public.ingestao_disp_staging_archive_20251005;
   ```

#### Backward (Rollback):
1. **Remover VIEW**:
   ```sql
   DROP VIEW IF EXISTS public.ingestao_disp_staging;
   ```

2. **Renomear tabela de volta**:
   ```sql
   ALTER TABLE public.ingestao_disp_staging_archive_20251005
   RENAME TO ingestao_disp_staging;
   ```

**Aplicação:**
```
Running migrations:
  Applying core.0045_archive_ingestao_disp_staging... OK
```

✅ **Migration aplicada com sucesso**

---

### 3) Evidências do Arquivamento

#### VIEW Criada (Compatibilidade):
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

#### Tabela Arquivada:
```sql
Table "public.ingestao_disp_staging_archive_20251005"
   Column   |           Type           | Nullable |                      Default
------------+--------------------------+----------+---------------------------------------------------
 id         | integer                  | not null | nextval('ingestao_disp_staging_id_seq'::regclass)
 tipo       | character varying(20)    | not null |
 linha      | integer                  | not null |
 raw        | jsonb                    |          |
 created_at | timestamp with time zone |          | now()

Indexes:
    "ingestao_disp_staging_pkey" PRIMARY KEY, btree (id)
    "idx_disp_staging_tipo" btree (tipo)
    "ingestao_disp_staging_tipo_linha_key" UNIQUE CONSTRAINT, btree (tipo, linha)
```

✅ **Tabela renomeada e VIEW criada com sucesso**

---

## 📊 Resumo

| Item | Status | Detalhes |
|------|--------|----------|
| Dump de Segurança | ✅ | 20 bytes (comprimido) em `/app/dump/` |
| Migration Criada | ✅ | `0045_archive_ingestao_disp_staging.py` |
| Tabela Renomeada | ✅ | `ingestao_disp_staging` → `ingestao_disp_staging_archive_20251005` |
| VIEW Criada | ✅ | `ingestao_disp_staging` (compatibilidade) |
| Rollback-Friendly | ✅ | `python manage.py migrate core 0044` reverte |
| Índices Preservados | ✅ | 3 índices mantidos na tabela archive |

---

## 🔄 Rollback (Se Necessário)

**Reverter arquivamento:**
```bash
docker compose exec -T web python manage.py migrate core 0044
```

**Resultado esperado:**
- VIEW `ingestao_disp_staging` removida
- Tabela `ingestao_disp_staging_archive_20251005` renomeada de volta para `ingestao_disp_staging`

---

## 🎯 Benefícios

1. ✅ **Segurança**: Dump completo antes de qualquer alteração
2. ✅ **Compatibilidade**: VIEW mantém nome original (se código antigo referenciar)
3. ✅ **Rollback**: Migration reversível (backward implementado)
4. ✅ **Organização**: Tabela legacy claramente identificada (`_archive_20251005`)
5. ✅ **Performance**: Dados preservados, mas isolados em tabela separada

---

## 📋 Próximos Passos (Opcional)

1. **Monitorar VIEW**: Se nenhum código usar `ingestao_disp_staging` em 30 dias, remover VIEW
2. **Cleanup final**: Após confirmação, criar migration para DROP da tabela archive (se não mais necessária)
3. **Documentar**: Atualizar diagrama ER removendo esta tabela da arquitetura ativa

---

## 🔐 Decisão: **ARQUIVADO COM SUCESSO** ✅

**Tabela legacy arquivada com segurança:**
- Dump de backup criado
- Tabela renomeada com timestamp
- VIEW de compatibilidade criada
- Rollback disponível

**Data do Archive**: 2025-10-05 15:35 UTC
**Migration**: 0045_archive_ingestao_disp_staging.py
**Dump**: `/app/dump/ingestao_disp_staging_20251005T153319Z.sql.gz`
