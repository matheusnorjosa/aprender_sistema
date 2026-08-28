"""
#1895 — handler export-contract de `equipe_gerencia` (classify + apply).

Primeiro NOT_IMPLEMENTED do dry-run v15. Reusa os helpers do serviço de upload existente
(`equipe_gerencia_import`: _get_or_create_gerencia / _resolve_usuario / _resolve_papel).
Contrato:
- classify: conta would_create/would_skip por NK (gerencia, usuario, papel), FK não-resolvida = reject;
- apply (create-only, --allow equipe_gerencia): cria EquipeGerencia com valid_from=hoje / valid_to=None;
- popula `Gerencia.setor_canonico` do row (vocabulário de produto, do de-para) — o fio de leitura do #1893.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportCallIssue=false

from __future__ import annotations

import json

import pytest

from apps.core.models import EquipeGerencia, Gerencia
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CSV = "gerencia,usuario_cpf,papel,setor_canonico\nVidas,10000005673,COORDENADOR,GESTÃO ESCOLAR\n"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict = {"generated_at": "x", "snapshot_date": "y", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv"}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


class TestEquipeGerenciaClassify:
    def test_classify_is_implemented_not_placeholder(self, tmp_path):
        Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
        UsuarioFactory(cpf="10000005673")
        path = _write_export(tmp_path, {"equipe_gerencia": _CSV})

        report = ExportContractImporter(path=path).run()
        pe = report["por_entidade"]["equipe_gerencia"]

        assert pe.get("status") != "not_implemented", "equipe_gerencia deve classificar, não ser placeholder"
        assert pe.get("would_create") == 1


class TestEquipeGerenciaApply:
    def test_apply_creates_vinculo_with_vigencia_and_setor_canonico(self, tmp_path):
        g = Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
        u = UsuarioFactory(cpf="10000005673")
        path = _write_export(tmp_path, {"equipe_gerencia": _CSV})

        ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

        v = EquipeGerencia.objects.filter(gerencia=g, usuario=u, papel="COORDENADOR").first()
        assert v is not None, "apply deve criar o vínculo"
        assert v.valid_from is not None, "vigência = data do import"
        assert v.valid_to is None
        g.refresh_from_db()
        assert g.setor_canonico == "GESTÃO ESCOLAR", "setor_canonico vem do row (de-para), não derivado"

    def test_apply_is_idempotent(self, tmp_path):
        Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
        UsuarioFactory(cpf="10000005673")
        path = _write_export(tmp_path, {"equipe_gerencia": _CSV})

        ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()
        ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()

        assert EquipeGerencia.objects.filter(papel="COORDENADOR").count() == 1, "2ª run não duplica"
