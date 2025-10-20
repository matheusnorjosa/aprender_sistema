# Pre-commit Hooks - Sistema Aprender

## Instalação

```bash
# Instalar pre-commit
pip install pre-commit

# Instalar hooks no repositório
pre-commit install
```

## Uso

### Execução Automática
Os hooks executam automaticamente a cada commit. Se algum arquivo for modificado pelos hooks, o commit será cancelado e você precisará adicionar as mudanças novamente:

```bash
git add .
git commit -m "sua mensagem"  # Hooks executam automaticamente
```

### Execução Manual

```bash
# Executar em todos os arquivos
pre-commit run --all-files

# Executar em arquivos específicos
pre-commit run --files core/models.py core/views.py

# Executar hooks específicos
pre-commit run black
pre-commit run isort
```

## Hooks Configurados

### Formatação de Código
- **Black**: Formata código Python automaticamente
- **isort**: Organiza imports seguindo padrões

### Verificações de Arquivo
- **trailing-whitespace**: Remove espaços em branco no final das linhas
- **end-of-file-fixer**: Garante linha em branco no final dos arquivos
- **check-yaml/json/toml**: Valida sintaxe de arquivos de configuração
- **check-added-large-files**: Impede commit de arquivos muito grandes
- **check-merge-conflict**: Detecta marcadores de conflito de merge
- **detect-private-key**: Detecta chaves privadas acidentalmente commitadas
- **check-ast**: Valida sintaxe Python
- **debug-statements**: Detecta statements de debug esquecidos

## Configuração

O arquivo `.pre-commit-config.yaml` contém toda a configuração. Principais settings:

- **Linha máxima**: 88 caracteres (padrão Black)
- **Target Python**: 3.12
- **Exclusões**: migrations/, __pycache__/, venv/, etc.

## Resolução de Problemas

### Hook falhou - arquivos modificados
Isso é normal. Os hooks formataram seu código. Execute:
```bash
git add .
git commit -m "sua mensagem"
```

### Pular hooks temporariamente
```bash
git commit --no-verify -m "commit sem hooks"
```

### Atualizar versões dos hooks
```bash
pre-commit autoupdate
```

### Desinstalar hooks
```bash
pre-commit uninstall
```

## Padrões de Código Aplicados

- **Formatação Black**: Linha 88 chars, aspas duplas, trailing commas
- **Imports isort**: Agrupados e ordenados (stdlib, third-party, local)
- **Sem debug statements**: Evita pdb.set_trace(), print() de debug
- **Arquivos limpos**: Sem trailing spaces, com final de linha

## Integração CI/CD

Os mesmos hooks podem ser executados em CI:

```yaml
# GitHub Actions example
- name: Run pre-commit
  run: |
    pip install pre-commit
    pre-commit run --all-files
```