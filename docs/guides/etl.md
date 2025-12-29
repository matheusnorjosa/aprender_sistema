# ETL e Importação de Dados

Guia para importação de dados das planilhas originais.

## Visão Geral

O sistema possui 21 comandos ETL para importação de dados:

```bash
# Listar comandos disponíveis
docker compose exec web python manage.py --help | grep import
```

## Comandos Principais

### Usuários

```bash
python manage.py import_usuarios --dry-run
python manage.py import_usuarios --apply
```

### Formadores

```bash
python manage.py import_formadores --dry-run
python manage.py import_formadores --apply
```

### Municípios

```bash
python manage.py import_municipios --dry-run
python manage.py import_municipios --apply
```

### Projetos

```bash
python manage.py import_projetos --dry-run
python manage.py import_projetos --apply
```

### Solicitações

```bash
python manage.py import_solicitacoes --dry-run
python manage.py import_solicitacoes --apply
```

## Princípios ETL

### 1. Idempotência

- Comandos podem ser executados múltiplas vezes
- Usa `update_or_create` para evitar duplicatas
- Chave única: campos de identificação natural

### 2. Dry-Run Obrigatório

```bash
# SEMPRE rodar dry-run primeiro
python manage.py import_dados --dry-run

# Verificar output, depois aplicar
python manage.py import_dados --apply
```

### 3. Quality Gates

- Validação de campos obrigatórios
- Normalização de dados (trim, lowercase)
- Tratamento de valores nulos

### 4. Relatórios

Cada comando gera relatório JSON:

```json
{
  "command": "import_usuarios",
  "mode": "apply",
  "started_at": "2025-01-15T10:00:00Z",
  "finished_at": "2025-01-15T10:01:00Z",
  "stats": {
    "total_rows": 150,
    "created": 145,
    "updated": 5,
    "skipped": 0,
    "errors": 0
  },
  "errors": []
}
```

## Estrutura de Arquivos

```
v2/backend/data/csv-import/
├── Acompanhamento de Agenda _ 2025.xlsx
├── Disponibilidade _ 2025.xlsx
├── Planilha de Controle - 2025.xlsx
└── Usuários.xlsx
```

## Fluxo Recomendado

1. **Municípios** (sem dependências)
2. **Projetos** (sem dependências)
3. **Usuários** (requer grupos)
4. **Formadores** (requer usuários)
5. **Solicitações** (requer formadores, projetos, municípios)
6. **Bloqueios** (requer formadores)

## Troubleshooting

### Erro de Encoding

```bash
# Converter arquivo para UTF-8
iconv -f ISO-8859-1 -t UTF-8 arquivo.csv > arquivo_utf8.csv
```

### Erro de Formato de Data

O sistema espera datas no formato ISO 8601 ou DD/MM/YYYY:

```python
# Formatos aceitos
"2025-01-15"
"2025-01-15T10:00:00"
"15/01/2025"
```

### Linhas Ignoradas

Verifique o relatório JSON para detalhes:

```bash
cat import_report_*.json | jq '.errors'
```
