"""
Testes para ETL de AcaoDAT.

Valida:
- Idempotência (rodar 2x não duplica)
- Resolução de FKs (município, projeto, responsável)
- Tipo de ação obrigatório
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

from apps.core.models import AcaoDAT, Municipio, Projeto
from apps.core.services.dat_cadastros_import import import_dat_cadastros


User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_dependencies():
    """Cria dependências necessárias para o ETL."""
    responsavel = User.objects.create_user(
        username="resp1",
        email="resp@example.com",
        password="test123",
        cpf="11111111111",
        first_name="João",
        last_name="Responsável",
    )

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="ACerta", ativo=True)

    return {"responsavel": responsavel, "municipio": municipio, "projeto": projeto}


@pytest.fixture
def csv_valid(tmp_path, setup_dependencies):
    """Cria CSV válido com headers flexíveis."""
    csv_file = tmp_path / "dat_cadastros.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Município",
                "Projeto",
                "Tipo de Ação",
                "Responsável",
                "Data Registro",
                "Observação",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Cadastro INEP",
            "Responsável": "resp@example.com",
            "Data Registro": "2025-01-15",
            "Observação": "Cadastro realizado",
        })

    return str(csv_file)


@pytest.fixture
def csv_missing_tipo_acao(tmp_path, setup_dependencies):
    """CSV sem tipo de ação (obrigatório)."""
    csv_file = tmp_path / "dat_missing_tipo.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Município", "Projeto", "Data Registro"],
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Data Registro": "2025-01-01",
        })

    return str(csv_file)


def test_import_creates_acao_dat(csv_valid):
    """Importação cria AcaoDAT com todos os campos."""
    report = import_dat_cadastros(csv_valid, dry_run=False)

    assert report["stats"]["created"] == 1
    assert report["stats"]["skipped"]["municipio"] == 0
    assert report["dry_run"] is False

    acao = AcaoDAT.objects.first()
    assert acao.municipio.nome == "Fortaleza"
    assert acao.projeto.nome == "ACerta"
    assert acao.tipo_acao == "Cadastro INEP"
    assert acao.responsavel.email == "resp@example.com"
    assert acao.data_registro == date(2025, 1, 15)
    assert acao.observacao == "Cadastro realizado"
    assert acao.external_hash is not None


def test_idempotency_no_duplicates(csv_valid):
    """Rodar ETL 2x não duplica registros (external_hash)."""
    # Primeira rodada
    report1 = import_dat_cadastros(csv_valid, dry_run=False)
    assert report1["stats"]["created"] == 1

    # Segunda rodada (idempotência)
    report2 = import_dat_cadastros(csv_valid, dry_run=False)
    assert report2["stats"]["unchanged"] == 1
    assert report2["stats"]["created"] == 0

    # Total de registros permanece 1
    assert AcaoDAT.objects.count() == 1


def test_dry_run_does_not_commit(csv_valid):
    """Dry-run não persiste dados no banco."""
    report = import_dat_cadastros(csv_valid, dry_run=True)

    assert report["stats"]["created"] == 1
    assert report["dry_run"] is True

    # Banco está vazio (rollback)
    assert AcaoDAT.objects.count() == 0


def test_skip_missing_tipo_acao(csv_missing_tipo_acao):
    """Registros sem tipo de ação são pulados (campo obrigatório)."""
    report = import_dat_cadastros(csv_missing_tipo_acao, dry_run=False)

    assert report["stats"]["created"] == 0
    assert report["stats"]["skipped"]["tipo_acao"] == 1

    pendencias = report["pendencias"]["tipo_acao"]
    assert len(pendencias) == 1


def test_report_saved_to_out_etl(csv_valid):
    """Relatório é salvo em out_etl/import_dat_cadastros_report.json."""
    import_dat_cadastros(csv_valid, dry_run=False)

    report_path = Path(settings.BASE_DIR) / "out_etl" / "import_dat_cadastros_report.json"
    assert report_path.exists()

    # Validar conteúdo do relatório
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "stats" in report
    assert "pendencias" in report
    assert "file" in report
    assert report["stats"]["created"] >= 0


def test_responsavel_optional(tmp_path, setup_dependencies):
    """Responsável é opcional - registro criado mesmo se não encontrado."""
    csv_file = tmp_path / "dat_no_resp.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Município", "Projeto", "Tipo de Ação", "Data Registro"]
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Cadastro SIGPEC",
            "Data Registro": "2025-01-01",
        })

    report = import_dat_cadastros(str(csv_file), dry_run=False)

    assert report["stats"]["created"] == 1

    acao = AcaoDAT.objects.first()
    assert acao.responsavel is None  # Opcional, não bloqueia criação
    assert acao.tipo_acao == "Cadastro SIGPEC"


def test_update_existing_record(tmp_path, setup_dependencies):
    """Atualiza registro existente se dados mudarem."""
    csv_file = tmp_path / "dat_update.csv"

    # Criar inicial
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Município", "Projeto", "Tipo de Ação", "Data Registro", "Observação"],
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Cadastro Teste",
            "Data Registro": "2025-01-01",
            "Observação": "Versão 1",
        })

    report1 = import_dat_cadastros(str(csv_file), dry_run=False)
    assert report1["stats"]["created"] == 1

    # Atualizar observação
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Município", "Projeto", "Tipo de Ação", "Data Registro", "Observação"],
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Cadastro Teste",
            "Data Registro": "2025-01-01",
            "Observação": "Versão 2 - atualizada",
        })

    report2 = import_dat_cadastros(str(csv_file), dry_run=False)
    assert report2["stats"]["updated"] == 1

    acao = AcaoDAT.objects.first()
    assert acao.observacao == "Versão 2 - atualizada"
    assert AcaoDAT.objects.count() == 1  # Não duplicou


def test_external_hash_includes_tipo_acao(tmp_path, setup_dependencies):
    """external_hash inclui tipo_acao, diferenciando ações do mesmo projeto/município/data."""
    csv_file = tmp_path / "dat_multiple.csv"

    # Criar 2 ações diferentes (mesmo município/projeto/data, tipo_acao diferente)
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Município", "Projeto", "Tipo de Ação", "Data Registro"]
        )
        writer.writeheader()
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Cadastro INEP",
            "Data Registro": "2025-01-01",
        })
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Cadastro SIGPEC",
            "Data Registro": "2025-01-01",
        })

    report = import_dat_cadastros(str(csv_file), dry_run=False)

    assert report["stats"]["created"] == 2  # Ambas criadas (hashes diferentes)
    assert AcaoDAT.objects.count() == 2

    acoes = AcaoDAT.objects.all()
    assert acoes[0].external_hash != acoes[1].external_hash  # Hashes diferentes


def test_date_parsing_formats(tmp_path, setup_dependencies):
    """Testa parsing de múltiplos formatos de data."""
    csv_file = tmp_path / "dat_dates.csv"

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Município", "Projeto", "Tipo de Ação", "Data Registro"]
        )
        writer.writeheader()
        # ISO format
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Teste ISO",
            "Data Registro": "2025-01-15",
        })
        # dd/mm/yyyy format
        writer.writerow({
            "Município": "Fortaleza",
            "Projeto": "ACerta",
            "Tipo de Ação": "Teste BR",
            "Data Registro": "20/01/2025",
        })

    report = import_dat_cadastros(str(csv_file), dry_run=False)

    assert report["stats"]["created"] == 2

    # Validar datas parseadas corretamente
    acao_iso = AcaoDAT.objects.get(tipo_acao="Teste ISO")
    assert acao_iso.data_registro == date(2025, 1, 15)

    acao_br = AcaoDAT.objects.get(tipo_acao="Teste BR")
    assert acao_br.data_registro == date(2025, 1, 20)
