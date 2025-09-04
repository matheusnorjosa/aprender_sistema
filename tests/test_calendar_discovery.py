"""
Script para descobrir o Calendar ID do calendário "Formações"
"""

import os
import sys

import django

# Configurar Django
sys.path.append(r"C:\Users\datsu\OneDrive\Documentos\Aprender Sistema")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.conf import settings

from google.oauth2 import service_account
from googleapiclient.discovery import build


def discover_calendar_id():
    """Descobrir o Calendar ID do calendário Formações"""

    try:
        print("Buscando Calendar ID do calendario 'Formacoes'...")
        print(f"Usando credenciais: {settings.GOOGLE_CALENDAR_CREDENTIALS_FILE}")

        # Configurar credenciais
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_CALENDAR_CREDENTIALS_FILE, scopes=SCOPES
        )

        # Criar serviço
        service = build("calendar", "v3", credentials=credentials)

        # Listar todos os calendários acessíveis
        print("\nCalendarios encontrados:")
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get("items", [])

        formacoes_calendars = []

        for calendar in calendars:
            calendar_id = calendar.get("id", "")
            summary = calendar.get("summary", "")
            description = calendar.get("description", "")
            access_role = calendar.get("accessRole", "")
            primary = calendar.get("primary", False)

            print(f"\n  {summary}")
            print(f"     ID: {calendar_id}")
            print(f"     Acesso: {access_role}")
            print(f"     Primario: {primary}")

            if description:
                print(f"     Descricao: {description}")

            # Procurar por calendários que contenham "Formações"
            if "formações" in summary.lower() or "formacoes" in summary.lower():
                formacoes_calendars.append(
                    {"id": calendar_id, "summary": summary, "access_role": access_role}
                )
                print(f"     >>> POSSIVEL MATCH PARA 'FORMACOES'!")

        print(f"\nTotal de calendarios encontrados: {len(calendars)}")

        if formacoes_calendars:
            print(
                f"\nCalendarios que podem ser 'Formacoes': {len(formacoes_calendars)}"
            )
            for cal in formacoes_calendars:
                print(f"   >>> {cal['summary']}: {cal['id']}")
                print(f"      Acesso: {cal['access_role']}")
        else:
            print("\nNenhum calendario encontrado com nome similar a 'Formacoes'")
            print("\nPossiveis solucoes:")
            print("   1. Calendario ainda nao foi compartilhado com a Service Account")
            print("   2. Nome exato do calendario eh diferente")
            print("   3. Service Account nao tem permissoes suficientes")

        # Instruções para o próximo passo
        print("\nPROXIMOS PASSOS:")
        print("   1. Se encontrou o calendario 'Formacoes', copie o ID")
        print("   2. Se nao encontrou, compartilhe o calendario com:")
        print(
            f"      sistema-aprender-service-334@aprender-sistema-calendar.iam.gserviceaccount.com"
        )
        print("   3. Configure o GOOGLE_CALENDAR_ID no settings.py")

        return formacoes_calendars

    except FileNotFoundError:
        print("Arquivo de credenciais nao encontrado!")
        print(f"   Verificar: {settings.GOOGLE_CALENDAR_CREDENTIALS_FILE}")
        return []

    except Exception as e:
        print(f"Erro ao descobrir Calendar ID: {e}")
        return []


if __name__ == "__main__":
    discover_calendar_id()
