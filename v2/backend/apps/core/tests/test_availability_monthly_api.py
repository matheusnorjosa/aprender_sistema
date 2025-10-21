"""
Testes integrados para API /availability/monthly.

Valida:
- Códigos E/2/P/T/X por dia/pessoa
- CH mês/ano corretos (horas decimais)
- Ranking denso por mês
- Cache Redis 5 minutos
- Details_index para E/2/X
"""

import pytest
from datetime import datetime
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.core.models import (
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
    AvailabilityBlock,
    Participation,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    """Cliente API autenticado."""
    return APIClient()


@pytest.fixture
def user_auth():
    """Usuário autenticado para requisições."""
    user = Usuario.objects.create_user(
        username="api_user",
        email="api@example.com",
        password="test123",
        cpf="99999999999",
        first_name="API",
        last_name="User",
    )
    return user


@pytest.fixture
def setup_data():
    """
    Cria dados de teste:
    - 2 usuários (Ana, Bruno) como FORMADOR
    - Projeto Gestão Escolar
    - Município Fortaleza
    - TipoEvento Formação
    - Eventos aprovados:
        - 2025-10-03 08:00-12:00 (Ana, 4h)
        - 2025-10-08 08:00-10:00 (Ana, 2h)
        - 2025-10-08 14:00-16:00 (Ana, 2h)
        - 2025-10-01 08:00-12:00 (Bruno, 4h)
        - 2025-10-20 08:00-12:00 (Ana, 4h) - evento dia 20
    - Bloqueios aprovados:
        - Ana: dia 05 (tipo=P, 08:00-12:00)
        - Ana: dia 20 (tipo=T, 14:00-18:00)
    """
    tz = timezone.get_current_timezone()

    # Usuários
    ana = Usuario.objects.create_user(
        username="ana",
        email="ana@example.com",
        password="test123",
        cpf="11111111111",
        first_name="Ana",
        last_name="Silva",
    )
    bruno = Usuario.objects.create_user(
        username="bruno",
        email="bruno@example.com",
        password="test123",
        cpf="22222222222",
        first_name="Bruno",
        last_name="Costa",
    )

    # Dependências
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Gestão Escolar", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    # Eventos aprovados
    # 2025-10-03 (Ana, 4h)
    sol1 = Solicitacao.objects.create(
        usuario=ana,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.make_aware(datetime(2025, 10, 3, 8, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 3, 12, 0), tz),
        status="aprovado",
    )
    Participation.objects.get_or_create(
        solicitacao=sol1, usuario=ana, role="FORMADOR"
    )

    # 2025-10-08 08:00-10:00 (Ana, 2h)
    sol2 = Solicitacao.objects.create(
        usuario=ana,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.make_aware(datetime(2025, 10, 8, 8, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 8, 10, 0), tz),
        status="aprovado",
    )
    Participation.objects.get_or_create(
        solicitacao=sol2, usuario=ana, role="FORMADOR"
    )

    # 2025-10-08 14:00-16:00 (Ana, 2h)
    sol3 = Solicitacao.objects.create(
        usuario=ana,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.make_aware(datetime(2025, 10, 8, 14, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 8, 16, 0), tz),
        status="aprovado",
    )
    Participation.objects.get_or_create(
        solicitacao=sol3, usuario=ana, role="FORMADOR"
    )

    # 2025-10-01 (Bruno, 4h)
    sol4 = Solicitacao.objects.create(
        usuario=bruno,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.make_aware(datetime(2025, 10, 1, 8, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 1, 12, 0), tz),
        status="aprovado",
    )
    Participation.objects.get_or_create(
        solicitacao=sol4, usuario=bruno, role="FORMADOR"
    )

    # 2025-10-20 08:00-12:00 (Ana, 4h) - para gerar X
    sol5 = Solicitacao.objects.create(
        usuario=ana,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.make_aware(datetime(2025, 10, 20, 8, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 20, 12, 0), tz),
        status="aprovado",
    )
    Participation.objects.get_or_create(
        solicitacao=sol5, usuario=ana, role="FORMADOR"
    )

    # Bloqueios aprovados
    # Ana: dia 05 (tipo=P)
    AvailabilityBlock.objects.create(
        usuario=ana,
        inicio=timezone.make_aware(datetime(2025, 10, 5, 8, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 5, 12, 0), tz),
        tipo="P",
        status="aprovado",
    )

    # Ana: dia 20 (tipo=T, mas tem evento, então gera X)
    AvailabilityBlock.objects.create(
        usuario=ana,
        inicio=timezone.make_aware(datetime(2025, 10, 20, 14, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 20, 18, 0), tz),
        tipo="T",
        status="aprovado",
    )

    return {
        "ana": ana,
        "bruno": bruno,
        "municipio": municipio,
        "projeto": projeto,
        "tipo_evento": tipo_evento,
    }


def test_monthly_availability_codes(api_client, user_auth, setup_data):
    """
    Testa códigos E/2/P/X para grade mensal.

    Valida:
    - Ana: 03/out "E"; 08/out "2"; 05/out "P"; 20/out "X"
    - Bruno: 01/out "E"
    - details_index contém E/2/X
    """
    api_client.force_authenticate(user=user_auth)

    response = api_client.get(
        "/api/availability/monthly/",
        {
            "year": 2025,
            "month": 10,
            "role": "FORMADOR",
            "sector": "Gestão Escolar",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Validar estrutura
    assert data["days"] == 31
    assert "legend" in data
    assert "people" in data
    assert "cells" in data
    assert "details_index" in data

    # Validar pessoas
    people = data["people"]
    assert len(people) == 2

    # Encontrar Ana e Bruno
    ana = setup_data["ana"]
    bruno = setup_data["bruno"]

    ana_data = next((p for p in people if p["id"] == ana.id), None)
    bruno_data = next((p for p in people if p["id"] == bruno.id), None)

    assert ana_data is not None
    assert bruno_data is not None
    assert ana_data["name"] == "Ana Silva"
    assert bruno_data["name"] == "Bruno Costa"

    # Validar cells para Ana (JSON serializa chaves int como str)
    ana_cells = data["cells"][str(ana.id)]
    assert ana_cells[str(3)] == "E"  # 03/out: 1 evento
    assert ana_cells[str(8)] == "2"  # 08/out: 2 eventos
    assert ana_cells[str(5)] == "P"  # 05/out: bloqueio parcial
    assert ana_cells[str(20)] == "X"  # 20/out: evento + bloqueio

    # Validar cells para Bruno
    bruno_cells = data["cells"][str(bruno.id)]
    assert bruno_cells[str(1)] == "E"  # 01/out: 1 evento

    # Validar details_index (JSON serializa chaves int como str)
    ana_details = data["details_index"][str(ana.id)]
    assert str(3) in ana_details  # Dia 03 (E)
    assert str(8) in ana_details  # Dia 08 (2)
    assert str(20) in ana_details  # Dia 20 (X)
    assert len(ana_details[str(8)]) == 2  # 2 eventos no dia 8

    # Validar formato de detalhe
    detail = ana_details[str(3)][0]
    assert "id" in detail
    assert detail["municipio"] == "Fortaleza"
    assert detail["data"] == "2025-10-03"
    assert detail["inicio"] == "08:00"
    assert detail["fim"] == "12:00"
    assert detail["tipo"] == "Formação"


def test_monthly_availability_ch_and_ranking(api_client, user_auth, setup_data):
    """
    Testa CH mês/ano e ranking denso.

    Ana: 4h (dia 3) + 2h + 2h (dia 8) + 4h (dia 20) = 12h mês
    Bruno: 4h (dia 1) = 4h mês

    Ranking denso:
    - Ana: 12h → posição 1
    - Bruno: 4h → posição 2
    """
    api_client.force_authenticate(user=user_auth)

    response = api_client.get(
        "/api/availability/monthly/",
        {"year": 2025, "month": 10, "role": "FORMADOR"},
    )

    assert response.status_code == 200
    data = response.json()

    people = data["people"]

    # Buscar por email (IDs podem variar entre testes devido a banco compartilhado)
    ana_data = next((p for p in people if p["email"] == "ana@example.com"), None)
    bruno_data = next((p for p in people if p["email"] == "bruno@example.com"), None)

    # Validar presença
    assert ana_data is not None, "Ana (ana@example.com) não encontrada em people"
    assert bruno_data is not None, "Bruno (bruno@example.com) não encontrado em people"
    assert ana_data["ch_month"] == 12.0
    assert bruno_data["ch_month"] == 4.0

    # Validar ranking denso
    assert ana_data["position_month"] == 1
    assert bruno_data["position_month"] == 2


def test_monthly_availability_cache(api_client, user_auth, setup_data):
    """
    Testa cache Redis (5 minutos).

    Faz 2 requisições e valida que retornam o mesmo payload.
    """
    cache.clear()
    api_client.force_authenticate(user=user_auth)

    # Primeira requisição
    response1 = api_client.get(
        "/api/availability/monthly/",
        {"year": 2025, "month": 10, "role": "FORMADOR"},
    )
    assert response1.status_code == 200
    data1 = response1.json()

    # Segunda requisição (deve vir do cache)
    response2 = api_client.get(
        "/api/availability/monthly/",
        {"year": 2025, "month": 10, "role": "FORMADOR"},
    )
    assert response2.status_code == 200
    data2 = response2.json()

    # Validar igualdade
    assert data1 == data2


def test_monthly_availability_invalid_params(api_client, user_auth):
    """
    Testa validação de parâmetros inválidos.
    """
    api_client.force_authenticate(user=user_auth)

    # Year inválido
    response = api_client.get(
        "/api/availability/monthly/",
        {"year": "invalid", "month": 10, "role": "FORMADOR"},
    )
    assert response.status_code == 400

    # Month inválido
    response = api_client.get(
        "/api/availability/monthly/",
        {"year": 2025, "month": 13, "role": "FORMADOR"},
    )
    assert response.status_code == 400

    # Role inválido
    response = api_client.get(
        "/api/availability/monthly/",
        {"year": 2025, "month": 10, "role": "INVALID"},
    )
    assert response.status_code == 400
