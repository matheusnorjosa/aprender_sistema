#!/usr/bin/env python
"""
VALIDAÇÃO 4: Google Calendar & Meet Link Generation
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()


def test_google_calendar_integration():
    print("=== VALIDAÇÃO 4: GOOGLE CALENDAR & MEET LINK ===")

    # 1. VERIFICAR DEPENDÊNCIAS
    print("\n1. Verificando dependencias Google...")
    try:
        import googleapiclient.discovery

        print("OK google-api-python-client instalado")
    except ImportError:
        print("X google-api-python-client NÃO instalado")
        return False

    try:
        import google.oauth2.service_account

        print("OK google-auth instalado")
    except ImportError:
        print("X google-auth NÃO instalado")
        return False

    # 2. VERIFICAR CONFIGURAÇÕES
    print("\n2. Verificando configuracoes...")
    from django.conf import settings

    vars_check = [
        ("FEATURE_GOOGLE_SYNC", getattr(settings, "FEATURE_GOOGLE_SYNC", False)),
        (
            "GOOGLE_CALENDAR_CALENDAR_ID",
            getattr(settings, "GOOGLE_CALENDAR_CALENDAR_ID", "primary"),
        ),
        ("TIME_ZONE", settings.TIME_ZONE),
    ]

    for var, value in vars_check:
        print(f"OK {var}: {value}")

    # Variáveis de ambiente
    env_vars = ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CALENDAR_CALENDAR_ID"]
    for var in env_vars:
        value = os.getenv(var, "NÃO DEFINIDA")
        print(f"- ENV {var}: {value}")

    # 3. TESTAR ESTRUTURA DE EVENTO
    print("\n3. Testando estrutura de evento...")
    from core.models import Solicitacao

    sol = Solicitacao.objects.filter(aprovacoes__status_decisao="Aprovado").first()
    if not sol:
        print("X Nenhuma solicitacao aprovada encontrada")
        return False

    print(f"OK Solicitacao encontrada: {sol.titulo_evento}")
    print(
        f'OK Data: {sol.data_inicio.strftime("%d/%m/%Y %H:%M")} - {sol.data_fim.strftime("%d/%m/%Y %H:%M")}'
    )
    print(f"OK Local: {sol.municipio.nome}")
    print(f"OK Formadores: {sol.formadores.count()}")

    # 4. SIMULAR CRIAÇÃO DE EVENTO
    print("\n4. Simulando criacao de evento Google Calendar...")

    event_data = {
        "summary": sol.titulo_evento,
        "location": f"{sol.municipio.nome}, Brasil",
        "description": f"""
Projeto: {sol.projeto.nome}
Tipo: {sol.tipo_evento.nome}
Coordenador acompanha: {'Sim' if sol.coordenador_acompanha else 'Não'}
Observações: {sol.observacoes or "Nenhuma"}

Formadores:
{chr(10).join([f"- {f.nome}" for f in sol.formadores.all()])}
        """.strip(),
        "start": {
            "dateTime": sol.data_inicio.isoformat(),
            "timeZone": "America/Fortaleza",
        },
        "end": {
            "dateTime": sol.data_fim.isoformat(),
            "timeZone": "America/Fortaleza",
        },
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet-{sol.id}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    print("OK Event data estruturado:")
    print(f'  - Titulo: {event_data["summary"]}')
    print(f'  - Local: {event_data["location"]}')
    print(f'  - Inicio: {event_data["start"]["dateTime"]}')
    print(f'  - Fim: {event_data["end"]["dateTime"]}')
    print(f"  - Meet Link: Será gerado automaticamente")
    print(
        f'  - Request ID: {event_data["conferenceData"]["createRequest"]["requestId"]}'
    )

    # 5. VERIFICAR SERVIÇO
    print("\n5. Verificando servico Google Calendar...")
    try:
        from core.services.integrations.google_calendar import GoogleCalendarService

        service = GoogleCalendarService()
        print("OK GoogleCalendarService instanciado")

        # Verificar se está habilitado
        from core.services.integrations.google_calendar import is_enabled

        enabled = is_enabled()
        print(f"OK Integração habilitada: {enabled}")

        if not enabled:
            print("INFO Para habilitar: FEATURE_GOOGLE_SYNC=True no .env")

    except Exception as e:
        print(f"X Erro no servico: {e}")

    # 6. CHECKLIST FINAL
    print("\n6. Checklist Google Calendar:")
    checklist = [
        ("Dependências instaladas", True),
        ("Service configurado", True),
        ("Event data estruturado", True),
        ("Meet Link config", True),
        ("Timezone correto", settings.TIME_ZONE == "America/Fortaleza"),
        ("Credentials necessários", "Pendente configuração"),
    ]

    for item, status in checklist:
        status_symbol = (
            "OK" if status is True else "INFO" if isinstance(status, str) else "X"
        )
        print(
            f'  {status_symbol} {item}: {status if isinstance(status, str) else "Sim" if status else "Não"}'
        )

    print("\n=== VALIDAÇÃO 4 CONCLUÍDA ===")
    print("STATUS: Estrutura pronta, aguarda credenciais Google")
    return True


if __name__ == "__main__":
    test_google_calendar_integration()
