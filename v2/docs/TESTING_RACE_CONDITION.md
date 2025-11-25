# Test Database Race Condition - test_config_api.py

## Problema

Quando múltiplas execuções de `pytest` rodam simultaneamente, ocorre erro de race condition:

```
django.db.utils.IntegrityError: duplicate key value violates unique constraint "pg_database_datname_index"
DETAIL: Key (datname)=(test_aprender_db) already exists.
```

## Causa Raiz

1. Dois processos pytest iniciam ao mesmo tempo
2. Ambos tentam criar banco de teste `test_aprender_db`
3. Primeiro cria com sucesso
4. Segundo falha com erro de unique constraint

## Reprodução

```bash
# Terminal 1
pytest apps/core/tests/test_config_api.py -vv &

# Terminal 2 (imediatamente após)
pytest apps/core/tests/test_config_api.py -vv
```

**Resultado**: Segundo pytest falha com IntegrityError.

## Soluções

### Solução 1: Executar Apenas UMA vez por sessão (Recomendado)

```bash
# ✅ Correto - execução única
pytest apps/core

# ❌ Errado - múltiplas execuções simultâneas
pytest apps/core/tests/test_config_api.py &
pytest apps/core/tests/test_admin_api.py
```

### Solução 2: Usar --reuse-db

Reutiliza banco de teste entre execuções, evitando recriação:

```bash
pytest apps/core/tests/test_config_api.py --reuse-db
```

**Vantagens**:
- Evita race condition
- Testes mais rápidos (não recria DB)

**Desvantagens**:
- Estado pode vazar entre execuções
- Precisa limpar manualmente: `pytest --create-db`

### Solução 3: Usar pytest-xdist com --dist=loadfile

Distribui testes por arquivo, não por teste individual:

```bash
pytest apps/core -n auto --dist=loadfile
```

**Nota**: Projeto já usa pytest-xdist (instalado), mas pode precisar de ajuste no pytest.ini.

### Solução 4: Nomes Únicos de DB por Worker

Adicionar em `pytest.ini`:

```ini
[pytest]
django_db_use_migrations = true
django_db_serialization = false

# Gera DB único por worker xdist
django_db_suffix = _{worker_id}
```

## Configuração Atual

**pytest.ini**:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
addopts = --strict-markers --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
```

**Recomendação**: Adicionar `--reuse-db` ao CI para evitar race conditions.

## Status

- **Ambiente Local**: Race condition reproduzível ✅
- **CI**: Não afetado (execuções sequenciais)
- **Impacto**: Baixo (apenas quando múltiplas execuções simultâneas)

## Commits de Referência

- Auditoria inicial: df60e67 (#203)
- Reprodução do erro: 2025-11-25

## Conclusão

**Workaround**: Evitar múltiplas execuções simultâneas de pytest.

**Fix Permanente**: Adicionar ao `pytest.ini`:
```ini
addopts = --strict-markers --tb=short --reuse-db
```

Ou documentar no README que pytest deve ser executado apenas uma vez por sessão.
