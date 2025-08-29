# Configuração de Acesso ao Google Sheets

## Situação Atual
- A service account existente (`sistema-aprender-service-334@aprender-sistema-calendar.iam.gserviceaccount.com`) está vinculada a um projeto Google Cloud que foi deletado
- Você mencionou que compartilhou a planilha com: `integracao-sa@aprender-integracoes.iam.gserviceaccount.com`

## Para Resolver o Acesso

### Opção 1: Usar a Service Account Correta
1. Obter a chave JSON da service account `integracao-sa@aprender-integracoes.iam.gserviceaccount.com`
2. Substituir o arquivo `aprender_sistema/tools/service_account.json`

### Opção 2: Criar Nova Service Account
1. Acessar [Google Cloud Console](https://console.cloud.google.com/)
2. Criar ou selecionar um projeto ativo
3. Ativar APIs necessárias:
   - Google Sheets API
   - Google Drive API
4. Criar service account:
   - IAM & Admin > Service Accounts
   - Create Service Account
   - Nome: `sistema-aprender-sheets`
   - Gerar chave JSON
5. Compartilhar planilha com o email da service account

### Opção 3: Usar OAuth2 (Recomendado para Desenvolvimento)
Se preferir não usar service account, posso implementar OAuth2 flow.

## Estrutura Esperada do JSON da Service Account
```json
{
  "type": "service_account",
  "project_id": "seu-projeto-ativo",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "integracao-sa@aprender-integracoes.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
```

## Próximos Passos
1. ✅ **Sistema de análise implementado** - Comandos prontos para usar
2. ⏳ **Aguardando credentials válidas** - Precisa da service account correta
3. 🚀 **Após configurar credentials** - Executar análise completa automaticamente

## Comandos Disponíveis

### Teste de Conexão
```bash
python manage.py import_google_sheets_compras --test-connection
```

### Listar Planilhas Acessíveis
```bash
python manage.py import_google_sheets_compras --list-sheets
```

### Análise Completa da Planilha
```bash
python manage.py analyze_google_sheets --show-data-samples --output-file="analise_completa.json"
```

### Importar Dados de Compras
```bash
python manage.py import_google_sheets_compras --dry-run
```

## Recursos Implementados
- ✅ Conexão segura com Google Sheets API
- ✅ Análise completa de estrutura das planilhas
- ✅ Detecção automática de tipos de dados
- ✅ Identificação de propósito das abas (compras, formações, etc.)
- ✅ Relatórios de qualidade de dados
- ✅ Importação automática com tratamento de erros
- ✅ Sistema de cache para performance
- ✅ Logs detalhados de processamento

Assim que as credenciais estiverem configuradas, poderemos executar a varredura completa da planilha!