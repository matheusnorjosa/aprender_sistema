"""
Tipo de evento e área do DAT com a mesma chave do município (ISS-1658 b, Refs #1658).

O classify de `tipo_evento` e `dat_area` casa pelo nome sem acento e sem caixa (`_norm`), mas o apply criava por
`nome__iexact`, que distingue acento: 'Formacao' no pacote dizia would_skip_same no ensaio e criava a cópia ao lado de
'Formação' no apply. E o índice de tipo de evento (usado também pela solicitação) era um dict que deixava o último
registro vencer quando duas grafias convivem no banco. Agora o apply usa o mesmo índice do classify, e a chave repetida
no cadastro para a carga com as ids, como o município (#2210).

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from apps.core.models import DATArea, TipoEvento
from apps.core.services.export_contract_importer import ExportContractImporter

pytestmark = pytest.mark.django_db

TIPO_HEADER = "nome,descricao,cor"
AREA_HEADER = "nome"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-11-12", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def test_grafia_sem_acento_nao_recria_o_tipo_de_evento(tmp_path):
    TipoEvento.objects.create(nome="Formação", cor="#111111")
    path = _write_export(tmp_path, {"tipo_evento": f"{TIPO_HEADER}\nFormacao,,#111111\n"})

    seco = ExportContractImporter(path=path).run()["por_entidade"]["tipo_evento"]
    r = ExportContractImporter(path=path, apply=True, allow=("tipo_evento",)).run()

    assert seco["would_skip_same"] == 1
    assert r["applied"]["tipo_evento"] == 0
    assert TipoEvento.objects.count() == 1


def test_grafia_sem_acento_nao_recria_a_area_do_dat(tmp_path):
    DATArea.objects.create(nome="Gestão")
    path = _write_export(tmp_path, {"dat_area": f"{AREA_HEADER}\nGestao\n"})

    seco = ExportContractImporter(path=path).run()["por_entidade"]["dat_area"]
    r = ExportContractImporter(path=path, apply=True, allow=("dat_area",)).run()

    assert seco["would_skip_same"] == 1
    assert r["applied"]["dat_area"] == 0
    assert DATArea.objects.count() == 1


def test_duas_grafias_no_mesmo_csv_criam_um_tipo_e_uma_area(tmp_path):
    path = _write_export(
        tmp_path,
        {
            "tipo_evento": f"{TIPO_HEADER}\nFormação,,\nFormacao,,\n",
            "dat_area": f"{AREA_HEADER}\nGestão\nGestao\n",
        },
    )

    r = ExportContractImporter(path=path, apply=True, allow=("tipo_evento", "dat_area")).run()

    assert (r["applied"]["tipo_evento"], r["applied"]["dat_area"]) == (1, 1)
    assert (TipoEvento.objects.count(), DATArea.objects.count()) == (1, 1)


def test_tipo_de_evento_repetido_no_cadastro_para_a_carga_e_lista_as_ids(tmp_path):
    a = TipoEvento.objects.create(nome="Formação")
    b = TipoEvento.objects.create(nome="Formacao")
    path = _write_export(tmp_path, {"tipo_evento": f"{TIPO_HEADER}\nOficina,,\n"})

    with pytest.raises(ValueError, match="tipo de evento repetido no cadastro") as exc:
        ExportContractImporter(path=path).run()

    assert f"t{a.pk}" in str(exc.value) and f"t{b.pk}" in str(exc.value)


def test_area_do_dat_repetida_no_cadastro_para_a_carga_sem_gravar(tmp_path):
    a = DATArea.objects.create(nome="Gestão")
    b = DATArea.objects.create(nome="GESTAO")
    path = _write_export(tmp_path, {"dat_area": f"{AREA_HEADER}\nNova\n"})

    with pytest.raises(ValueError, match="área do DAT repetida no cadastro") as exc:
        ExportContractImporter(path=path, apply=True, allow=("dat_area",)).run()

    assert f"a{a.pk}" in str(exc.value) and f"a{b.pk}" in str(exc.value)
    assert not DATArea.objects.filter(nome="Nova").exists()


def test_comando_mostra_o_tipo_repetido_como_erro_do_comando(tmp_path):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    TipoEvento.objects.create(nome="Formação")
    TipoEvento.objects.create(nome="FORMACAO")
    path = _write_export(tmp_path, {"tipo_evento": f"{TIPO_HEADER}\nOficina,,\n"})

    with pytest.raises(CommandError, match="tipo de evento repetido no cadastro"):
        call_command("import_export_contract", path=path, stdout=io.StringIO())
