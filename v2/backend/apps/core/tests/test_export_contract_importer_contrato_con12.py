"""CON-12: o importador confere se o pacote da planilha veio inteiro antes de gravar.

- BOM no começo do CSV ou do manifest.json é aceito (utf-8-sig); sem BOM nada muda.
- Coluna obrigatória que falta: `usuario` em qualquer modo; `solicitacao` e `participation` só na virada.
- Arquivo que falta: o declarado no manifest, o da entidade do `--allow-entity` e, na virada,
  solicitacao.csv e participation.csv.
- `report["contrato_faltando"]` traz só nomes de arquivo e coluna. Com falta, nada é gravado, e o comando
  termina com erro (também com --json e no dry-run). `contrato_versao` só aparece na saída de texto.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false

from __future__ import annotations

import csv
import io
import json
from typing import Any

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.models import DATArea, Usuario
from apps.core.models.solicitacao import Participation, Solicitacao
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.test_export_contract_importer_virada import (  # noqa: F401 (fixtures)
    _CPF_COORD,
    _CPF_F1,
    _PART_COLS,
    _SOL_COLS,
    _part,
    _sol,
    hoje_fixo,
    m,
)

pytestmark = pytest.mark.django_db

_SEM_FALTA = {"arquivos": [], "colunas": {}}


def _csv(cols: list[str], rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def _pacote(
    tmp_path,
    *,
    sol_cols: list[str] | None = _SOL_COLS,
    part_cols: list[str] | None = _PART_COLS,
    manifest: dict[str, Any] | None = None,
) -> str:
    """Pacote da virada com um evento e um formador. `None` nas colunas = o arquivo não vem."""
    d = tmp_path / "pacote"
    d.mkdir()
    entities: dict[str, Any] = {}
    if sol_cols is not None:
        (d / "solicitacao.csv").write_text(_csv(sol_cols, [_sol()]), encoding="utf-8")
        entities["solicitacao"] = {"file_csv": "solicitacao.csv", "rows": 1}
    if part_cols is not None:
        (d / "participation.csv").write_text(_csv(part_cols, [_part("EV1")]), encoding="utf-8")
        entities["participation"] = {"file_csv": "participation.csv", "rows": 1}
    m_json = manifest if manifest is not None else {"entities": entities}
    (d / "manifest.json").write_text(json.dumps(m_json), encoding="utf-8")
    return str(d)


def _arquivos(tmp_path, files: dict[str, str], manifest: dict[str, Any] | None = None) -> str:
    d = tmp_path / "export"
    d.mkdir()
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
    entities = {name: {"file_csv": f"{name}.csv"} for name in files}
    (d / "manifest.json").write_text(json.dumps(manifest or {"entities": entities}), encoding="utf-8")
    return str(d)


def _sem(cols: list[str], *fora: str) -> list[str]:
    return [c for c in cols if c not in fora]


def _comando(path: str, **opts: Any) -> tuple[str, CommandError | None]:
    out = io.StringIO()
    try:
        call_command("import_export_contract", path=path, stdout=out, **opts)
    except CommandError as e:
        return out.getvalue(), e
    return out.getvalue(), None


# ---------- BOM ----------
def test_bom_no_csv_nao_some_com_a_primeira_coluna(tmp_path):
    path = _arquivos(tmp_path, {"dat_area": "﻿nome,descricao\nArea Nova A,d\nArea Nova B,d\n"})
    r = ExportContractImporter(path=path).run()
    assert r["por_entidade"]["dat_area"]["would_create"] == 2
    assert r["por_entidade"]["dat_area"]["would_reject"] == 0
    assert r["contrato_faltando"] == _SEM_FALTA


def test_bom_no_cabecalho_nao_vira_coluna_faltando(tmp_path):
    """Fila do CON-12 (d): a conferência das colunas lê o cabeçalho com utf-8-sig; com BOM, `cpf` não some."""
    path = _arquivos(tmp_path, {"usuario": "﻿cpf,email,nome_completo\n"})
    r = ExportContractImporter(path=path).run()
    assert r["contrato_faltando"] == _SEM_FALTA


def test_bom_no_manifest_e_lido(tmp_path):
    path = _arquivos(tmp_path, {"dat_area": "nome,descricao\nA,d\n"})
    manifest = {"snapshot_date": "2026-11-10", "entities": {"dat_area": {"file_csv": "dat_area.csv"}}}
    (tmp_path / "export" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8-sig")
    r = ExportContractImporter(path=path).run()
    assert r["manifest"]["snapshot_date"] == "2026-11-10"


# ---------- colunas obrigatórias na virada ----------
def test_virada_sem_cancelado_aponta_a_coluna_e_segue_classificando(tmp_path, m):
    path = _pacote(tmp_path, sol_cols=_sem(_SOL_COLS, "cancelado"))
    r = ExportContractImporter(path=path, mode="virada").run()
    assert r["contrato_faltando"] == {"arquivos": [], "colunas": {"solicitacao": ["cancelado"]}}
    assert r["por_entidade"]["solicitacao"]["export_rows"] == 1


@pytest.mark.parametrize(
    "coluna",
    ["cancelado", "projetos", "na_agenda_google", "external_event_id", "evento_ids_anteriores", "disciplina"],
)
def test_virada_coluna_de_solicitacao_que_passava_calada(tmp_path, m, coluna):
    path = _pacote(tmp_path, sol_cols=_sem(_SOL_COLS, coluna))
    r = ExportContractImporter(path=path, mode="virada").run()
    assert r["contrato_faltando"]["colunas"] == {"solicitacao": [coluna]}


def test_virada_apply_com_falta_nao_grava_nada(tmp_path, m):
    path = _pacote(tmp_path, sol_cols=_sem(_SOL_COLS, "cancelado"))
    r = ExportContractImporter(path=path, mode="virada", apply=True, allow=("solicitacao", "participation")).run()
    assert r["applied"] == {}
    assert Solicitacao.objects.count() == 0
    assert Participation.objects.count() == 0


def test_virada_apply_sem_falta_grava(tmp_path, m):
    """Controle positivo: o mesmo pacote, inteiro, grava."""
    path = _pacote(tmp_path)
    r = ExportContractImporter(path=path, mode="virada", apply=True, allow=("solicitacao", "participation")).run()
    assert r["contrato_faltando"] == _SEM_FALTA
    assert Solicitacao.objects.count() == 1


@pytest.mark.parametrize("coluna", ["role", "match_procedencia", "usuario", "usuario_email"])
def test_virada_participation_sem_coluna_obrigatoria(tmp_path, m, coluna):
    path = _pacote(tmp_path, part_cols=_sem(_PART_COLS, coluna))
    r = ExportContractImporter(path=path, mode="virada").run()
    assert r["contrato_faltando"]["colunas"] == {"participation": [coluna]}


# ---------- arquivos que faltam ----------
def test_virada_dry_run_sem_participation_csv(tmp_path, m):
    path = _pacote(tmp_path, part_cols=None)
    r = ExportContractImporter(path=path, mode="virada").run()
    assert r["contrato_faltando"] == {"arquivos": ["participation.csv"], "colunas": {}}


def test_manifest_declara_arquivo_que_nao_existe(tmp_path):
    entities = {
        "dat_area": {"file_csv": "dat_area.csv"},
        "participation": {"file_csv": "participation.csv"},
    }
    path = _arquivos(tmp_path, {"dat_area": "nome,descricao\nA,d\n"}, manifest={"entities": entities})
    r = ExportContractImporter(path=path).run()
    assert r["contrato_faltando"] == {"arquivos": ["participation.csv"], "colunas": {}}


def test_pacote_sem_manifest_e_fora_do_contrato_e_nao_grava(tmp_path):
    """Fila do CON-12 (b): sem o manifest.json (ou --path errado) o pacote não é reconhecido; antes passava calado."""
    import os

    path = _arquivos(tmp_path, {"dat_area": "nome,descricao\nArea Sem Manifest,d\n"})
    os.remove(os.path.join(path, "manifest.json"))

    r = ExportContractImporter(path=path, apply=True, allow=("dat_area",)).run()

    assert r["contrato_faltando"]["arquivos"] == ["manifest.json"]
    assert r["applied"] == {}
    assert not DATArea.objects.filter(nome="Area Sem Manifest").exists()


def test_allow_entity_sem_o_csv_e_recusado(tmp_path):
    path = _arquivos(tmp_path, {"dat_area": "nome,descricao\nArea Nova,d\n"})
    antes = Usuario.objects.count()
    r = ExportContractImporter(path=path, apply=True, allow=("usuario", "dat_area")).run()
    assert r["contrato_faltando"]["arquivos"] == ["usuario.csv"]
    assert r["applied"] == {}
    assert Usuario.objects.count() == antes
    assert not DATArea.objects.filter(nome="Area Nova").exists()


# ---------- sem falso positivo ----------
def test_create_only_com_solicitacao_legada_nao_acusa_falta(tmp_path):
    legado = ["evento_id", "municipio", "uf", "projeto", "tipo_evento", "data", "hora_inicio", "hora_fim"]
    path = _arquivos(tmp_path, {"solicitacao": _csv(legado, [_sol()]), "participation": "evento_id,role\n"})
    r = ExportContractImporter(path=path).run()
    assert r["contrato_faltando"] == _SEM_FALTA


def test_coluna_a_mais_nao_e_falta(tmp_path, m):
    path = _pacote(tmp_path)  # _SOL_COLS traz `aprovado`, que o importador não lê
    r = ExportContractImporter(path=path, mode="virada").run()
    assert r["contrato_faltando"] == _SEM_FALTA
    assert "aprovado" in r["por_entidade"]["solicitacao"]["ignored_fields"]


# ---------- comando ----------
def test_comando_dry_run_virada_com_falta_termina_com_erro(tmp_path, m):
    path = _pacote(tmp_path, sol_cols=_sem(_SOL_COLS, "cancelado"))
    out, erro = _comando(path, mode="virada")
    assert erro is not None
    assert "solicitacao: cancelado" in str(erro)
    assert "o --apply recusa" in str(erro)
    assert "[solicitacao] rows=" in out
    assert "ERRO" in out


def test_comando_json_imprime_o_relatorio_inteiro_antes_do_erro(tmp_path, m):
    path = _pacote(tmp_path, sol_cols=_sem(_SOL_COLS, "cancelado"))
    out, erro = _comando(path, mode="virada", json=True)
    assert erro is not None
    assert json.loads(out)["contrato_faltando"]["colunas"] == {"solicitacao": ["cancelado"]}


def test_comando_apply_usuario_sem_email_nao_grava(tmp_path):
    path = _arquivos(tmp_path, {"usuario": f"nome_completo,cpf\nPessoa Teste,{_CPF_COORD}\n"})
    antes = Usuario.objects.count()
    _, erro = _comando(path, apply=True, allow=["usuario"])
    assert erro is not None
    assert "usuario: email" in str(erro)
    assert "nada gravado" in str(erro)
    assert Usuario.objects.count() == antes


def test_comando_mostra_contrato_versao_sem_conferir(tmp_path):
    manifest = {"contrato_versao": "v40", "entities": {"dat_area": {"file_csv": "dat_area.csv"}}}
    path = _arquivos(tmp_path, {"dat_area": "nome,descricao\nA,d\n"}, manifest=manifest)
    out, erro = _comando(path)
    assert erro is None
    assert "contrato_versao=v40" in out


def test_comando_sem_contrato_versao_diz_ausente_e_nao_falha(tmp_path):
    path = _arquivos(tmp_path, {"dat_area": "nome,descricao\nA,d\n"})
    out, erro = _comando(path)
    assert erro is None
    assert "contrato_versao=ausente" in out


def test_sem_dado_pessoal_no_erro_nem_no_relatorio(tmp_path, m):
    path = _pacote(tmp_path, part_cols=_sem(_PART_COLS, "role"))
    out, erro = _comando(path, mode="virada", json=True)
    assert erro is not None
    falta = json.dumps(json.loads(out)["contrato_faltando"])
    for dado in (_CPF_F1, _CPF_COORD, "example.invalid"):
        assert dado not in str(erro)
        assert dado not in falta
