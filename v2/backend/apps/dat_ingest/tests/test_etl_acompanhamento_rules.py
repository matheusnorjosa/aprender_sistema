"""
Testes de regras de negócio do ETL de Acompanhamento.

Valida:
- Super com múltiplos municípios → N Solicitações
- Outros sem formadores → Coordenador também é FORMADOR
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import csv
import pytest
from django.core.management import call_command
from django.contrib.auth import get_user_model

from apps.core.models import Municipio, Projeto, TipoEvento, Solicitacao, Participation


User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_dependencies():
    """Cria dependências para testes."""
    coord = User.objects.create_user(
        username="coord1",
        email="coord@example.com",
        password="test123",
        cpf="11111111111",
    )

    Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    Municipio.objects.create(nome="Caucaia", uf="CE", ativo=True)
    Projeto.objects.create(nome="Super", ativo=True)
    Projeto.objects.create(nome="Gestão Escolar", ativo=True)
    TipoEvento.objects.create(nome="Formação")

    return {"coord": coord}


def test_super_multi_municipio(tmp_path, setup_dependencies):
    """
    Super com "Fortaleza; Caucaia" → 2 Solicitações (1 por município).
    """
    eventos_csv = tmp_path / "eventos.csv"
    with open(eventos_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "event_hash",
                "source_sheet",
                "municipio",
                "tipo",
                "data",
                "hora_inicio",
                "hora_fim",
                "projeto",
                "aprovacao",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "event_hash": "super001",
            "source_sheet": "Super",
            "municipio": "Fortaleza; Caucaia",
            "tipo": "Formação",
            "data": "2025-01-10",
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "projeto": "Super",
            "aprovacao": "SIM",
        })

    participantes_csv = tmp_path / "participantes.csv"
    with open(participantes_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["event_hash", "role", "display_name", "email"]
        )
        writer.writeheader()
        writer.writerow({
            "event_hash": "super001",
            "role": "COORDENADOR",
            "display_name": "",
            "email": "coord@example.com",
        })

    call_command(
        "etl_upsert_acompanhamento",
        events_csv=str(eventos_csv),
        participants_csv=str(participantes_csv),
        today="2025-02-01",  # Evento no passado
        apply=True,  # Persist data to DB
    )

    # Deve criar 2 Solicitações (1 por município)
    assert Solicitacao.objects.count() == 2

    fortaleza_sol = Solicitacao.objects.get(municipio__nome="Fortaleza")
    caucaia_sol = Solicitacao.objects.get(municipio__nome="Caucaia")

    assert fortaleza_sol.status == "aprovado"  # Passado + SIM
    assert caucaia_sol.status == "aprovado"

    # Ambos com external_hash diferente
    assert fortaleza_sol.external_hash != caucaia_sol.external_hash


def test_outros_sem_formador_duplica_coordenador(tmp_path, setup_dependencies):
    """
    Outros sem formadores → Coordenador também é FORMADOR.
    """
    eventos_csv = tmp_path / "eventos.csv"
    with open(eventos_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "event_hash",
                "source_sheet",
                "municipio",
                "tipo",
                "data",
                "hora_inicio",
                "hora_fim",
                "projeto",
                "aprovacao",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "event_hash": "outros001",
            "source_sheet": "Outros",
            "municipio": "Fortaleza",
            "tipo": "Formação",
            "data": "2025-03-20",
            "hora_inicio": "14:00",
            "hora_fim": "17:00",
            "projeto": "IDEB",  # → Gestão Escolar
            "aprovacao": "",
        })

    participantes_csv = tmp_path / "participantes.csv"
    with open(participantes_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["event_hash", "role", "display_name", "email"]
        )
        writer.writeheader()
        # Apenas COORDENADOR (sem FORMADOR)
        writer.writerow({
            "event_hash": "outros001",
            "role": "COORDENADOR",
            "display_name": "",
            "email": "coord@example.com",
        })

    call_command(
        "etl_upsert_acompanhamento",
        events_csv=str(eventos_csv),
        participants_csv=str(participantes_csv),
        today="2025-01-01",
        apply=True,  # Persist data to DB
    )

    assert Solicitacao.objects.count() == 1
    solicitacao = Solicitacao.objects.first()

    # Deve ter 2 Participations: COORDENADOR + FORMADOR (mesmo usuário)
    participations = Participation.objects.filter(solicitacao=solicitacao)
    assert participations.count() == 2

    roles = {p.role for p in participations}
    assert roles == {"COORDENADOR", "FORMADOR"}

    # Mesmo usuário em ambos
    usuarios = {p.usuario.email for p in participations}
    assert usuarios == {"coord@example.com"}
