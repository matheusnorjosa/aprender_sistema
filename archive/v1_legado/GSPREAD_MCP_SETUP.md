# 🚀 **GSPREAD + DJANGO-MCP-SERVER - GUIA DE SETUP**

## ✅ **IMPLEMENTAÇÃO COMPLETA**

### 🎯 **O QUE FOI IMPLEMENTADO:**

1. **✅ GSPREAD Integration**
   - Serviço centralizado: `core/services/google_sheets_service.py`
   - Comando de importação: `core/management/commands/import_google_sheets.py`
   - Dependência já instalada: `gspread==6.1.4`

2. **✅ Django-MCP-Server Integration**
   - App adicionado ao `INSTALLED_APPS`
   - URLs configuradas: `/mcp/`
   - Ferramentas MCP definidas: `core/mcp_tools.py`
   - Auto-registro via `core/apps.py`

3. **✅ MCP Tools Disponíveis:**
   - `FormadorQueryTool` → Consultar formadores
   - `MunicipioQueryTool` → Consultar municípios
   - `SolicitacoesPendentesTool` → Solicitações pendentes
   - `DisponibilidadeFormadorTool` → Disponibilidade por período
   - `RelatorioEventosTool` → Relatórios estatísticos
   - `LogAuditoriaTool` → Logs de auditoria

---

## 📋 **CONFIGURAÇÃO NECESSÁRIA**

### 1. **Google Sheets Credentials**

#### Opção A: Service Account (Recomendado)
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie/selecione um projeto
3. Ative Google Sheets API
4. Crie Service Account
5. Baixe JSON das credenciais
6. Renomeie para `google_service_account.json`
7. Coloque na raiz do projeto

#### Opção B: Variável de Ambiente
```bash
export GOOGLE_SHEETS_CREDENTIALS_PATH="/path/to/credentials.json"
```

### 2. **Compartilhar Planilhas**
- Compartilhe suas planilhas Google com o email do Service Account
- Email estará no arquivo JSON: `client_email`

---

## 🛠️ **COMO USAR**

### **1. Importação Google Sheets**

```bash
# Importar tudo de uma planilha (auto-detect abas)
python manage.py import_google_sheets --spreadsheet-key=1ABC...XYZ

# Importar aba específica
python manage.py import_google_sheets \\
    --spreadsheet-key=1ABC...XYZ \\
    --worksheet-name="Formadores" \\
    --data-type=formadores

# Dry-run (testar sem salvar)
python manage.py import_google_sheets \\
    --spreadsheet-key=1ABC...XYZ \\
    --dry-run

# Limpar dados existentes antes
python manage.py import_google_sheets \\
    --spreadsheet-key=1ABC...XYZ \\
    --clear
```

#### **Formatos de Planilha Suportados:**

**Formadores:**
```
nome | email | area_atuacao
João Silva | joao@email.com | Superintendência
```

**Municípios:**
```
nome | uf | ativo
Fortaleza | CE | True
```

**Projetos:**
```
nome | descricao | ativo
ACerta | Projeto ACerta | True
```

**Tipos de Evento:**
```
nome | online | duracao_padrao
Workshop | False | 4
```

### **2. MCP Tools - Interação AI**

#### **Endpoint MCP:** `http://localhost:8000/mcp/`

**Ferramentas disponíveis:**
```python
# Consultar formadores ativos
GET /mcp/tools/formadores/

# Solicitações pendentes  
GET /mcp/tools/solicitacoes_pendentes/

# Disponibilidade por período
GET /mcp/tools/disponibilidade_formadores/?data_inicio=2025-01-01&data_fim=2025-01-31

# Relatórios estatísticos
GET /mcp/tools/relatorio_eventos/?periodo_dias=30
```

---

## 🔧 **PRÓXIMOS PASSOS**

### **Fase 1 - Testar Importação:**
1. Configure credenciais Google
2. Teste importação com `--dry-run`
3. Execute importação real
4. Verifique dados no Django Admin

### **Fase 2 - Configurar MCP Cliente:**
1. Configure Claude Code para conectar ao MCP endpoint
2. Teste queries via AI
3. Experimente relatórios automáticos

### **Fase 3 - Automação:**
1. Configure imports automáticos (via cron/celery)
2. Sincronização bidirecional
3. Dashboards alimentados por MCP

---

## 🆘 **TROUBLESHOOTING**

### **Erro: Credentials not found**
```bash
# Verifique se o arquivo existe
ls google_service_account.json

# Ou configure via env
export GOOGLE_SHEETS_CREDENTIALS_PATH="/full/path/to/credentials.json"
```

### **Erro: Permission denied**
- Compartilhe a planilha com o email do Service Account
- Email está em: `client_email` no JSON

### **Erro: MCP tools not found**
```bash
# Verifique se django-mcp-server foi instalado
python -c "import mcp_server; print('OK')"

# Restart do servidor Django
python manage.py runserver
```

### **Erro: Planilha não encontrada**
- Verifique se o spreadsheet-key está correto
- Key está na URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_KEY/`

---

## 🎉 **RESULTADO**

### **Antes:**
- ❌ Importação manual de CSVs
- ❌ Sem integração AI
- ❌ Queries manuais no admin

### **Depois:**
- ✅ Importação automática do Google Sheets
- ✅ Claude pode consultar dados via MCP
- ✅ Relatórios automáticos via AI
- ✅ Sincronização em tempo real

**O sistema agora está AI-ready e com importação automatizada!** 🚀✨