"""
Tests do APPLY (create-only) da fatia plano_formacao do export-contract.

Contrato (travado com o pipeline sheets.banco): `ano` declarado do workbook (coluna `ano`);
`sem_plano`=reserva (não é plano → não cria); coordenador resolvido por email→nome (DATCoordenador
não tem CPF nem unique → ambíguo/ausente = NULL). NK (municipio, projeto, ano).

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


def _setup(tmp_path, row: str):
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    return _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"})


def test_apply_plano_creates_with_ano_coordenador_and_ch(tmp_path):
    actor = _actor()
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    coord = DATCoordenador.objects.create(nome="Coord X", email="coord@x.com", area="DAT", created_by=actor)
    row = "Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,Coord X,,coord@x.com,10.00,40.00,50.00"
    path = _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"})
    r = ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert r["applied"]["plano_formacao"] == 1
    p = PlanoFormacoes.objects.get()
    assert p.ano == 2026
    assert p.coordenador_id == coord.id  # resolvido por email
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
    assert PlanoFormacoes.objects.get().coordenador_id is None  # nome não bate → NULL, não chuta


def test_apply_plano_ambiguous_email_resolves_none(tmp_path):
    """Email de CARGO herdado por 2 coordenadores (a caixa trocou de dono) → NULL, não chuta o dono atual."""
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
    assert PlanoFormacoes.objects.get().coordenador_id is None  # email ambíguo → NULL (não atrela o errado)


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


# --------------------- resolução por CPF (opção A #1837 · Wave 2) ---------------------

_CPF_A = "22255588846"


def _plano_with(tmp_path, coordenador="", coordenador_cpf="", coordenador_email=""):
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    ProjetoFactory(nome="Proj X", fluxo="NAO_SUPER")
    row = (
        f"Cidade X,CIDADE X,CE,Proj X,Proj X,2026,workbook,false,"
        f"{coordenador},{coordenador_cpf},{coordenador_email},0,0,0"
    )
    return _write_export(tmp_path, {"plano_formacao": f"{PLANO_HEADER}\n{row}\n"})


def test_apply_plano_resolves_by_cpf(tmp_path):
    """CPF casa o coordenador mesmo com nome/email da linha divergentes."""
    actor = _actor()
    coord = DATCoordenador.objects.create(
        nome="Pessoa Real", email="pessoal@x.com", area="DAT", cpf=_CPF_A, created_by=actor
    )
    path = _plano_with(tmp_path, coordenador="Outro Nome", coordenador_cpf=_CPF_A, coordenador_email="cargo@x.com")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert PlanoFormacoes.objects.get().coordenador_id == coord.id


def test_apply_plano_cpf_wins_over_divergent_email(tmp_path):
    """A linha traz o CPF de A e o email de cargo de B → resolve A (CPF autoritativo)."""
    actor = _actor()
    a = DATCoordenador.objects.create(nome="A", email="a@x.com", area="DAT", cpf=_CPF_A, created_by=actor)
    DATCoordenador.objects.create(nome="B", email="coordenacao11@x.com", area="DAT", created_by=actor)
    path = _plano_with(tmp_path, coordenador_cpf=_CPF_A, coordenador_email="coordenacao11@x.com")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert PlanoFormacoes.objects.get().coordenador_id == a.id


def test_apply_plano_cpf_miss_falls_to_name_not_email(tmp_path):
    """CPF presente mas sem match → cai para NOME (sem match) → NULL. NUNCA para o email de cargo."""
    actor = _actor()
    DATCoordenador.objects.create(nome="Cargo Holder", email="coordenacao11@x.com", area="DAT", created_by=actor)
    path = _plano_with(
        tmp_path, coordenador="Nome Que Nao Existe", coordenador_cpf=_CPF_A, coordenador_email="coordenacao11@x.com"
    )
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert PlanoFormacoes.objects.get().coordenador_id is None  # não usou o email de cargo


def test_apply_plano_no_cpf_uses_email(tmp_path):
    """Sem CPF na linha → mantém o fallback email→nome (status quo PR3)."""
    actor = _actor()
    coord = DATCoordenador.objects.create(nome="E", email="e@x.com", area="DAT", created_by=actor)
    path = _plano_with(tmp_path, coordenador_email="e@x.com")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert PlanoFormacoes.objects.get().coordenador_id == coord.id


def test_apply_plano_empty_cpf_index_guard(tmp_path):
    """Guard falsy: um coordenador com cpf='' não pode ser casado por uma linha de cpf vazio."""
    actor = _actor()
    DATCoordenador.objects.create(nome="Vazio", email="", area="DAT", cpf="", created_by=actor)
    path = _plano_with(tmp_path, coordenador="Sem Ninguem", coordenador_cpf="", coordenador_email="")
    ExportContractImporter(path=path, apply=True, allow=("plano_formacao",), actor=actor).run()
    assert PlanoFormacoes.objects.get().coordenador_id is None
