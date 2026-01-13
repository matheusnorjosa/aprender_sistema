"""
Testes de idempotência do ETL de Acompanhamento.

Valida que rodar 2x o mesmo CSV não duplica Solicitações/Participations.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

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
    """Cria dependências necessárias para o ETL."""
    coord = User.objects.create_user(
        username="coord1",
        email="coord@example.com",
        password="test123",
        cpf="11111111111",
        first_name="Coordenador",
        last_name="Um",
    )
    form1 = User.objects.create_user(
        username="form1",
        email="form1@example.com",
        password="test123",
        cpf="22222222222",
    )
    form2 = User.objects.create_user(
        username="form2",
        email="form2@example.com",
        password="test123",
        cpf="33333333333",
    )

    Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    Projeto.objects.create(nome="ACerta", ativo=True)
    TipoEvento.objects.create(nome="Formação", descricao="Formação continuada")

    return {"coord": coord, "form1": form1, "form2": form2}


@pytest.fixture
def csv_files(tmp_path):
    """Cria CSVs temporários mínimos."""
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
            "event_hash": "test001",
            "source_sheet": "ACerta",
            "municipio": "Fortaleza",
            "tipo": "Formação",
            "data": "2025-02-15",
            "hora_inicio": "14:00",
            "hora_fim": "18:00",
            "projeto": "ACerta",
            "aprovacao": "",
        })

    participantes_csv = tmp_path / "participantes.csv"
    with open(participantes_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["event_hash", "role", "display_name", "email"]
        )
        writer.writeheader()
        writer.writerow({
            "event_hash": "test001",
            "role": "COORDENADOR",
            "display_name": "Coordenador Um",
            "email": "coord@example.com",
        })
        writer.writerow({
            "event_hash": "test001",
            "role": "FORMADOR",
            "display_name": "",
            "email": "form1@example.com",
        })
        writer.writerow({
            "event_hash": "test001",
            "role": "FORMADOR",
            "display_name": "",
            "email": "form2@example.com",
        })

    return str(eventos_csv), str(participantes_csv)


def test_two_runs_no_duplicates(csv_files, setup_dependencies):
    """
    Roda ETL 2x: deve criar 1 Solicitação + 3 Participation sem duplicar.
    """
    eventos_csv, participantes_csv = csv_files

    # Primeira rodada
    call_command(
        "etl_upsert_acompanhamento",
        events_csv=eventos_csv,
        participants_csv=participantes_csv,
        today="2025-01-01",
        apply=True,  # Persist data to DB
    )

    assert Solicitacao.objects.count() == 1
    assert Participation.objects.count() == 3

    # Segunda rodada (idempotência)
    call_command(
        "etl_upsert_acompanhamento",
        events_csv=eventos_csv,
        participants_csv=participantes_csv,
        today="2025-01-01",
        apply=True,  # Persist data to DB
    )

    # Não duplica
    assert Solicitacao.objects.count() == 1
    assert Participation.objects.count() == 3
