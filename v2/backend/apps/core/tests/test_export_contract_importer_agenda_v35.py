"""Agenda do export v35 no importer do export-contract (decisões do dono, 05/10/2026).

- `disciplina`: Superativar/ACerta (agrupadores) com disciplina única vão para o projeto da disciplina;
  disciplina dupla, vazia ou público ficam no agrupador (P8).
- `cancelado=true`: linha nova nasce `reprovado` (não existe "cancelado" no modelo) e fica no AuditLog.
- `evento_ids_anteriores`: id antigo já gravado em `external_hash` = mesmo evento. Não cria de novo;
  re-chaveia o `external_hash` para o id novo, sem tocar status/data.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.core.models import AuditLog, Municipio, TipoEvento
from apps.core.models.solicitacao import Solicitacao
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_FORTALEZA = ZoneInfo("America/Fortaleza")

_COLS = [
    "evento_id",
    "municipio",
    "uf",
    "projeto",
    "tipo_evento",
    "data",
    "hora_inicio",
    "hora_fim",
    "segmento",
    "solicitante_cpf",
    "disciplina",
    "cancelado",
    "evento_ids_anteriores",
]


def _row(**kw: str) -> dict[str, str]:
    base = {
        "evento_id": "EV900001",
        "municipio": "Cidade X",
        "uf": "CE",
        "projeto": "Projeto X",
        "tipo_evento": "Formacao",
        "data": "2026-11-10",
        "hora_inicio": "09:00",
        "hora_fim": "12:00",
        "segmento": "3º ano",
        "solicitante_cpf": "11144477735",
        "disciplina": "",
        "cancelado": "",
        "evento_ids_anteriores": "[]",
    }
    base.update(kw)
    return base


def _write_export(tmp_path, rows: list[dict[str, str]]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=_COLS)
    w.writeheader()
    w.writerows(rows)
    (d / "solicitacao.csv").write_text(buf.getvalue(), encoding="utf-8")
    manifest: dict[str, Any] = {"entities": {"solicitacao": {"file_csv": "solicitacao.csv", "rows": len(rows)}}}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _apply(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()


@pytest.fixture
def masters():
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    TipoEventoFactory(nome="Formacao")
    UsuarioFactory(username="coord1", cpf="11144477735", email="coord1@example.invalid")
    nomes = [
        "Projeto X",
        "Superativar",
        "Superativar Linguagens",
        "Superativar Matemática",
        "ACerta",
        "ACerta Português",
        "ACerta Matemática",
    ]
    return {n: ProjetoFactory(nome=n, fluxo="NAO_SUPER") for n in nomes}


# ---------- disciplina ----------
@pytest.mark.parametrize(
    ("agrupador", "disciplina", "esperado"),
    [
        ("Superativar", "LING", "Superativar Linguagens"),
        ("Superativar", "MAT", "Superativar Matemática"),
        ("ACerta", "LING", "ACerta Português"),
        ("ACerta", "MAT", "ACerta Matemática"),
    ],
)
def test_agrupador_com_disciplina_unica_vai_para_o_projeto_da_disciplina(
    tmp_path, masters, agrupador, disciplina, esperado
):
    path = _write_export(tmp_path, [_row(projeto=agrupador, disciplina=disciplina)])
    _apply(path)
    assert Solicitacao.objects.get().projeto.nome == esperado


@pytest.mark.parametrize("agrupador", ["Superativar", "ACerta"])
@pytest.mark.parametrize("disciplina", ["LING-MAT", ""])
def test_agrupador_com_disciplina_dupla_ou_vazia_fica_no_agrupador(tmp_path, masters, agrupador, disciplina):
    path = _write_export(tmp_path, [_row(projeto=agrupador, disciplina=disciplina)])
    _apply(path)
    assert Solicitacao.objects.get().projeto.nome == agrupador


def test_disciplina_nao_mexe_em_outro_projeto(tmp_path, masters):
    path = _write_export(tmp_path, [_row(projeto="Projeto X", disciplina="MAT")])
    _apply(path)
    assert Solicitacao.objects.get().projeto.nome == "Projeto X"


# ---------- cancelado ----------
def test_linha_nova_cancelada_nasce_reprovada_e_fica_no_auditlog(tmp_path, masters):
    path = _write_export(tmp_path, [_row(cancelado="true")])
    r = _apply(path)
    sol = Solicitacao.objects.get()
    assert sol.status == Solicitacao.Status.REPROVADO, "cancelado na planilha nunca entra pendente/aprovado"
    assert r["applied"]["solicitacao__cancelada_reprovada"] == 1
    log = AuditLog.objects.get(action=AuditLog.Action.REJECT, model_name="Solicitacao")
    assert log.details["solicitacao_id"] == sol.id
    assert log.details["motivo"] == "cancelado_na_planilha"


def test_linha_nao_cancelada_segue_o_status_de_hoje(tmp_path, masters):
    path = _write_export(tmp_path, [_row(cancelado="false")])
    _apply(path)
    assert Solicitacao.objects.get().status == Solicitacao.Status.APROVADO, "NAO_SUPER → aprovado"
    assert not AuditLog.objects.filter(action=AuditLog.Action.REJECT).exists()


# ---------- id antigo ----------
def _sol_existente(masters, ext_hash: str, status: str) -> Solicitacao:
    inicio = timezone.make_aware(datetime(2026, 9, 8, 8, 0), _FORTALEZA)
    fim = timezone.make_aware(datetime(2026, 9, 8, 12, 0), _FORTALEZA)
    coord = UsuarioFactory(username="coord_antigo", cpf="22255588846", email="antigo@example.invalid")
    return Solicitacao.objects.create(
        usuario=coord,
        coordenador=coord,
        municipio=Municipio.objects.get(),
        projeto=masters["Projeto X"],
        tipo_evento=TipoEvento.objects.get(),
        inicio=inicio,
        fim=fim,
        status=status,
        external_hash=ext_hash,
    )


def test_id_antigo_existente_nao_duplica_e_rechaveia(tmp_path, masters):
    antiga = _sol_existente(masters, "EV000100", Solicitacao.Status.APROVADO)
    inicio, fim = antiga.inicio, antiga.fim
    path = _write_export(tmp_path, [_row(evento_id="EV900100", evento_ids_anteriores='["EV000100"]', cancelado="true")])
    r = _apply(path)
    assert Solicitacao.objects.count() == 1, "id antigo já em prod = mesmo evento, não cria de novo"
    antiga.refresh_from_db()
    assert antiga.external_hash == "EV900100", "re-chaveia para as próximas cargas acharem"
    assert antiga.status == Solicitacao.Status.APROVADO, "status protegido (nem o cancelado da linha mexe)"
    assert (antiga.inicio, antiga.fim) == (inicio, fim), "data não muda"
    assert r["applied"]["solicitacao"] == 0
    assert r["applied"]["solicitacao__rechaveada"] == 1
    log = AuditLog.objects.get(action=AuditLog.Action.UPDATE, model_name="Solicitacao")
    assert log.details == {
        "solicitacao_id": antiga.id,
        "origem": "import_export_contract",
        "campo": "external_hash",
        "de": "EV000100",
        "para": "EV900100",
    }


def test_id_antigo_no_dry_run_conta_como_existente(tmp_path, masters):
    _sol_existente(masters, "EV000100", Solicitacao.Status.APROVADO)
    path = _write_export(tmp_path, [_row(evento_id="EV900100", evento_ids_anteriores='["EV000100"]')])
    tally = ExportContractImporter(path=path).run()["por_entidade"]["solicitacao"]
    assert tally["would_create"] == 0
    assert tally["would_skip_same"] == 1
    assert tally["would_rekey"] == 1
    assert Solicitacao.objects.get().external_hash == "EV000100", "dry-run não grava"


def test_id_antigo_que_nao_existe_cria_normalmente(tmp_path, masters):
    path = _write_export(tmp_path, [_row(evento_id="EV900100", evento_ids_anteriores='["EV000999"]')])
    r = _apply(path)
    assert r["applied"]["solicitacao"] == 1
    assert Solicitacao.objects.get().external_hash == "EV900100"
    assert "solicitacao__rechaveada" not in r["applied"]


def test_linha_sem_id_antigo_segue_igual_a_hoje(tmp_path, masters):
    _sol_existente(masters, "EV000100", Solicitacao.Status.APROVADO)
    path = _write_export(tmp_path, [_row(evento_id="EV900100")])
    r = _apply(path)
    assert r["applied"]["solicitacao"] == 1
    assert set(Solicitacao.objects.values_list("external_hash", flat=True)) == {"EV000100", "EV900100"}
