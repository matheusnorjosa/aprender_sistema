#!/usr/bin/env python
"""
Autorização OAuth2 direta sem input do usuário
"""
print("=== INICIANDO OAUTH2 AUTOMATICO ===")
print("Email: aprender-sistema@aprendereditora.com.br")

try:
    import gspread

    print("Executando OAuth2...")

    # Autorização OAuth2
    gc = gspread.oauth(
        credentials_filename="google_oauth_credentials.json",
        authorized_user_filename="google_authorized_user.json",
    )

    print("SUCESSO: OAuth2 autorizado!")

    # Testar acesso às planilhas
    print("\nTestando acesso as planilhas...")

    # Planilha de usuários
    sheet_id = "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
    sheet = gc.open_by_key(sheet_id)

    print(f"SUCESSO: Planilha acessada - {sheet.title}")

    # Testar outras planilhas
    planilhas_test = [
        ("Disponibilidade", "1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw"),
        ("Controle", "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"),
        ("Acompanhamento", "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"),
    ]

    sucessos = 0
    for nome, sheet_id in planilhas_test:
        try:
            sheet = gc.open_by_key(sheet_id)
            print(f"SUCESSO: {nome} - {sheet.title}")
            sucessos += 1
        except Exception as e:
            print(f"ERRO: {nome} - {str(e)[:50]}...")

    print(f"\nRESULTADO: {sucessos + 1}/{len(planilhas_test) + 1} planilhas acessiveis")

    if sucessos >= 3:
        print("\nSISTEMA GOOGLE FUNCIONANDO!")
        print("Pronto para extracao de dados!")

except Exception as e:
    print(f"ERRO: {str(e)[:100]}...")

    if "authorization" in str(e).lower():
        print("INFO: Necessario autorizar no navegador")
        print("Use: aprender-sistema@aprendereditora.com.br")
