"""
Tests do APPLY (create-only) da fatia plano_formacao do export-contract.

Contrato (travado com o pipeline sheets.banco): `ano` declarado do workbook (coluna `ano`);
`sem_plano`=reserva (não é plano → não cria); coordenadores = as PESSOAS que coordenaram, N:N por
co-liderança (#1957): array `coordenadores_cpf` com fallback `coordenador_cpf` único, cada CPF → `Usuario`
(cpf unique; sem fallback email/nome; ausente/inválido/sem match → descartado, #1849). NK (municipio,
projeto, ano).

Segurança: apply exige allowlist + actor (--as-user); create-only; idempotente. Fixtures sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from apps.core.models import DATCoordenador, PlanoFormacoes
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

PLANO_HEADER = (
    "municipio,municipio_norm,uf,projeto,projeto_norm,ano,ano_origem,sem_plano,"
    "coordenador,coordenador_cpf,coordenador_email,ch_estudo,ch_total_planilha,ch_anual_planilha"
)
# Header com a coluna N:N (co-liderança, #1957). CSV antigo (sem ela) cai no fallback coordenador_cpf.
PLANO_HEADER_M2M = PLANO_HEADER + ",coordenadores_cpf"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-08-24", "snapshot_date": "2026-08-24", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _actor():
    return UsuarioFactory(username="u_apply_plano", password="x", cpf="11144477735")


def _coord_ids(p: PlanoFormacoes) -> list[int]:
    """Ids dos coordenadores (M2M), em ordem de id — o dado importado."""
    return list(p.coordenadores.values_list("id", flat=True).order_by("id"))


def _setup(tmp_path, row: str):
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    return _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"})


def test_apply_plano_creates_with_ano_coordenador_and_ch(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    coord = UsuarioFactory(cpf="22255588846")  # a PESSOA que coordenou
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,Coord X,22255588846,coord@x.com,10.00,40.00,50.00"
    path = _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert r["applied"]["plano_formacao"] == 1
    p = PlanoFormacoes.objects.get()
    assert p.ano == 2026
    assert _coord_ids(p) == [coord.id]  # resolvido por CPF → Usuario (fallback da coluna única)
    assert p.ch_estudo == Decimal("10.00")
    assert p.ch_total == Decimal("40.00")  # semeado de ch_total_planilha
    assert p.ch_anual == Decimal("50.00")  # semeado de ch_anual_planilha
    assert p.created_by_id == actor.id


def test_apply_plano_two_years_coexist(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    csv = (
        f"{PLANO_HEADER}\n"
        "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,,,,0,0,0\n"
        "Cidade X,CIDADE X,CE,Proj X,Proj X,2027,celula,false,,,,0,0,0\n"
    )
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"plano_formacao": csv}), apply=True, allow=("plano_formacao",), actor=actor
    ).run()
    assert r["applied"]["plano_formacao"] == 2
    assert set(PlanoFormacoes.objects.values_list("ano", flat=True)) == {2026, 2027}


def test_apply_plano_skips_sem_plano(tmp_path):
    actor = _actor()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2027,celula,true,,,,0,0,0"
    r = ExportContractImporter(path=_setup(tmp_path, row), apply=True, allow=("plano_formacao",), actor=actor).run()
    assert r["applied"]["plano_formacao"] == 0  # reserva, não é plano
    assert PlanoFormacoes.objects.count() == 0


def test_apply_plano_coordenador_none_when_unresolvable(tmp_path):
    actor = _actor()
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,Fulano Inexistente,,,0,0,0"
    ExportContractImporter(path=_setup(tmp_path, row), apply=True, allow=("plano_formacao",), actor=actor).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == []  # nome não bate → sem coordenador, não chuta


def test_apply_plano_ambiguous_email_resolves_none(tmp_path):
    """Email de CARGO herdado por 2 coordenadores (a caixa trocou de dono) → sem coordenador (só resolve por CPF)."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    # mesmo email de função em 2 DATCoordenador (histórico de troca)
    DATCoordenador.objects.create(nome="Coord Antiga", email="coordenacao11@x.com", area="DAT", created_by=actor)
    DATCoordenador.objects.create(nome="Coord Nova", email="coordenacao11@x.com", area="DAT", created_by=actor)
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,,,coordenacao11@x.com,0,0,0"
    ExportContractImporter(
        path=_write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"}),
        apply=True,
        allow=("plano_formacao",),
        actor=actor,
    ).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == []  # email ambíguo → sem coordenador (não atrela o errado)


def test_apply_plano_idempotent(tmp_path):
    actor = _actor()
    path = _setup(tmp_path, "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,,,,0,0,0")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert r2["applied"]["plano_formacao"] == 0
    assert PlanoFormacoes.objects.count() == 1


def test_apply_plano_requires_actor(tmp_path):
    path = _setup(tmp_path, "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,,,,0,0,0")
    with pytest.raises(ValueError):
        ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=None).run()


def test_apply_plano_blocked_without_allowlist(tmp_path):
    actor = _actor()
    path = _setup(tmp_path, "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,,,,0,0,0")
    r = ExportContractImporter(path=path, apply=True, allow=(), actor=actor).run()
    assert r["apply_blocked"] is True
    assert PlanoFormacoes.objects.count() == 0


def test_apply_plano_skips_unresolved_projeto(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    row = "Cidade X,CIDADE X,CE,Proj Inexistente,Proj Inexistente,2026,workbook,false,,,,0,0,0"
    r = ExportContractImporter(
        path=_write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"}),
        apply=True,
        allow=("plano_formacao",),
        actor=actor,
    ).run()
    assert r["applied"]["plano_formacao"] == 0


def test_classify_plano_sem_plano_is_visible_reject(tmp_path):
    """Linha reservada (sem_plano) vira reject VISÍVEL no dry-run (reconcilia contagem, não some)."""
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    csv = (
        f"{PLANO_HEADER}\n"
        "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,,,,0,0,0\n"  # create
        "Cidade X,CIDADE X,CE,Proj X,Proj X,2027,celula,true,,,,0,0,0\n"  # sem_plano → reject
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"plano_formacao": csv})).run()["por_entidade"][
        "plano_formacao"
    ]
    assert r["would_create"] == 1
    assert r["would_reject"] == 1  # sem_plano visível


def test_classify_plano_ano_in_nk(tmp_path):
    """NK temporal: mesmo (mun, proj) com anos diferentes = distintos."""
    creator = UsuarioFactory(username="u_pf_ano", password="x", cpf="22255588846")
    mun = MunicipioFactory(nome="Cidade Ano PF", uf="CE", ativo=True)
    proj = ProjetoFactory(nome="Proj Ano PF", fluxo="NAO_SUPER")
    PlanoFormacoes.objects.create(municipio=mun, projeto=proj, ano=2026, created_by=creator)
    csv = (
        f"{PLANO_HEADER}\n"
        "Cidade Ano PF,CIDADE ANO PF,CE,Proj Ano PF,Proj Ano PF,2026,workbook,false,,,,0,0,0\n"  # existe → skip
        "Cidade Ano PF,CIDADE ANO PF,CE,Proj Ano PF,Proj Ano PF,2027,celula,false,,,,0,0,0\n"  # novo → create
    )
    r = ExportContractImporter(path=_write_export(tmp_path, {"plano_formacao": csv})).run()["por_entidade"][
        "plano_formacao"
    ]
    assert r["would_skip_same"] == 1
    assert r["would_create"] == 1
    assert r["would_reject"] == 0


def test_apply_plano_no_coordenador_pii_in_report(tmp_path):
    """coordenador é pessoa → nome/email/CPF nunca no relatório (dry-run não lê coordenador)."""
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,CoordSecretoZZZ,22255588846,secreto@zzz.com,0,0,0"
    report = ExportContractImporter(path=_write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"})).run()
    blob = json.dumps(report)
    assert "CoordSecretoZZZ" not in blob
    assert "secreto@zzz.com" not in blob
    assert "22255588846" not in blob  # o CPF (novo) também não vaza no report


# --------------------- resolução dos coordenadores = PESSOAS (Usuario) por CPF, N:N (#1849/#1957) ---------------------
# Os coordenadores do plano vêm da coluna Coordenador da Agenda = quem tocou o evento (PESSOAS).
# Co-liderança (RELAY 32/34): array `coordenadores_cpf`, fallback `coordenador_cpf` único. Resolve 100%
# contra Usuario por CPF (unique). SEM fallback email/nome (a pessoa é chave de CPF).

_CPF_A = "22255588846"
_CPF_B = "33366699957"


def _plano_with(tmp_path, coordenador="", coordenador_cpf="", coordenador_email=""):
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    row = (
        f"Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,"
        f"{coordenador},{coordenador_cpf},{coordenador_email},0,0,0"
    )
    return _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"})


def test_apply_plano_resolves_coordenador_to_usuario_by_cpf(tmp_path):
    """Coordenador do plano casa a PESSOA (Usuario) por CPF, ignorando nome/email divergentes na linha."""
    actor = _actor()
    pessoa = UsuarioFactory(cpf=_CPF_A)
    path = _plano_with(tmp_path, coordenador="Outro Nome", coordenador_cpf=_CPF_A, coordenador_email="cargo@x.com")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == [pessoa.id]


def test_apply_plano_cpf_miss_is_null(tmp_path):
    """CPF presente mas nenhum Usuario tem → sem coordenador (sem fallback email/nome)."""
    actor = _actor()
    UsuarioFactory(cpf=_CPF_B)  # outra pessoa, cpf diferente
    path = _plano_with(tmp_path, coordenador="Nome Qualquer", coordenador_cpf=_CPF_A, coordenador_email="cargo@x.com")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == []


def test_apply_plano_no_cpf_is_null(tmp_path):
    """Sem CPF na linha → sem coordenador (sem fallback por email/nome de cargo)."""
    actor = _actor()
    UsuarioFactory(cpf=_CPF_A)
    path = _plano_with(tmp_path, coordenador="Alguem", coordenador_cpf="", coordenador_email="e@x.com")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == []


def test_apply_plano_invalid_cpf_is_null(tmp_path):
    """CPF estruturalmente inválido (mod-11) → sem coordenador, sem chute."""
    actor = _actor()
    path = _plano_with(tmp_path, coordenador_cpf="12345678900")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == []


# --------------------- co-liderança N:N: array coordenadores_cpf (#1957) ---------------------


def _plano_m2m(tmp_path, coordenadores_cpf_json: str, coordenador_cpf: str = ""):
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    # coordenadores_cpf é array JSON → vem entre aspas no CSV (contém vírgulas).
    row = (
        f"Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,Dupla,{coordenador_cpf},,0,0,0,"
        f'"{coordenadores_cpf_json}"'
    )
    return _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER_M2M}\n{row}\n"})


def test_apply_plano_multiple_coordenadores_from_json_array(tmp_path):
    """Co-liderança (#1957): array coordenadores_cpf → M2M com os N coordenadores resolvidos por CPF.

    Reproduz UNIÃO DOS PALMARES / 'Elienai & Silvio': 1 plano (NK mun/proj/ano), 2 coordenadores.
    """
    actor = _actor()
    a = UsuarioFactory(cpf=_CPF_A)
    b = UsuarioFactory(cpf=_CPF_B)
    json_arr = f'[""{_CPF_A}"",""{_CPF_B}""]'  # aspas duplicadas = escape CSV
    path = _plano_m2m(tmp_path, json_arr)
    r = ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert r["applied"]["plano_formacao"] == 1  # 1 plano, não 2
    assert set(_coord_ids(PlanoFormacoes.objects.get())) == {a.id, b.id}


def test_apply_plano_coordenadores_array_skips_unresolvable(tmp_path):
    """Array com um CPF válido + um sem match no cadastro → só o que resolve entra no M2M (sem chute)."""
    actor = _actor()
    a = UsuarioFactory(cpf=_CPF_A)  # existe
    # _CPF_B não tem Usuario cadastrado
    json_arr = f'[""{_CPF_A}"",""{_CPF_B}""]'
    path = _plano_m2m(tmp_path, json_arr)
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == [a.id]


def test_apply_plano_array_takes_precedence_over_single(tmp_path):
    """Havendo o array (não-vazio), ele manda; a coluna única `coordenador_cpf` é ignorada."""
    actor = _actor()
    a = UsuarioFactory(cpf=_CPF_A)
    UsuarioFactory(cpf=_CPF_B)  # B existe no cadastro — mas o array [A] deve vencer mesmo assim
    json_arr = f'[""{_CPF_A}""]'  # array só com A
    path = _plano_m2m(tmp_path, json_arr, coordenador_cpf=_CPF_B)  # single = B, deve ser ignorado
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == [a.id]


# --------------- reconcile do M2M coordenadores em plano EXISTENTE (#1957 follow-up, v18) ---------------
# O importer é create-only para o PLANO, mas mantém `coordenadores` (autoritativo do import, read-only na
# UI) em sincronia num plano JÁ existente — REPORTADO sob `plano_formacao__coordenadores_reconciled`, nunca
# silencioso (#1628/#1738), e NUNCA esvazia (array vazio = ausência de sinal, não sinal de remoção).
# Necessário porque o backfill do #1958 deu 1 coordenador aos planos co-liderados; o array v18 traz os 2.


def _write_plano_arr(base, arr_json, ch_estudo="0"):
    """Escreve um export mínimo de plano_formacao com um array de coordenadores, num subdir próprio."""
    base.mkdir(parents=True, exist_ok=True)
    row = f'Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,Dupla,,,{ch_estudo},0,0,"{arr_json}"'
    (base / "plano_formacao.csv").write_text(f"{PLANO_HEADER_M2M}\n{row}\n", encoding="utf-8")
    (base / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "x",
                "snapshot_date": "x",
                "entities": {"plano_formacao": {"file_csv": "plano_formacao.csv", "rows": 1}},
            }
        ),
        encoding="utf-8",
    )
    return str(base)


def test_apply_plano_reconciles_coordenadores_on_existing(tmp_path):
    """Plano já existente com 1 coordenador + array v18 com 2 → reconcilia p/ os 2 (reportado)."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    a = UsuarioFactory(cpf=_CPF_A)
    b = UsuarioFactory(cpf=_CPF_B)
    ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v1", f'[""{_CPF_A}""]'),
        apply=True,
        allow=("plano_formacao",),
        actor=actor,
    ).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == [a.id]
    r = ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v2", f'[""{_CPF_A}"",""{_CPF_B}""]'),
        apply=True,
        allow=("plano_formacao",),
        actor=actor,
    ).run()
    assert r["applied"]["plano_formacao"] == 0  # nenhum plano NOVO
    assert r["applied"]["plano_formacao__coordenadores_reconciled"] == 1
    assert set(_coord_ids(PlanoFormacoes.objects.get())) == {a.id, b.id}


def test_apply_plano_reconcile_idempotent(tmp_path):
    """Reconciliar com o mesmo array de novo → 0 (sem chave reconciled, sem re-escrever o M2M)."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    UsuarioFactory(cpf=_CPF_A)
    UsuarioFactory(cpf=_CPF_B)
    arr = f'[""{_CPF_A}"",""{_CPF_B}""]'
    ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v1", arr), apply=True, allow=("plano_formacao",), actor=actor
    ).run()
    r = ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v2", arr), apply=True, allow=("plano_formacao",), actor=actor
    ).run()
    assert r["applied"]["plano_formacao"] == 0
    assert "plano_formacao__coordenadores_reconciled" not in r["applied"]


def test_apply_plano_reconcile_scoped_to_coordenadores(tmp_path):
    """Reconcile toca SÓ coordenadores; ch_estudo do plano existente NÃO muda (create-only anti-silent-update)."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    a = UsuarioFactory(cpf=_CPF_A)
    b = UsuarioFactory(cpf=_CPF_B)
    ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v1", f'[""{_CPF_A}""]', ch_estudo="10"),
        apply=True,
        allow=("plano_formacao",),
        actor=actor,
    ).run()
    ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v2", f'[""{_CPF_A}"",""{_CPF_B}""]', ch_estudo="99"),
        apply=True,
        allow=("plano_formacao",),
        actor=actor,
    ).run()
    p = PlanoFormacoes.objects.get()
    assert set(_coord_ids(p)) == {a.id, b.id}
    assert p.ch_estudo == Decimal("10.00")  # o resto NÃO é sobrescrito


def test_apply_plano_reconcile_empty_array_does_not_wipe(tmp_path):
    """Array vazio numa reentrega = ausência de sinal → NÃO esvazia os coordenadores existentes."""
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    a = UsuarioFactory(cpf=_CPF_A)
    ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v1", f'[""{_CPF_A}""]'), apply=True, allow=("plano_formacao",), actor=actor
    ).run()
    r = ExportContractImporter(
        path=_write_plano_arr(tmp_path / "v2", "[]"), apply=True, allow=("plano_formacao",), actor=actor
    ).run()
    assert _coord_ids(PlanoFormacoes.objects.get()) == [a.id]  # preservado
    assert "plano_formacao__coordenadores_reconciled" not in r["applied"]
