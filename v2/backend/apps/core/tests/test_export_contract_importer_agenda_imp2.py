"""IMP-2: agenda e participação no importer do export-contract (decisões do dono, 14/10/2026).

- Participação só vincula pessoa a evento CRIADO NESTA EXECUÇÃO. Evento que já existia (ou que foi
  re-chaveado por `evento_ids_anteriores`) não ganha nem perde participante: a virada cuida disso.
- Evento NOVO com data passada (antes de hoje em Fortaleza) não é criado; fica para a virada. Evento de
  hoje entra. Evento existente passado segue como antes (reconcile e re-chave intactos).
- O comando barra `participation` na allowlist sem `solicitacao`.
- O dry-run espelha o apply: passado novo e participação de evento existente viram skip com motivo, e
  o contador `rekey_contraditorio` mostra o id antigo que também é id próprio de outra linha.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

import pytest

from apps.core.models import Municipio, TipoEvento, Usuario
from apps.core.models.solicitacao import Participation, Solicitacao
from apps.core.services import export_contract_importer
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_FORTALEZA = ZoneInfo("America/Fortaleza")
HOJE = date(2026, 10, 14)
ONTEM = "2026-10-13"
AMANHA = "2026-10-15"

_SOL_COLS = [
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
    "cancelado",
    "evento_ids_anteriores",
    "segmento_norm",
]
_PART_COLS = ["evento_id", "usuario", "usuario_cpf", "usuario_email", "role"]
_CPF_COORD = "11144477735"
_CPF_FORM = "52998224725"
_CPF_FORM2 = "39053344705"


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(export_contract_importer, "_hoje", lambda: HOJE)


@pytest.fixture
def masters():
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    TipoEventoFactory(nome="Formacao")
    UsuarioFactory(username="coord1", cpf=_CPF_COORD, email="coord1@example.invalid")
    UsuarioFactory(username="form1", cpf=_CPF_FORM, email="form1@example.invalid")
    UsuarioFactory(username="form2", cpf=_CPF_FORM2, email="form2@example.invalid")
    return ProjetoFactory(nome="Projeto X", fluxo="NAO_SUPER")


def _sol(**kw: str) -> dict[str, str]:
    base = {
        "evento_id": "EV900001",
        "municipio": "Cidade X",
        "uf": "CE",
        "projeto": "Projeto X",
        "tipo_evento": "Formacao",
        "data": AMANHA,
        "hora_inicio": "09:00",
        "hora_fim": "12:00",
        "segmento": "3º ano",
        "solicitante_cpf": _CPF_COORD,
        "cancelado": "",
        "evento_ids_anteriores": "[]",
        "segmento_norm": "",
    }
    base.update(kw)
    return base


def _part(evento_id: str, cpf: str = _CPF_FORM, role: str = "FORMADOR") -> dict[str, str]:
    return {"evento_id": evento_id, "usuario": "", "usuario_cpf": cpf, "usuario_email": "", "role": role}


def _csv(cols: list[str], rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def _export(tmp_path, sols: list[dict[str, str]], parts: list[dict[str, str]] | None = None, nome: str = "x") -> str:
    d = tmp_path / nome
    d.mkdir()
    entities: dict[str, Any] = {"solicitacao": {"file_csv": "solicitacao.csv", "rows": len(sols)}}
    (d / "solicitacao.csv").write_text(_csv(_SOL_COLS, sols), encoding="utf-8")
    if parts is not None:
        (d / "participation.csv").write_text(_csv(_PART_COLS, parts), encoding="utf-8")
        entities["participation"] = {"file_csv": "participation.csv", "rows": len(parts)}
    (d / "manifest.json").write_text(json.dumps({"entities": entities}), encoding="utf-8")
    return str(d)


def _apply(path: str, allow: tuple[str, ...] = ("solicitacao", "participation")) -> dict[str, Any]:
    return ExportContractImporter(path=path, apply=True, allow=allow).run()


def _dry(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path).run()["por_entidade"]


def _motivos(tally: dict[str, Any]) -> dict[str, int]:
    return {k: n for k, n in tally["skip_reasons"].items() if n}


def _existente(projeto, ext_hash: str, dia: date) -> Solicitacao:
    coord = UsuarioFactory(username=f"c_{ext_hash}", email=f"{ext_hash.lower()}@example.invalid")
    return Solicitacao.objects.create(
        usuario=coord,
        coordenador=coord,
        municipio=Municipio.objects.get(),
        projeto=projeto,
        tipo_evento=TipoEvento.objects.get(),
        inicio=timezone.make_aware(datetime.combine(dia, time(8, 0)), _FORTALEZA),
        fim=timezone.make_aware(datetime.combine(dia, time(12, 0)), _FORTALEZA),
        status=Solicitacao.Status.APROVADO,
        external_hash=ext_hash,
    )


def _formadores(ext_hash: str) -> set[str]:
    return set(
        Participation.objects.filter(solicitacao__external_hash=ext_hash, role="FORMADOR").values_list(
            "usuario__cpf", flat=True
        )
    )


# ---------- (b) evento passado novo ----------
def test_evento_novo_passado_nao_e_criado(tmp_path, masters):
    r = _apply(_export(tmp_path, [_sol(data=ONTEM)]), allow=("solicitacao",))
    assert Solicitacao.objects.count() == 0, "passado novo fica para a virada"
    assert r["applied"]["solicitacao"] == 0
    assert r["applied"]["solicitacao__pulada_passado"] == 1


def test_evento_novo_de_hoje_e_criado(tmp_path, masters):
    r = _apply(_export(tmp_path, [_sol(data=HOJE.isoformat())]), allow=("solicitacao",))
    assert r["applied"]["solicitacao"] == 1
    assert "solicitacao__pulada_passado" not in r["applied"]


def test_evento_novo_passado_cancelado_tambem_nao_nasce(tmp_path, masters):
    r = _apply(_export(tmp_path, [_sol(data=ONTEM, cancelado="true")]), allow=("solicitacao",))
    assert Solicitacao.objects.count() == 0
    assert r["applied"]["solicitacao__pulada_passado"] == 1


def test_evento_existente_passado_segue_com_o_reconcile(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 9, 8))
    r = _apply(_export(tmp_path, [_sol(evento_id="EV000100", data="2026-09-08", segmento_norm="3º ano EF")]))
    assert r["applied"]["solicitacao__segmento_norm_reconciled"] == 1
    assert "solicitacao__pulada_passado" not in r["applied"], "existente não é 'passado novo'"


def test_evento_existente_passado_segue_re_chaveando(tmp_path, masters):
    antiga = _existente(masters, "EV000100", date(2026, 9, 8))
    linha = _sol(evento_id="EV900100", data="2026-09-08", evento_ids_anteriores='["EV000100"]')
    r = _apply(_export(tmp_path, [linha]), allow=("solicitacao",))
    antiga.refresh_from_db()
    assert antiga.external_hash == "EV900100"
    assert r["applied"]["solicitacao__rechaveada"] == 1
    assert Solicitacao.objects.count() == 1


def test_dry_run_passado_novo_vira_skip_com_motivo(tmp_path, masters):
    rows = [_sol(evento_id="EV1", data=ONTEM), _sol(evento_id="EV2", data=AMANHA, cancelado="true")]
    tally = _dry(_export(tmp_path, rows))["solicitacao"]
    assert (tally["would_create"], tally["would_skip_same"]) == (1, 1)
    assert _motivos(tally) == {"evento_passado_novo": 1}
    assert tally["would_create_cancelada"] == 1


# ---------- (a) participação só em evento criado nesta execução ----------
def test_participacao_vincula_evento_criado_nesta_execucao(tmp_path, masters):
    r = _apply(_export(tmp_path, [_sol(evento_id="EV900200")], [_part("EV900200")]))
    assert r["applied"]["participation"] == 1
    assert _formadores("EV900200") == {_CPF_FORM}


def test_evento_existente_nao_ganha_nem_perde_participante(tmp_path, masters):
    sol = _existente(masters, "EV000100", date(2026, 11, 20))
    form2 = Usuario.objects.get(cpf=_CPF_FORM2)
    Participation.objects.create(solicitacao=sol, usuario=form2, role=Participation.Role.FORMADOR)
    path = _export(tmp_path, [_sol(evento_id="EV000100", data="2026-11-20")], [_part("EV000100")])
    r = _apply(path)
    assert r["applied"]["participation"] == 0
    assert _formadores("EV000100") == {_CPF_FORM2}, "fica quem já estava; quem a planilha lista não entra"


def test_evento_re_chaveado_nao_ganha_participante(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    linha = _sol(evento_id="EV900100", data="2026-11-20", evento_ids_anteriores='["EV000100"]')
    r = _apply(_export(tmp_path, [linha], [_part("EV900100")]))
    assert r["applied"]["solicitacao__rechaveada"] == 1
    assert r["applied"]["participation"] == 0
    assert _formadores("EV900100") == set()


def test_evento_passado_novo_nao_ganha_participante(tmp_path, masters):
    r = _apply(_export(tmp_path, [_sol(data=ONTEM)], [_part("EV900001")]))
    assert r["applied"]["participation"] == 0
    assert Participation.objects.count() == 0


def test_segunda_carga_nao_acrescenta_participante_ao_evento_da_primeira(tmp_path, masters):
    linha = _sol(evento_id="EV900300")
    _apply(_export(tmp_path, [linha], [_part("EV900300")], nome="a"))
    r2 = _apply(_export(tmp_path, [linha], [_part("EV900300"), _part("EV900300", cpf=_CPF_FORM2)], nome="b"))
    assert r2["applied"]["participation"] == 0
    assert _formadores("EV900300") == {_CPF_FORM}, "na 2ª carga o evento já existia"


def test_participation_sem_solicitacao_no_apply_nao_vincula(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    r = _apply(_export(tmp_path, [_sol(evento_id="EV000100")], [_part("EV000100")]), allow=("participation",))
    assert r["applied"]["participation"] == 0


def test_dry_run_participacao_espelha_o_apply(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    _existente(masters, "EV000200", date(2026, 11, 21))
    sols = [
        _sol(evento_id="EV000100", data="2026-11-20"),  # existente
        _sol(evento_id="EV900200", data="2026-11-21", evento_ids_anteriores='["EV000200"]'),  # re-chaveado
        _sol(evento_id="EV900300", data=AMANHA, hora_inicio="13:00", hora_fim="17:00"),  # novo
        _sol(evento_id="EV900400", data=ONTEM),  # passado novo
    ]
    parts = [
        _part("EV000100"),
        _part("EV900200"),
        _part("EV900300"),
        _part("EV900300", cpf=_CPF_FORM2),
        _part("EV900400"),
        _part("EV_ORFAO"),
    ]
    tally = _dry(_export(tmp_path, sols, parts))["participation"]
    assert tally["would_create"] == 2, "só o evento que seria criado"
    assert tally["would_skip_same"] == 3
    assert _motivos(tally) == {"evento_existente": 2, "evento_passado_novo": 1}
    assert tally["would_reject"] == 1, "órfã segue rejeitada"


# ---------- (c) trava no comando ----------
def test_comando_barra_participation_sem_solicitacao(tmp_path, masters):
    path = _export(tmp_path, [_sol()], [_part("EV900001")])
    with pytest.raises(CommandError, match="participation"):
        call_command("import_export_contract", "--path", path, "--apply", "--allow-entity", "participation")
    assert Participation.objects.count() == 0


def test_comando_aceita_participation_com_solicitacao(tmp_path, masters):
    path = _export(tmp_path, [_sol()], [_part("EV900001")])
    call_command(
        "import_export_contract",
        "--path",
        path,
        "--apply",
        "--allow-entity",
        "participation",
        "--allow-entity",
        "solicitacao",
        stdout=io.StringIO(),
    )
    assert _formadores("EV900001") == {_CPF_FORM}


# ---------- (d) rekey contraditório (caso Filadélfia) e saída em texto ----------
def test_rekey_contraditorio_conta_id_antigo_que_e_id_proprio_de_outra_linha(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    rows = [
        _sol(evento_id="EV000100", data="2026-11-20"),
        _sol(evento_id="EV900100", evento_ids_anteriores='["EV000100"]', hora_inicio="14:00", hora_fim="17:00"),
    ]
    tally = _dry(_export(tmp_path, rows))["solicitacao"]
    assert tally["rekey_contraditorio"] == 1
    assert (tally["would_rekey"], tally["would_create"]) == (0, 1), "só visibilidade, nada muda no resto"


def test_rekey_contraditorio_ignora_id_antigo_que_nao_esta_em_prod(tmp_path, masters):
    rows = [
        _sol(evento_id="EV000100"),
        _sol(evento_id="EV900100", evento_ids_anteriores='["EV000100"]', hora_inicio="14:00", hora_fim="17:00"),
    ]
    assert _dry(_export(tmp_path, rows))["solicitacao"]["rekey_contraditorio"] == 0


def test_saida_em_texto_mostra_skip_reasons_e_rekey_contraditorio(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    rows = [
        _sol(evento_id="EV000100", data="2026-11-20"),
        _sol(evento_id="EV900100", evento_ids_anteriores='["EV000100"]', hora_inicio="14:00", hora_fim="17:00"),
        _sol(evento_id="EV900400", data=ONTEM),
    ]
    out = io.StringIO()
    call_command("import_export_contract", "--path", _export(tmp_path, rows, [_part("EV000100")]), stdout=out)
    texto = out.getvalue()
    assert "skip_reasons={'evento_passado_novo': 1}" in texto
    assert "skip_reasons={'evento_existente': 1}" in texto
    assert "rekey_contraditorio=1" in texto


# ---------- (d) dry-run coerente com o apply: casos de borda ----------
_HOJE_REAL = export_contract_importer._hoje  # capturado antes da fixture autouse trocar


def _dry_e_apply(path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return _dry(path), _apply(path)["applied"]


def test_dry_run_mesmo_id_novo_em_duas_linhas_re_chaveadas_nao_preve_participacao(tmp_path, masters):
    _existente(masters, "EV000200", date(2026, 11, 21))
    sols = [
        _sol(evento_id="EV900200", data="2026-11-21", evento_ids_anteriores='["EV000200"]'),
        _sol(evento_id="EV900200", data="2026-11-22", evento_ids_anteriores='["EV000200"]'),
    ]
    dry, applied = _dry_e_apply(_export(tmp_path, sols, [_part("EV900200")]))
    assert dry["solicitacao"]["would_create"] == applied["solicitacao"] == 0
    assert dry["participation"]["would_create"] == applied["participation"] == 0
    assert _motivos(dry["participation"]) == {"evento_existente": 1}


def test_dry_run_re_chave_seguida_do_mesmo_id_sem_antigo_nao_preve_criacao(tmp_path, masters):
    _existente(masters, "EVA", date(2026, 11, 1))
    sols = [_sol(evento_id="EVX", evento_ids_anteriores='["EVA"]'), _sol(evento_id="EVX")]
    dry, applied = _dry_e_apply(_export(tmp_path, sols, [_part("EVX")]))
    assert (dry["solicitacao"]["would_create"], dry["solicitacao"]["would_rekey"]) == (0, 1)
    assert dry["participation"]["would_create"] == applied["participation"] == 0
    assert applied["solicitacao__rechaveada"] == 1


def test_dry_run_fim_antes_do_inicio_e_rejeitado_como_no_apply(tmp_path, masters):
    sols = [_sol(evento_id="EV900300", hora_inicio="14:00", hora_fim="10:00")]
    dry, applied = _dry_e_apply(_export(tmp_path, sols, [_part("EV900300")]))
    assert dry["solicitacao"]["would_create"] == applied["solicitacao"] == 0
    assert dry["solicitacao"]["would_reject"] == 1
    assert dry["solicitacao"]["reject_reasons"] == {"fim_antes_do_inicio": 1}
    assert dry["participation"]["would_create"] == applied["participation"] == 0
    assert dry["participation"]["would_reject"] == 1


def test_dry_run_coordenador_solicitante_nao_conta_como_participacao_nova(tmp_path, masters):
    parts = [_part("EVC", cpf=_CPF_COORD, role="COORDENADOR"), _part("EVC", cpf=_CPF_FORM, role="COORDENADOR")]
    dry, applied = _dry_e_apply(_export(tmp_path, [_sol(evento_id="EVC")], parts))
    assert dry["participation"]["would_create"] == applied["participation"] == 1, "só o outro coordenador"
    assert _motivos(dry["participation"]) == {"coordenador_solicitante": 1}


def test_dry_run_re_chave_comum_nao_e_contraditoria(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    linha = _sol(evento_id="EV900100", data="2026-11-20", evento_ids_anteriores='["EV000100"]')
    tally = _dry(_export(tmp_path, [linha]))["solicitacao"]
    assert (tally["would_rekey"], tally["rekey_contraditorio"]) == (1, 0)


def test_dry_run_id_proprio_listado_como_antigo_nao_e_contraditorio(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    linha = _sol(evento_id="EV000100", data="2026-11-20", evento_ids_anteriores='["EV000100"]')
    assert _dry(_export(tmp_path, [linha]))["solicitacao"]["rekey_contraditorio"] == 0


def test_dry_run_evento_de_hoje_seria_criado(tmp_path, masters):
    tally = _dry(_export(tmp_path, [_sol(data=HOJE.isoformat())]))["solicitacao"]
    assert tally["would_create"] == 1
    assert _motivos(tally) == {}


def test_dry_run_participation_sem_solicitacao_csv_usa_o_banco(tmp_path, masters):
    _existente(masters, "EV000100", date(2026, 11, 20))
    d = tmp_path / "so_part"
    d.mkdir()
    (d / "participation.csv").write_text(_csv(_PART_COLS, [_part("EV000100")]), encoding="utf-8")
    manifest = {"entities": {"participation": {"file_csv": "participation.csv", "rows": 1}}}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    tally = _dry(str(d))["participation"]
    assert _motivos(tally) == {"evento_existente": 1}
    assert tally["would_reject"] == 0


def test_hoje_usa_o_fuso_de_fortaleza(tmp_path, masters, monkeypatch):
    # 23:30 de 14/10 em Fortaleza = 02:30 de 15/10 em UTC: o evento de 14/10 ainda é de hoje.
    monkeypatch.setattr(export_contract_importer, "_hoje", _HOJE_REAL)
    monkeypatch.setattr(timezone, "now", lambda: datetime(2026, 10, 15, 2, 30, tzinfo=ZoneInfo("UTC")))
    r = _apply(_export(tmp_path, [_sol(data="2026-10-14")]), allow=("solicitacao",))
    assert r["applied"]["solicitacao"] == 1
