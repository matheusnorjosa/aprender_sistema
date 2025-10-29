# Variáveis de Ambiente - ETL

Este documento lista as variáveis de ambiente configuráveis para os comandos ETL do Aprender Sistema v2.

## Diretórios ETL

### ETL_OUTPUT_DIR
**Descrição**: Diretório de saída para relatórios gerados pelos comandos ETL (JSON, CSV).

**Default**: `{BASE_DIR}/out_etl` (ex: `/app/out_etl` no Docker)

**Exemplo**:
```bash
# Docker Compose
ETL_OUTPUT_DIR=/app/custom_reports

# Local development
ETL_OUTPUT_DIR=/tmp/etl_output
```

**Comandos afetados**:
- `audit_agenda_users`: gera `audit_users_*.json` e `audit_users_*.csv`
- `assign_cpf_from_excel`: gera `assign_cpf_report.json`
- Admin action `export_usuarios_sem_cpf`: gera `usuarios_sem_cpf.csv`

### ETL_DATA_DIR
**Descrição**: Diretório base para importação de arquivos CSV/XLSX.

**Default**: `{BASE_DIR}/data/csv-import` (ex: `/app/data/csv-import` no Docker)

**Exemplo**:
```bash
# Docker Compose
ETL_DATA_DIR=/app/data/imports

# Local development
ETL_DATA_DIR=/home/user/aprender/data
```

**Comandos afetados** (futuro):
- `import_acompanhamento`
- `import_deslocamento`
- `import_acoes_controle`
- `import_cadastros_dat`

---

## Uso em Docker Compose

Adicione as variáveis ao serviço `web` em `docker-compose.yml`:

```yaml
services:
  web:
    environment:
      - ETL_OUTPUT_DIR=/app/custom_reports
      - ETL_DATA_DIR=/app/data/custom_imports
```

Ou defina em `.env`:

```bash
# .env
ETL_OUTPUT_DIR=/app/custom_reports
ETL_DATA_DIR=/app/data/custom_imports
```

---

## Testes

Use `override_settings` para testar com diretórios customizados:

```python
from django.test import override_settings
from pathlib import Path

@override_settings(ETL_OUTPUT_DIR=str(tmp_path / "output"))
def test_command_output(tmp_path):
    """Testa comando com diretório customizado."""
    call_command('audit_agenda_users', ...)
    assert (tmp_path / "output" / "audit_users_crosscheck_report.json").exists()
```

---

## Histórico

- **PR #53** (2025-10-29): Adicionadas `ETL_OUTPUT_DIR` e `ETL_DATA_DIR` em `config/settings.py`
- Comandos migrados: `audit_agenda_users`, `assign_cpf_from_excel`, admin export
- Comandos pendentes: imports de acompanhamento/deslocamento/ações/cadastros

---

## Referências

- Issue #53: Configurar ETL_OUTPUT_DIR e ETL_DATA_DIR via settings
- `v2/backend/config/settings.py`: Definições das variáveis (linhas 410-412)
- `v2/docs/USERS_CPF_GUIDE.md`: Guia de uso dos comandos CPF
