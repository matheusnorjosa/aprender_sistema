# Teste de Credenciais Google Sheets (gspread)

## Status

- **gspread disponível:** ✓ Sim
- **Credenciais testadas:** ✗ Não
- **GOOGLE_APPLICATION_CREDENTIALS:** ✗ Não definida

## Resultado

GOOGLE_APPLICATION_CREDENTIALS não definida

## Próximos Passos


1. Obter credenciais de Service Account do Google Cloud Console
2. Baixar arquivo JSON de credenciais
3. Definir variável de ambiente:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```
4. Instalar gspread se necessário:
   ```bash
   pip install gspread google-auth
   ```
5. Testar leitura de uma planilha pública
