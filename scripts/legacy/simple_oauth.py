import gspread

print("Iniciando OAuth2...")
try:
    gc = gspread.oauth(credentials_filename="google_oauth_credentials.json")
    print("OAuth2 autorizado com sucesso!")

    # Testar acesso
    sheet_id = "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
    sheet = gc.open_by_key(sheet_id)
    print(f"Planilha acessada: {sheet.title}")

except Exception as e:
    print(f"Erro: {e}")
