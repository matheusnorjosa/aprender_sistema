"""
Testes para ETL de AcaoControle.

Valida:
- Idempotência (rodar 2x não duplica)
- Resolução de FKs (município, projeto, coordenador)
- Parsing de datas (ISO, dd/mm/yyyy, Excel serial)
- Tratamento de pendências (registros sem FK)
- Relatório em out_etl/
"""

import csv
import json
import pytest
from datetime import date
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.core.models import AcaoControle, Municipio, Projeto
from apps.core.services.controle_acoes_import import import_acoes_controle


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
        first_name="Maria",
        last_name="Silva",
    )

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    return {"coord": coord, "municipio": municipio, "projeto": projeto}


@pytest.fixture
def csv_valid(tmp_path, setup_dependencies):
    """Cria CSV válido com headers flexíveis."""
    csv_file = tmp_path / "acoes_controle.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Município",
                "Projeto",
                "Coordenador",
                "Data Entrega",
                "Data Carta",
                "Contato Inicial",
                "Data Reunião",
                "Observação",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Coordenador": "coord@example.com",
            "Data Entrega": "2025-01-15",
            "Data Carta": "15/01/2025",
            "Contato Inicial": "44951",  # Excel serial for 2025-01-20
            "Data Reunião": "2025-02-01",
            "Observação": "Teste observação",
        })

    return str(csv_file)


@pytest.fixture
def csv_with_missing_fk(tmp_path):
    """CSV com município inexistente."""
    csv_file = tmp_path / "acoes_missing.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Município", "Projeto", "Data Entrega"],
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Município Inexistente",
            "Projeto": "ACerta",
            "Data Entrega": "2025-01-01",
        })

    return str(csv_file)


def test_import_creates_acao_controle(csv_valid):
    """Importação cria AcaoControle com todas as datas parseadas."""
    report = import_acoes_controle(csv_valid, dry_run=False)

    assert report["stats"]["created"] == 1
    assert report["stats"]["skipped"]["municipio"] == 0
    assert report["dry_run"] is False

    acao = AcaoControle.objects.first()
    assert acao.municipio.nome == "Fortaleza"
    assert acao.projeto.nome == "ACerta"
    assert acao.coordenador.email == "coord@example.com"
    assert acao.data_entrega == date(2025, 1, 15)  # ISO
    assert acao.data_carta == date(2025, 1, 15)  # dd/mm/yyyy
    assert acao.contato_inicial == date(2025, 1, 20)  # Excel serial
    assert acao.data_reuniao == date(2025, 2, 1)
    assert acao.observacao == "Teste observação"
    assert acao.external_hash is not None


def test_idempotency_no_duplicates(csv_valid):
    """Rodar ETL 2x não duplica registros (external_hash)."""
    # Primeira rodada
    report1 = import_acoes_controle(csv_valid, dry_run=False)
    assert report1["stats"]["created"] == 1

    # Segunda rodada (idempotência)
    report2 = import_acoes_controle(csv_valid, dry_run=False)
    assert report2["stats"]["unchanged"] == 1
    assert report2["stats"]["created"] == 0

    # Total de registros permanece 1
    assert AcaoControle.objects.count() == 1


def test_dry_run_does_not_commit(csv_valid):
    """Dry-run não persiste dados no banco."""
    report = import_acoes_controle(csv_valid, dry_run=True)

    assert report["stats"]["created"] == 1
    assert report["dry_run"] is True

    # Banco está vazio (rollback)
    assert AcaoControle.objects.count() == 0


def test_skip_missing_municipio(csv_with_missing_fk):
    """Registros com município inexistente são pulados."""
    report = import_acoes_controle(csv_with_missing_fk, dry_run=False)

    assert report["stats"]["created"] == 0
    assert report["stats"]["skipped"]["municipio"] == 1

    pendencias = report["pendencias"]["municipios"]
    assert len(pendencias) == 1
    assert pendencias[0]["nome"] == "Município Inexistente"


def test_report_saved_to_out_etl(csv_valid):
    """Relatório é salvo em out_etl/import_acoes_controle_report.json."""
    import_acoes_controle(csv_valid, dry_run=False)

    report_path = Path(settings.BASE_DIR) / "out_etl" / "import_acoes_controle_report.json"
    assert report_path.exists()

    # Validar conteúdo do relatório
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "stats" in report
    assert "pendencias" in report
    assert "file" in report
    assert report["stats"]["created"] >= 0


def test_coordenador_optional(tmp_path, setup_dependencies):
    """Coordenador é opcional - registro criado mesmo se não encontrado."""
    csv_file = tmp_path / "acoes_no_coord.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Município", "Projeto", "Data Entrega"]
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Data Entrega": "2025-01-01",
        })

    report = import_acoes_controle(str(csv_file), dry_run=False)

    assert report["stats"]["created"] == 1

    acao = AcaoControle.objects.first()
    assert acao.coordenador is None  # Opcional, não bloqueia criação


def test_update_existing_record(tmp_path, setup_dependencies):
    """Atualiza registro existente se dados mudarem."""
    csv_file = tmp_path / "acoes_update.csv"

    # Criar inicial
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Município", "Projeto", "Data Entrega", "Observação"]
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Data Entrega": "2025-01-01",
            "Observação": "Versão 1",
        })

    report1 = import_acoes_controle(str(csv_file), dry_run=False)
    assert report1["stats"]["created"] == 1

    # Atualizar observação
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Município", "Projeto", "Data Entrega", "Observação"]
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Data Entrega": "2025-01-01",
            "Observação": "Versão 2 - atualizada",
        })

    report2 = import_acoes_controle(str(csv_file), dry_run=False)
    assert report2["stats"]["updated"] == 1

    acao = AcaoControle.objects.first()
    assert acao.observacao == "Versão 2 - atualizada"
    assert AcaoControle.objects.count() == 1  # Não duplicou
