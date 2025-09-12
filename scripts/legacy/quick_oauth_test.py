#!/usr/bin/env python
"""
Teste rápido de autorização OAuth2
"""
import os

from dotenv import load_dotenv

load_dotenv()

print("=== TESTE RÁPIDO OAUTH2 ===")

try:
    import gspread

    print("1. gspread importado OK")

    # Tentar OAuth2
    print("2. Tentando OAuth2...")
    gc = gspread.oauth()
    print("   OK - OAuth2 autorizado!")

    # Testar uma planilha
    sheet_id = os.getenv("GOOGLE_SHEETS_USUARIOS_ID")
    print(f"3. Testando planilha: {sheet_id}")

    sheet = gc.open_by_key(sheet_id)
    print(f"   OK - Planilha aberta: {sheet.title}")

    worksheet = sheet.sheet1
    data = worksheet.get_all_values()[:5]  # Apenas 5 linhas
    print(f"   OK - Dados lidos: {len(data)} linhas")

    if data:
        print(f"   Primeira linha: {data[0]}")

    print("\n🎉 CONEXÃO GOOGLE SHEETS FUNCIONANDO!")
    print("✅ Sistema pronto para extração completa!")

except Exception as e:
    print(f"❌ Erro: {e}")

    if "OAuth2" in str(e) or "authorization" in str(e).lower():
        print("\n📝 Autorização necessária:")
        print("1. Execute o teste novamente")
        print("2. Autorize no navegador que abrir")
        print("3. Feche o navegador após autorizar")
