"""
Testes para ETL de AcaoControle.

Valida:
- Idempotência (rodar 2x não duplica)
- Resolução de FKs (município, projeto, coordenador)
- Parsing de datas (ISO, dd/mm/yyyy, Excel serial)
- Tratamento de pendências (registros sem FK)
- Relatório em out_etl/
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import csv
import json
import tempfile
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model

import pytest

from apps.core.models import AcaoControle, Municipio, Projeto
from apps.core.services.controle_acoes_import import import_acoes_controle

User = get_user_model()
pytestmark = pytest.mark.django_db


def _create_csv_file(rows, fieldnames):
    """Helper para criar arquivo CSV temporário."""
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8", newline="")
    writer = csv.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    tmp.close()
    return tmp.name


def test_import_creates_acao_controle():
    """Importação cria AcaoControle com todas as datas parseadas."""
    # Criar dependências diretamente
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

    # Criar CSV temporário
    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Coordenador": "coord@example.com",
                "Data Entrega": "2025-01-15",
                "Data Carta": "15/01/2025",
                "Contato Inicial": "45677",  # Excel serial for 2025-01-20
                "Data Reunião": "2025-02-01",
                "Observação": "Teste observação",
            }
        ],
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

    report = import_acoes_controle(csv_file, dry_run=False)

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


def test_idempotency_no_duplicates():
    """Rodar ETL 2x não duplica registros (external_hash)."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Data Entrega": "2025-01-15",
            }
        ],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    # Primeira rodada
    report1 = import_acoes_controle(csv_file, dry_run=False)
    assert report1["stats"]["created"] == 1

    # Segunda rodada (idempotência)
    report2 = import_acoes_controle(csv_file, dry_run=False)
    assert report2["stats"]["unchanged"] == 1
    assert report2["stats"]["created"] == 0

    # Total de registros permanece 1
    assert AcaoControle.objects.count() == 1


def test_dry_run_does_not_commit():
    """Dry-run não persiste dados no banco."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Data Entrega": "2025-01-15",
            }
        ],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=True)

    assert report["stats"]["created"] == 1
    assert report["dry_run"] is True

    # Banco está vazio (rollback)
    assert AcaoControle.objects.count() == 0


def test_skip_missing_municipio():
    """Registros com município inexistente são pulados."""
    Projeto.objects.create(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Município Inexistente",
                "Projeto": "ACerta",
                "Data Entrega": "2025-01-01",
            }
        ],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=False)

    assert report["stats"]["created"] == 0
    assert report["stats"]["skipped"]["municipio"] == 1

    pendencias = report["pendencias"]["municipios"]
    assert len(pendencias) == 1
    assert pendencias[0]["nome"] == "Município Inexistente"


def test_report_saved_to_out_etl():
    """Relatório é salvo em out_etl/import_acoes_controle_report.json."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Data Entrega": "2025-01-15",
            }
        ],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    import_acoes_controle(csv_file, dry_run=False)

    report_path = Path(settings.BASE_DIR) / "out_etl" / "import_acoes_controle_report.json"
    assert report_path.exists()

    # Validar conteúdo do relatório
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "stats" in report
    assert "pendencias" in report
    assert "file" in report
    assert report["stats"]["created"] >= 0


def test_coordenador_optional():
    """Coordenador é opcional - registro criado mesmo se não encontrado."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Data Entrega": "2025-01-01",
            }
        ],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=False)

    assert report["stats"]["created"] == 1

    acao = AcaoControle.objects.first()
    assert acao.coordenador is None  # Opcional, não bloqueia criação


def test_update_existing_record():
    """Atualiza registro existente se dados mudarem."""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    # Criar inicial
    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Data Entrega": "2025-01-01",
                "Observação": "Versão 1",
            }
        ],
        fieldnames=["Município", "Projeto", "Data Entrega", "Observação"],
    )

    report1 = import_acoes_controle(csv_file, dry_run=False)
    assert report1["stats"]["created"] == 1

    # Atualizar observação
    csv_file2 = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Data Entrega": "2025-01-01",
                "Observação": "Versão 2 - atualizada",
            }
        ],
        fieldnames=["Município", "Projeto", "Data Entrega", "Observação"],
    )

    report2 = import_acoes_controle(csv_file2, dry_run=False)
    assert report2["stats"]["updated"] == 1

    acao = AcaoControle.objects.first()
    assert acao.observacao == "Versão 2 - atualizada"
    assert AcaoControle.objects.count() == 1  # Não duplicou
