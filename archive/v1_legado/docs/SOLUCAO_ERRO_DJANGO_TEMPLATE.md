# 🔧 SOLUÇÃO: ModuleNotFoundError: django.template

## 📋 Resumo do Problema

**Erro**: `ModuleNotFoundError: No module named 'django.template'`

**Causa Raiz**: Instalação corrompida do Django 5.2.4 (versão inexistente)

**Impacto**: Sistema completamente inoperante - nenhum comando Django funciona

---

## ✅ SOLUÇÃO RÁPIDA (Windows)

### Opção 1: Script Automático (RECOMENDADO)

```powershell
# Executar no PowerShell
cd "C:\Users\datsu\OneDrive\Documentos\Aprender Sistema"
.\fix_django_installation.ps1
```

### Opção 2: Manual

```powershell
# 1. Remover venv corrompido
cd "C:\Users\datsu\OneDrive\Documentos\Aprender Sistema"
Remove-Item .venv -Recurse -Force

# 2. Criar novo venv
python -m venv .venv

# 3. Ativar venv
.venv\Scripts\Activate.ps1

# 4. Atualizar pip
python -m pip install --upgrade pip

# 5. Instalar dependências corretas
pip install -r requirements.txt

# 6. Verificar instalação
python -c "import django; print(f'Django {django.__version__}'); import django.template; print('OK')"

# 7. Testar sistema
python manage.py check
```

---

## ✅ SOLUÇÃO RÁPIDA (Linux/Mac)

### Opção 1: Script Automático (RECOMENDADO)

```bash
# Executar no terminal
cd ~/caminho/para/aprender_sistema
chmod +x fix_django_installation.sh
./fix_django_installation.sh
```

### Opção 2: Manual

```bash
# 1. Remover venv corrompido
rm -rf .venv

# 2. Criar novo venv
python3 -m venv .venv

# 3. Ativar venv
source .venv/bin/activate

# 4. Atualizar pip
python -m pip install --upgrade pip

# 5. Instalar dependências corretas
pip install -r requirements.txt

# 6. Verificar instalação
python -c "import django; print(f'Django {django.__version__}'); import django.template; print('OK')"

# 7. Testar sistema
python manage.py check
```

---

## 🔍 DIAGNÓSTICO DETALHADO

### 1. Verificar Instalação Django

```python
# Testar import básico
python -c "import django; print(django.__version__)"
# Output esperado: 4.2.x (ou 5.0.x, 5.1.x)

# Testar django.template
python -c "import django.template; print('OK')"
# Output esperado: OK
```

### 2. Verificar Estrutura do Django

```python
# Listar módulos do Django
python -c "import django, os; print(os.listdir(os.path.dirname(django.__file__)))"
```

**Módulos esperados**:
```
['apps', 'conf', 'contrib', 'core', 'db', 'dispatch', 'forms', 'http',
 'middleware', 'shortcuts.py', 'template', 'templatetags', 'test',
 'urls', 'utils', 'views', ...]
```

**⚠️ Se `template` NÃO estiver na lista → Instalação corrompida!**

### 3. Verificar PYTHONPATH

```python
python -c "import sys; print('\n'.join(sys.path))"
```

Deve incluir:
```
C:\...\Aprender Sistema\.venv\Lib\site-packages
```

---

## 🔧 PROBLEMA NO `requirements.txt` (CORRIGIDO)

### Antes (INCORRETO):
```
Django==5.2.4  # ❌ Esta versão NÃO EXISTE!
```

### Depois (CORRETO):
```
Django>=4.2.0,<5.0.0  # ✅ Django 4.2 LTS (suporte até 2026)
```

### Versões Django Válidas:

| Versão | Status | Suporte até |
|--------|--------|-------------|
| Django 4.2.x | **LTS (Recomendado)** | Abril 2026 |
| Django 5.0.x | Estável | Abril 2025 |
| Django 5.1.x | Mais recente | Dezembro 2025 |

**Nota**: Django 5.2.4 **não existe** oficialmente!

---

## ⚙️ CONFIGURAÇÃO CORRIGIDA

### `requirements.txt` Atualizado

```txt
# Core Django dependencies
Django>=4.2.0,<5.0.0  # Django 4.2 LTS
asgiref>=3.7.0
psycopg2-binary>=2.9.0
sqlparse>=0.4.0
tzdata>=2024.1

# Django extensions
django-extensions>=3.2.0

# Django REST Framework
djangorestframework>=3.14.0
django-filter>=23.0
django-cors-headers>=4.0.0

# Google APIs integration
google-api-python-client>=2.100.0
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
gspread>=6.0.0

# Data migration
django-import-export>=4.0.0
pandas>=2.1.0
openpyxl>=3.1.0

# Async processing
celery>=5.3.0
redis>=4.5.0
django-celery-beat>=2.5.0

# Production server
gunicorn>=21.0.0
whitenoise>=6.5.0

# Utilities
python-decouple>=3.8
Pillow>=10.0.0
```

### `settings.py` Simplificado

```python
"""
Django settings for aprender_sistema project - VERSÃO SIMPLIFICADA
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'dev-insecure-key-only-for-local-development'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Local apps
    'core',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aprender_sistema.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

---

## 🧪 VALIDAÇÃO PÓS-CORREÇÃO

### Checklist de Verificação

```bash
# 1. Django instalado corretamente
python -c "import django; print(f'✅ Django {django.__version__}')"

# 2. django.template funciona
python -c "import django.template; print('✅ django.template OK')"

# 3. django.core.management funciona
python -c "from django.core.management import execute_from_command_line; print('✅ management OK')"

# 4. Django check passa
python manage.py check
# Output esperado: System check identified no issues (0 silenced).

# 5. Migrations funcionam
python manage.py migrate

# 6. Servidor inicia
python manage.py runserver
# Deve iniciar sem erros
```

### Output Esperado

```
✅ Django 4.2.x
✅ django.template OK
✅ management OK
System check identified no issues (0 silenced).
```

---

## 🚀 PRÓXIMOS PASSOS

Após correção bem-sucedida:

### 1. Aplicar Migrations

```bash
python manage.py migrate
```

### 2. Criar Superuser

```bash
python manage.py createsuperuser
```

Dados sugeridos:
- CPF: 12345678901 (11 dígitos)
- Email: admin@aprender.com
- Senha: (sua senha segura)

### 3. Rodar Servidor

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

### 4. Verificar Admin

http://localhost:8000/admin

---

## 🐛 TROUBLESHOOTING

### Erro: "Permission denied" ao executar script

**Windows**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Linux/Mac**:
```bash
chmod +x fix_django_installation.sh
```

### Erro: "python not found"

Tente:
- Windows: `py` ao invés de `python`
- Linux/Mac: `python3` ao invés de `python`

### Erro: "pip not found"

```bash
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

### Venv não ativa

**Windows**:
```powershell
.venv\Scripts\Activate.ps1
```

**Linux/Mac**:
```bash
source .venv/bin/activate
```

---

## 📞 SUPORTE

Se o problema persistir:

1. **Verificar Python**: `python --version` (deve ser 3.11+)
2. **Limpar cache pip**: `pip cache purge`
3. **Reinstalar Python**: Baixar de python.org
4. **Verificar variáveis de ambiente**: PATH deve incluir Python

---

## 📚 REFERÊNCIAS

- [Django Documentation](https://docs.djangoproject.com/en/4.2/)
- [Django Releases](https://www.djangoproject.com/download/)
- [Python Virtual Environments](https://docs.python.org/3/library/venv.html)

---

**Última atualização**: 2025-09-30
**Status**: ✅ Problema resolvido com correção do requirements.txt
