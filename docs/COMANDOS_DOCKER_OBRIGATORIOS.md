# 🐳 **COMANDOS DOCKER OBRIGATÓRIOS - Sistema Aprender**

## ⚠️ **POLÍTICA DE DOCKERIZAÇÃO TOTAL**

**REGRA OBRIGATÓRIA**: TODO desenvolvimento, teste, manutenção e operação do Sistema Aprender deve ser executado **EXCLUSIVAMENTE NO DOCKER**.

### 🚫 **PROIBIDO:**
- ❌ `python manage.py` (ambiente local)
- ❌ `venv/Scripts/python manage.py` (ambiente local)  
- ❌ Qualquer comando Django fora do container
- ❌ Acesso direto ao SQLite local
- ❌ Pip install fora do container

### ✅ **OBRIGATÓRIO:**
- ✅ `docker exec aprender_web python manage.py` (dentro do container)
- ✅ `docker-compose` para gestão de serviços
- ✅ PostgreSQL como banco único

---

## 📋 **COMANDOS ESSENCIAIS**

### **🚀 Inicialização**
```bash
# Iniciar ambiente completo
docker-compose up -d

# Verificar status dos containers
docker ps

# Ver logs em tempo real
docker-compose logs -f web
```

### **🔧 Django Management**
```bash
# Migrations
docker exec aprender_web python manage.py makemigrations
docker exec aprender_web python manage.py migrate

# Superuser
docker exec -it aprender_web python manage.py createsuperuser

# Shell Django
docker exec -it aprender_web python manage.py shell

# Testes
docker exec aprender_web python manage.py test

# Check sistema
docker exec aprender_web python manage.py check

# Health check
docker exec aprender_web python manage.py health_check
```

### **📊 População de Dados**
```bash
# Popular dados das planilhas
docker exec aprender_web python manage.py populate_from_extracted_data

# Criar dados de exemplo
docker exec aprender_web python manage.py create_sample_data

# Verificar dados populados
docker exec aprender_web python manage.py shell -c "from core.models import Usuario; print(f'Usuários: {Usuario.objects.count()}')"
```

### **🗄️ Banco de Dados**
```bash
# Acesso ao PostgreSQL
docker exec -it aprender_db psql -U adm_aprender -d aprender_sistema_db

# Backup do banco
docker exec aprender_db pg_dump -U adm_aprender -d aprender_sistema_db > backup.sql

# Restore do banco  
docker exec -i aprender_db psql -U adm_aprender -d aprender_sistema_db < backup.sql

# Verificar conexão
docker exec aprender_db pg_isready -U adm_aprender -d aprender_sistema_db
```

### **📁 Arquivos e Logs**
```bash
# Acessar container
docker exec -it aprender_web sh

# Ver estrutura de arquivos
docker exec aprender_web ls -la /app/

# Ver logs específicos
docker exec aprender_web tail -f /app/logs/django.log

# Copiar arquivos
docker cp arquivo.txt aprender_web:/app/
docker cp aprender_web:/app/arquivo.txt .
```

---

## 🎯 **COMANDOS ESPECÍFICOS DO PROJETO**

### **📊 Scripts de Importação**
```bash
# Importar municípios
docker exec aprender_web python manage.py import_municipios

# Importar projetos  
docker exec aprender_web python manage.py import_projetos

# Importar tipos de evento
docker exec aprender_web python manage.py import_tipos_evento

# Importar disponibilidades
docker exec aprender_web python manage.py import_disponibilidades

# Importar dados do Google Sheets
docker exec aprender_web python manage.py import_google_sheets
```

### **🔧 Manutenção e Limpeza**
```bash
# Limpar dados de teste
docker exec aprender_web python manage.py clean_test_data

# Configurar grupos
docker exec aprender_web python manage.py setup_groups

# Fixar grupos de usuário
docker exec aprender_web python manage.py fix_user_groups

# Organizar projetos por setor
docker exec aprender_web python manage.py organize_projects_by_sector
```

### **📈 Monitoramento e Teste**
```bash
# Teste de integração
docker exec aprender_web python manage.py integration_test

# Teste de algoritmos
docker exec aprender_web python manage.py test_algorithms

# Monitoramento do sistema
docker exec aprender_web python manage.py test_monitoring

# Verificação de calendário
docker exec aprender_web python manage.py calendar_check
```

### **🔍 Ferramentas Avançadas**
```bash
# Ferramentas Tier 2
docker exec aprender_web python manage.py tier2_tools

# Ferramentas Tier 3  
docker exec aprender_web python manage.py tier3_tools

# Assistente IA
docker exec aprender_web python manage.py ai_assistant

# Otimizar assets
docker exec aprender_web python manage.py optimize_assets
```

---

## 🔄 **WORKFLOW OBRIGATÓRIO**

### **🌅 Início do Trabalho**
```bash
# 1. Iniciar ambiente
docker-compose up -d

# 2. Verificar health
docker exec aprender_web python manage.py check

# 3. Verificar dados
docker exec aprender_web python manage.py shell -c "from core.models import Usuario; print(f'Usuários: {Usuario.objects.count()}')"
```

### **💻 Durante Desenvolvimento**
```bash
# Para qualquer comando Django, sempre use:
docker exec aprender_web python manage.py <comando>

# Para acessar shell interativo:
docker exec -it aprender_web python manage.py shell

# Para executar testes:
docker exec aprender_web python manage.py test
```

### **🔚 Fim do Trabalho**
```bash
# Parar containers (preserva dados)
docker-compose down

# Parar e remover volumes (CUIDADO - apaga dados)
docker-compose down -v
```

---

## 📊 **VERIFICAÇÕES OBRIGATÓRIAS**

### **✅ Checklist de Validação**
```bash
# 1. Containers rodando
docker ps | grep aprender

# 2. Banco PostgreSQL ativo
docker exec aprender_db pg_isready -U adm_aprender -d aprender_sistema_db

# 3. Django funcionando
docker exec aprender_web python manage.py check

# 4. Dados populados
docker exec aprender_web python manage.py shell -c "from core.models import Usuario, Municipio, Projeto; print(f'Usuários: {Usuario.objects.count()}, Municípios: {Municipio.objects.count()}, Projetos: {Projeto.objects.count()}')"

# 5. Aplicação acessível
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

---

## ⚠️ **RESOLUÇÃO DE PROBLEMAS**

### **🔧 Problemas Comuns**
```bash
# Container não inicia
docker-compose down && docker-compose up -d

# Banco não conecta
docker exec aprender_db pg_isready -U adm_aprender -d aprender_sistema_db

# Migrations pendentes
docker exec aprender_web python manage.py migrate

# Limpar cache
docker exec aprender_web python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Rebuild completo
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## 🎯 **ESTADO ATUAL CONFIRMADO**

### **📊 Dados Populados no Docker:**
- ✅ **119 Usuários** (dados das planilhas + teste)
- ✅ **83 Formadores** (vinculados aos usuários)
- ✅ **10 Municípios** (dados reais)
- ✅ **8 Projetos** (dados reais)
- ✅ **PostgreSQL** funcionando
- ✅ **Aplicação** rodando na porta 8000

### **🔑 Usuários de Teste:**
- `superintendente`
- `coordenador`  
- `formador_teste`
- `controle`
- Qualquer CPF dos usuários das planilhas

---

## 📝 **PRÓXIMOS PASSOS**

1. **Sempre usar** comandos Docker listados acima
2. **Nunca executar** comandos Python localmente
3. **Verificar regularmente** o health check
4. **Backup** dos dados PostgreSQL antes de mudanças grandes
5. **Testar** novas funcionalidades no container

---

**🐳 LEMBRETE: TODO COMANDO DEVE SER EXECUTADO VIA DOCKER EXEC!**

*Documento criado em: 2025-09-11*  
*Ambiente: Docker PostgreSQL*  
*Status: ✅ AMBIENTE 100% DOCKERIZADO*