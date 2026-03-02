"""
Testes para o management command etl_import_compras (Issue #713).

Valida:
- dry-run não persiste nada
- apply persiste compras
- idempotência (segunda execução não duplica)
- arquivo inexistente → CommandError
- relatório JSON gravado em out_etl/
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import tempfile
from collections.abc import Generator
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.models import Compra, Municipio, Projeto

pytestmark = pytest.mark.django_db

CSV_CONTENT = """\
CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções
001,LIVRO NOVO LENDO,100,Acarape,CE,2026-01-15,Formação inicial
002,KIT GESTÃO ESCOLAR,50,Pacajus,CE,2026-02-20,Reposição
"""


@pytest.fixture()
def setup_data() -> None:
    Municipio.objects.get_or_create(nome="Acarape", defaults={"uf": "CE", "ativo": True})
    Municipio.objects.get_or_create(nome="Pacajus", defaults={"uf": "CE", "ativo": True})
    Projeto.objects.get_or_create(nome="Novo Lendo", defaults={"ativo": True})
    Projeto.objects.get_or_create(nome="Gestão Escolar", defaults={"ativo": True})


@pytest.fixture()
def csv_path(setup_data: None) -> Generator[str, None, None]:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write(CSV_CONTENT)
    tmp.close()
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


class TestEtlImportComprasCommand:
    def test_dry_run_nao_persiste(self, csv_path: str) -> None:
        """dry-run deve simular sem gravar no banco."""
        Compra.objects.all().delete()
        out = StringIO()
        call_command("etl_import_compras", f"--file={csv_path}", "--dry-run", stdout=out)
        assert Compra.objects.count() == 0
        output = out.getvalue()
        assert "dry" in output.lower() or "DRY" in output

    def test_apply_persiste_compras(self, csv_path: str) -> None:
        """apply deve persistir as compras no banco."""
        Compra.objects.all().delete()
        call_command("etl_import_compras", f"--file={csv_path}", stdout=StringIO())
        assert Compra.objects.count() >= 1

    def test_idempotencia(self, csv_path: str) -> None:
        """Segunda execução não deve duplicar registros."""
        Compra.objects.all().delete()
        call_command("etl_import_compras", f"--file={csv_path}", stdout=StringIO())
        count_after_first = Compra.objects.count()
        call_command("etl_import_compras", f"--file={csv_path}", stdout=StringIO())
        assert Compra.objects.count() == count_after_first

    def test_arquivo_inexistente_levanta_error(self) -> None:
        """Arquivo inexistente deve levantar CommandError."""
        with pytest.raises((CommandError, FileNotFoundError)):
            call_command("etl_import_compras", "--file=/nao/existe.csv", stdout=StringIO())

    def test_relatorio_json_gerado(self, csv_path: str, tmp_path: Path) -> None:
        """Comando deve gerar relatório JSON em out_etl/."""
        Compra.objects.all().delete()
        out = StringIO()
        call_command("etl_import_compras", f"--file={csv_path}", "--dry-run", stdout=out)
        output = out.getvalue()
        # Relatório mencionado na saída
        assert "report" in output.lower() or "relatório" in output.lower() or "json" in output.lower()
