#!/usr/bin/env python
"""
Extração silenciosa da planilha Controle 2025
"""
import json
import os
import sys
from datetime import datetime

import gspread
from dotenv import load_dotenv

load_dotenv()


def clean_unicode_text(text):
    """Remove caracteres Unicode problemáticos"""
    if not isinstance(text, str):
        return text

    # Substituir emojis por códigos
    replacements = {
        "\U0001f7e5": "LARANJA",
        "\U0001f7e6": "AZUL",
        "\U0001f7e7": "ROXO",
        "\U0001f7e8": "AMARELO",
        "\U0001f7e9": "VERDE",
        "\U0001f7ea": "VERMELHO",
        "\u2705": "OK",
        "\u274c": "X",
        "\U0001f680": "NEXT",
        "\U0001f525": "HOT",
    }

    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)

    # Converter caracteres acentuados para ASCII
    import unicodedata

    try:
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
    except:
        pass

    return text


def extract_controle_silent():
    """Extração silenciosa sem print problemático"""

    try:
        # Log de progresso em arquivo
        log_messages = []
        log_messages.append("INICIO: Extraindo Controle 2025")

        # Conectar com gspread
        gc = gspread.oauth(
            credentials_filename="google_oauth_credentials.json",
            authorized_user_filename="google_authorized_user.json",
        )

        # Abrir planilha
        controle_id = os.getenv("GOOGLE_SHEETS_CONTROLE_ID")
        sheet = gc.open_by_key(controle_id)

        log_messages.append(f"OK: Planilha {sheet.title} aberta")

        # Extrair abas
        worksheets_data = {}
        total_records = 0

        for worksheet in sheet.worksheets():
            aba_nome = worksheet.title
            log_messages.append(f"Processando: {aba_nome}")

            try:
                # Obter dados
                raw_data = worksheet.get_all_values()

                # Limpar Unicode
                clean_data = []
                for row in raw_data:
                    clean_row = [clean_unicode_text(str(cell)) for cell in row]
                    clean_data.append(clean_row)

                worksheets_data[aba_nome] = {
                    "headers": clean_data[0] if clean_data else [],
                    "data": clean_data[1:] if len(clean_data) > 1 else [],
                    "total_rows": len(clean_data),
                    "total_cols": len(clean_data[0]) if clean_data else 0,
                }

                total_records += len(clean_data)
                log_messages.append(f"OK: {aba_nome} - {len(clean_data)} registros")

            except Exception as e:
                log_messages.append(f"ERRO: {aba_nome} - {str(e)[:30]}")
                worksheets_data[aba_nome] = {
                    "headers": [],
                    "data": [],
                    "total_rows": 0,
                    "total_cols": 0,
                    "error": str(e),
                }

        # Salvar dados
        dados_controle = {
            "planilha_nome": sheet.title,
            "planilha_id": controle_id,
            "data_extracao": datetime.now().isoformat(),
            "total_abas": len(sheet.worksheets()),
            "total_registros": total_records,
            "worksheets": worksheets_data,
            "unicode_cleaning": True,
            "extraction_log": log_messages,
        }

        # Salvar arquivo
        with open("extracted_controle.json", "w", encoding="utf-8") as f:
            json.dump(dados_controle, f, indent=2, ensure_ascii=False)

        # Salvar log separado
        with open("extraction_controle.log", "w", encoding="utf-8") as f:
            for msg in log_messages:
                f.write(msg + "\n")

        # Retornar sucesso silenciosamente
        return True

    except Exception as e:
        # Salvar erro em arquivo
        with open("extraction_error.log", "w", encoding="utf-8") as f:
            f.write(f"ERRO: {str(e)}\n")
        return False


if __name__ == "__main__":
    # Redirecionar stdout para evitar problemas de encoding
    sys.stdout = open(os.devnull, "w")

    success = extract_controle_silent()

    # Restaurar stdout
    sys.stdout = sys.__stdout__

    if success:
        print("SUCCESS: extracted_controle.json criado")
    else:
        print("ERROR: Verifique extraction_error.log")
