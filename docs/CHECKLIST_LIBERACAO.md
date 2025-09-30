# 📋 Checklist de Liberação - Aprender Sistema

## ✅ PASSO 1: Git Limpo & Branch Dedicada

```bash
# Verificar status limpo
git status

# Criar branch dedicada para os commits
git checkout -b feat/execucao-mini-commits

# Validar branch atual
git branch --show-current
```

**Critério**: `git status` deve mostrar working tree clean.

---

## 🐳 PASSO 2: Ambiente de Teste/Staging Ativo

```bash
# Subir containers
docker compose up -d

# Verificar logs sem erros críticos
docker compose logs --tail=50

# Testar acesso à aplicação
curl -I http://localhost:8000/
```

**Critério**: Docker sobe sem erros, aplicação responde HTTP 200.

---

## 🗄️ PASSO 3: Banco de Staging Separado

```bash
# Criar backup do banco atual
cp db.sqlite3 db_backup_$(date +%Y%m%d_%H%M%S).sqlite3

# Ou para PostgreSQL:
# pg_dump aprender_sistema > backup_$(date +%Y%m%d_%H%M%S).sql

# Testar migrações em ambiente limpo
python manage.py migrate --check
```

**Critério**: Backup criado, migrações aplicáveis sem conflitos.

---

## 🔐 PASSO 4: Segredos Fora do Código

### Criar .env de exemplo:
```bash
# Criar .env.example (template público)
cat > .env.example << 'EOF'
# Ambiente (development|staging|production)
ENVIRONMENT=production

# Segurança (OBRIGATÓRIO EM PRODUÇÃO)
SECRET_KEY=your-secret-key-here-minimum-50-characters-required
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Banco de dados
DB_NAME=aprender_sistema
DB_USER=aprender_user
DB_PASSWORD=your-secure-password-here
DB_HOST=localhost
DB_PORT=5432

# Email (opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Google Calendar (opcional)
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/credentials.json
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com

# Redis (opcional)
REDIS_URL=redis://localhost:6379/1

# CSRF
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
EOF
```

### Validar variáveis:
```bash
# Gerar SECRET_KEY segura
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"

# Verificar .env não está no git
grep -r "SECRET_KEY.*=" . --exclude-dir=.git || echo "✅ Segredos não encontrados no código"
```

**Critério**: `.env.example` criado, segredos não commitados.

---

## 🧪 PASSO 5: Dados de Teste Criados

```bash
# Aplicar migrações
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser

# Carregar dados básicos
python manage.py shell << 'EOF'
from django.contrib.auth.models import Group
from core.models import Usuario, Municipio, Projeto, TipoEvento, Formador

# Criar grupos
groups = ['coordenador', 'superintendencia', 'controle', 'formador']
for group_name in groups:
    Group.objects.get_or_create(name=group_name)

# Criar dados mínimos para teste
Municipio.objects.get_or_create(nome="Fortaleza", defaults={"uf": "CE"})
Projeto.objects.get_or_create(nome="Projeto Teste", defaults={"descricao": "Projeto para testes"})
TipoEvento.objects.get_or_create(nome="Formação Online", defaults={"duracao": 4, "online": True})
TipoEvento.objects.get_or_create(nome="Formação Presencial", defaults={"duracao": 8, "online": False})

print("✅ Dados de teste criados")
EOF
```

**Critério**: Usuários por grupo, 1+ município, projeto, formador, tipos de evento.

---

## 🔄 PASSO 6: Backups & Migrações

```bash
# Criar snapshot do banco staging
python manage.py dumpdata --indent=2 > staging_snapshot_$(date +%Y%m%d).json

# Testar rollback de migração (se necessário)
python manage.py showmigrations core

# Validar que pode aplicar migrações
python manage.py migrate --check
```

**Critério**: Snapshot criado, migrações reversíveis.

---

## 🎯 PASSO 7: Validação Final

### Ambiente Development:
```bash
python manage.py check
python manage.py test core.tests -v 2
```

### Ambiente Production (simulado):
```bash
ENVIRONMENT=production \
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))") \
ALLOWED_HOSTS=localhost,127.0.0.1 \
DB_PASSWORD=test \
python manage.py check --deploy --settings=aprender_sistema.settings_production
```

**Critério**: 
- ✅ `check` sem warnings críticos
- ✅ `check --deploy` para produção OK
- ✅ Testes passando
- ✅ Sistema inicia sem erros

---

## 🚀 PASSO 8: Fluxo E2E Mínimo

```bash
# Testar fluxo básico
python manage.py runserver 8000
```

**Validar manualmente**:
1. Login funciona (`/login/`)
2. Home carrega (`/`)
3. Menu lateral visível
4. Páginas principais acessíveis

**Critério**: Interface carrega, login funciona, navegação OK.

---

## 🏆 CRITÉRIOS DE APROVAÇÃO FINAL

- [ ] Git status limpo
- [ ] Branch `feat/execucao-mini-commits` criada
- [ ] Docker compose sobe sem erros
- [ ] Dados de teste carregados
- [ ] Backup de staging criado
- [ ] `python manage.py check --deploy` OK
- [ ] Argon2 configurado corretamente
- [ ] Segredos não estão no código
- [ ] Fluxo E2E básico funcional

**🎯 Meta**: Sistema pronto para receber os commits atômicos planejados com segurança total.

---

## 📝 Comandos Úteis Pós-Liberação

```bash
# Validar configuração de produção
python manage.py check --deploy --settings=aprender_sistema.settings_production

# Testar hash Argon2
python manage.py shell -c "from django.contrib.auth.hashers import make_password; print(make_password('test123'))"

# Verificar logs de segurança
tail -f logs/security.log

# Monitor de saúde
docker compose ps
```