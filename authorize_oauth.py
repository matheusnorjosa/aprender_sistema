#!/usr/bin/env python
"""
Script de autorização OAuth2 com tratamento de erros
"""
import os
import sys


def authorize_google_access():
    """Executa autorização OAuth2 para Google Sheets"""

    print("=== AUTORIZAÇÃO GOOGLE OAUTH2 ===")
    print("Email: aprender-sistema@aprendereditora.com.br")
    print("Senha: Sistema@123")
    print()
    print("Este script abrirá o navegador para autorização...")
    print("Pressione Ctrl+C para cancelar")

    try:
        input("Pressione Enter para continuar...")

        print("\nIniciando autorização OAuth2...")

        import gspread

        # Tentar autorização
        gc = gspread.oauth(
            credentials_filename="google_oauth_credentials.json",
            authorized_user_filename="google_authorized_user.json",
        )

        print("✅ AUTORIZAÇÃO CONCLUÍDA COM SUCESSO!")

        # Testar acesso básico
        print("\nTestando acesso às planilhas...")

        # Testar planilha de usuários
        sheet_id = "1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI"
        sheet = gc.open_by_key(sheet_id)

        print(f"✅ Planilha acessada: {sheet.title}")
        print(f"✅ Abas disponíveis: {len(sheet.worksheets())}")

        # Testar leitura
        worksheet = sheet.sheet1
        first_row = worksheet.row_values(1)

        print(f"✅ Primeira linha lida: {len(first_row)} colunas")

        print("\n🎉 SISTEMA GOOGLE FUNCIONANDO PERFEITAMENTE!")
        print("\nPróximos passos automáticos:")
        print("- Extração de dados históricos")
        print("- Análise de estruturas das planilhas")
        print("- Implementação de sincronização")

        return True

    except KeyboardInterrupt:
        print("\n❌ Autorização cancelada pelo usuário")
        return False

    except Exception as e:
        print(f"\n❌ Erro na autorização: {e}")

        if "OAuth2" in str(e) or "authorization" in str(e).lower():
            print("\nDicas para resolver:")
            print("1. Verifique se o email está correto")
            print("2. Use aprender-sistema@aprendereditora.com.br")
            print("3. Autorize todas as permissões solicitadas")
            print("4. Aguarde o navegador carregar completamente")

        return False


if __name__ == "__main__":
    success = authorize_google_access()

    if success:
        print("\n✅ PRONTO PARA EXTRAÇÃO DE DADOS!")
        sys.exit(0)
    else:
        print("\n❌ AUTORIZAÇÃO NECESSÁRIA PARA CONTINUAR")
        sys.exit(1)
