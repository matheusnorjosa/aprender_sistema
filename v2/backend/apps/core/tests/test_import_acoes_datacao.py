"""
Testes para o import de Ações → DATAcao (Onda 1, imports órfãos).

O import `import_acoes_controle` foi redirecionado do modelo legacy
`AcaoControle` (que nenhuma tela lê) para o modelo operacional `DATAcao`
(lido pela AcoesPage em `/dat/acoes-ciclo/`). Ver
`v2/docs/plans/PLANO_IMPORTS_ORFAOS.md` (Onda 1).

Valida:
- Cria DATAcao com datas mapeadas + status derivado (tem data → concluído)
- Idempotência pela chave natural (municipio, projeto) — sem external_hash
- Coordenador mapeado para DATCoordenador (email → nome → null)
- created_by obrigatório (DATAcao.created_by é NOT NULL)
- observacao única da origem → observacao_carta
- dry-run não persiste; pendências de município; relatório em out_etl/
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import csv
import json
import tempfile
from datetime import date
from pathlib import Path

from django.conf import settings

import pytest

from apps.core.models import DATAcao, DATCoordenador
from apps.core.services.controle_acoes_import import import_acoes_controle
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

CONCLUIDO = DATAcao.StatusEtapa.CONCLUIDO
PENDENTE = DATAcao.StatusEtapa.PENDENTE


def _create_csv_file(rows, fieldnames):
    """Helper para criar arquivo CSV temporário."""
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8", newline="")
    writer = csv.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    tmp.close()
    return tmp.name


def _actor():
    """Usuário-serviço para created_by (o endpoint passa request.user)."""
    return UsuarioFactory(
        username="importador",
        email="importador@example.com",
        password="test123",
        cpf="11144477735",
        first_name="Serviço",
        last_name="Import",
    )


def _coordenador(actor, *, nome="Maria Silva", email="coord@example.com"):
    return DATCoordenador.objects.create(nome=nome, email=email, area="DAT", created_by=actor)


def test_import_creates_datacao_with_derived_status():
    """Importação cria DATAcao com datas mapeadas e status derivado por etapa."""
    actor = _actor()
    coord = _coordenador(actor)
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Coordenador": "coord@example.com",
                "Data Entrega": "2025-01-15",
                "Data Carta": "15/01/2025",
                "Contato Inicial": "45677",  # Excel serial → 2025-01-20
                "Data Reunião": "",  # sem data → etapa pendente
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

    report = import_acoes_controle(csv_file, dry_run=False, created_by=actor)

    assert report["stats"]["created"] == 1
    assert report["stats"]["skipped"]["municipio"] == 0
    assert report["dry_run"] is False

    acao = DATAcao.objects.get()
    assert acao.municipio.nome == "Fortaleza"
    assert acao.projeto.nome == "ACerta"
    assert acao.coordenador_id == coord.id
    assert acao.created_by_id == actor.id
    # Datas mapeadas (contato_inicial → data_contato)
    assert acao.data_carta == date(2025, 1, 15)
    assert acao.data_contato == date(2025, 1, 20)
    assert acao.data_reuniao is None
    assert acao.data_entrega == date(2025, 1, 15)
    # Status derivado: tem data → concluído; sem data → pendente
    assert acao.status_carta == CONCLUIDO
    assert acao.status_contato == CONCLUIDO
    assert acao.status_reuniao == PENDENTE
    assert acao.status_entrega == CONCLUIDO
    # Observação única da origem vai para a 1ª etapa
    assert acao.observacao_carta == "Teste observação"


def test_idempotency_no_duplicates():
    """Rodar 2x não duplica (chave natural municipio+projeto)."""
    actor = _actor()
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[{"Município": "Fortaleza", "Projeto": "ACerta", "Data Entrega": "2025-01-15"}],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report1 = import_acoes_controle(csv_file, dry_run=False, created_by=actor)
    assert report1["stats"]["created"] == 1

    report2 = import_acoes_controle(csv_file, dry_run=False, created_by=actor)
    assert report2["stats"]["unchanged"] == 1
    assert report2["stats"]["created"] == 0

    assert DATAcao.objects.count() == 1


def test_dry_run_does_not_commit():
    """Dry-run não persiste (rollback)."""
    actor = _actor()
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[{"Município": "Fortaleza", "Projeto": "ACerta", "Data Entrega": "2025-01-15"}],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=True, created_by=actor)

    assert report["stats"]["created"] == 1
    assert report["dry_run"] is True
    assert DATAcao.objects.count() == 0


def test_created_by_required():
    """DATAcao.created_by é NOT NULL → import sem created_by falha explicitamente."""
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)
    csv_file = _create_csv_file(
        rows=[{"Município": "Fortaleza", "Projeto": "ACerta", "Data Entrega": "2025-01-15"}],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    with pytest.raises(ValueError):
        import_acoes_controle(csv_file, dry_run=False)


def test_coordenador_matched_by_email():
    """Coordenador da origem casa com DATCoordenador por email."""
    actor = _actor()
    coord = _coordenador(actor, nome="João", email="joao@dat.com")
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {"Município": "Fortaleza", "Projeto": "ACerta", "Coordenador": "joao@dat.com", "Data Entrega": "2025-01-15"}
        ],
        fieldnames=["Município", "Projeto", "Coordenador", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=False, created_by=actor)
    assert report["stats"]["created"] == 1
    assert DATAcao.objects.get().coordenador_id == coord.id


def test_coordenador_optional_null_when_unmatched():
    """Coordenador não encontrado → DATAcao.coordenador null, ainda cria."""
    actor = _actor()
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[
            {
                "Município": "Fortaleza",
                "Projeto": "ACerta",
                "Coordenador": "naoexiste@dat.com",
                "Data Entrega": "2025-01-15",
            }
        ],
        fieldnames=["Município", "Projeto", "Coordenador", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=False, created_by=actor)
    assert report["stats"]["created"] == 1
    assert DATAcao.objects.get().coordenador is None


def test_skip_missing_municipio():
    """Município inexistente é pulado com pendência."""
    actor = _actor()
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[{"Município": "Município Inexistente", "Projeto": "ACerta", "Data Entrega": "2025-01-01"}],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=False, created_by=actor)

    assert report["stats"]["created"] == 0
    assert report["stats"]["skipped"]["municipio"] == 1
    assert DATAcao.objects.count() == 0
    pendencias = report["pendencias"]["municipios"]
    assert len(pendencias) == 1
    assert pendencias[0]["nome"] == "Município Inexistente"


def test_update_existing_record():
    """Atualiza a mesma DATAcao (municipio+projeto) se dados mudarem."""
    actor = _actor()
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[{"Município": "Fortaleza", "Projeto": "ACerta", "Observação": "Versão 1"}],
        fieldnames=["Município", "Projeto", "Observação"],
    )
    report1 = import_acoes_controle(csv_file, dry_run=False, created_by=actor)
    assert report1["stats"]["created"] == 1

    csv_file2 = _create_csv_file(
        rows=[{"Município": "Fortaleza", "Projeto": "ACerta", "Data Reunião": "2025-02-01", "Observação": "Versão 2"}],
        fieldnames=["Município", "Projeto", "Data Reunião", "Observação"],
    )
    report2 = import_acoes_controle(csv_file2, dry_run=False, created_by=actor)
    assert report2["stats"]["updated"] == 1

    acao = DATAcao.objects.get()
    assert acao.observacao_carta == "Versão 2"
    assert acao.data_reuniao == date(2025, 2, 1)
    assert acao.status_reuniao == CONCLUIDO  # ganhou data → concluído
    assert acao.updated_by_id == actor.id
    assert DATAcao.objects.count() == 1


def test_municipio_with_accent_resolves():
    """Regression: município acentuado no DB casa com entrada acentuada."""
    actor = _actor()
    MunicipioFactory(nome="Iguatú", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[{"Município": "Iguatú", "Projeto": "ACerta", "Data Entrega": "2026-01-15"}],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=False, created_by=actor)
    assert report["stats"]["created"] == 1
    assert report["stats"]["skipped"]["municipio"] == 0
    assert DATAcao.objects.count() == 1


def test_municipio_cidade_uf_format_resolves():
    """Município no formato 'CIDADE-UF' é desambiguado pelo resolver."""
    actor = _actor()
    MunicipioFactory(nome="Curvelo", uf="MG", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[{"Município": "CURVELO-MG", "Projeto": "ACerta", "Data Entrega": "2026-01-15"}],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    report = import_acoes_controle(csv_file, dry_run=False, created_by=actor)
    assert report["stats"]["created"] == 1
    assert DATAcao.objects.count() == 1


def test_report_saved_to_out_etl():
    """Relatório é salvo em out_etl/import_acoes_controle_report.json."""
    actor = _actor()
    MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    ProjetoFactory(nome="ACerta", ativo=True)

    csv_file = _create_csv_file(
        rows=[{"Município": "Fortaleza", "Projeto": "ACerta", "Data Entrega": "2025-01-15"}],
        fieldnames=["Município", "Projeto", "Data Entrega"],
    )

    import_acoes_controle(csv_file, dry_run=False, created_by=actor)

    report_path = Path(settings.BASE_DIR) / "out_etl" / "import_acoes_controle_report.json"
    assert report_path.exists()
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    assert "stats" in report
    assert "pendencias" in report
    assert "file" in report
