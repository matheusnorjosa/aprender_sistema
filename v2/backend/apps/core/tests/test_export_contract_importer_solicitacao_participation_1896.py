"""#1896 — apply (create-only) de `solicitacao` + `participation` no export-contract importer.

Fixtures sintéticos (sem PII real). Contratos exercidos:
- solicitante = coordenador (D3), resolvido por CPF; grava nos DOIS (FK `coordenador` + Participation
  COORDENADOR — decisão (a)).
- status via `resolve_initial_status` (PA-01: SUPER/desconhecido → pendente; NAO_SUPER → aprovado).
- NK = `_compute_external_hash` (mun,proj,tipo,data,hora_ini,hora_fim,segmento) — idempotente.
- participation liga por `evento_hash_natural` → `solicitacao.external_hash`; resolve usuario
  EMAIL-first → CPF → nome; sem match e com nome → `guest_nome` (preserva, não descarta).
- papel vem do CSV (derivado de POSIÇÃO pela planilha), NUNCA do cargo do usuário.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportIndexIssue=false, reportCallIssue=false, reportArgumentType=false

from __future__ import annotations

import json
from datetime import date, time
from typing import Any

import pytest

from apps.core.models.solicitacao import Participation, Solicitacao
from apps.core.services.eventos_import import _compute_external_hash
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

SOL_HEADER = (
    "municipio,uf,projeto,tipo_evento,data,hora_inicio,hora_fim,segmento,"
    "coord_acompanha,coordenador,coordenador_cpf,is_online,evento_hash_natural"
)
PART_HEADER = "evento_hash_natural,usuario,usuario_norm,usuario_cpf,usuario_email,role"


def _write_export(tmp_path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"generated_at": "2026-08-31", "snapshot_date": "2026-05-19", "entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv", "rows": max(content.strip().count("\n"), 0)}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _masters(fluxo: str = "NAO_SUPER"):
    mun = MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    proj = ProjetoFactory(nome="Projeto X", codigo="PX", fluxo=fluxo)
    tipo = TipoEventoFactory(nome="Formacao")
    coord = UsuarioFactory(
        username="coord1", cpf="11144477735", email="coord1@x.com", first_name="Coord", last_name="Um"
    )
    return mun, proj, tipo, coord


def _hash(mun, proj, tipo, seg="Fund I"):
    return _compute_external_hash(mun.id, proj.id, tipo.id, date(2026, 5, 10), time(9, 0), time(12, 0), seg)


def _sol_row(coord_cpf="11144477735", ehash="", seg="Fund I", coord_ac="Sim"):
    return (
        f"{SOL_HEADER}\n"
        f"Cidade X,CE,Projeto X,Formacao,2026-05-10,09:00,12:00,{seg},"
        f"{coord_ac},Coord Um,{coord_cpf},Nao,{ehash}\n"
    )


def test_apply_solicitacao_coordenador_as_solicitante_and_participation(tmp_path):
    mun, proj, tipo, coord = _masters()
    eh = _hash(mun, proj, tipo)
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh)})
    r = ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    assert r["applied"]["solicitacao"] == 1
    sol = Solicitacao.objects.get()
    assert sol.usuario_id == coord.id, "solicitante = coordenador (D3)"
    assert sol.coordenador_id == coord.id, "grava nos DOIS (decisão a)"
    assert (sol.municipio_id, sol.projeto_id, sol.tipo_evento_id) == (mun.id, proj.id, tipo.id)
    assert sol.status == "aprovado", "NAO_SUPER → resolve_initial_status"
    assert sol.segmento == "Fund I"
    assert sol.coordenador_acompanha is True, "coord_acompanha Sim → True"
    assert sol.external_hash == eh
    assert Participation.objects.filter(solicitacao=sol, usuario=coord, role="COORDENADOR").exists()


def test_apply_solicitacao_super_stays_pendente(tmp_path):
    mun, proj, tipo, _coord = _masters(fluxo="SUPER")
    eh = _hash(mun, proj, tipo)
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh)})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    assert Solicitacao.objects.get().status == "pendente", "PA-01: SUPER nunca auto-aprova"


def test_apply_solicitacao_rejects_when_coordenador_unresolved(tmp_path):
    mun, proj, tipo, _coord = _masters()
    eh = _hash(mun, proj, tipo)
    # CPF não cadastrado → sem solicitante (usuario NOT NULL) → não cria
    path = _write_export(tmp_path, {"solicitacao": _sol_row(coord_cpf="52998224725", ehash=eh)})
    r = ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    assert r["applied"]["solicitacao"] == 0
    assert Solicitacao.objects.count() == 0


def test_apply_solicitacao_idempotent(tmp_path):
    mun, proj, tipo, _coord = _masters()
    eh = _hash(mun, proj, tipo)
    files = {"solicitacao": _sol_row(ehash=eh)}
    path = _write_export(tmp_path, files)
    ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    r2 = ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    assert r2["applied"]["solicitacao"] == 0, "2ª run não duplica"
    assert Solicitacao.objects.count() == 1


def test_apply_participation_links_by_hash_and_email_first(tmp_path):
    mun, proj, tipo, _coord = _masters()
    formador = UsuarioFactory(
        username="form1", cpf="52998224725", email="form1@x.com", first_name="Form", last_name="Um"
    )
    eh = _hash(mun, proj, tipo)
    part = f"{PART_HEADER}\n{eh},Form Um,FORM UM,52998224725,form1@x.com,FORMADOR\n"
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh), "participation": part})
    r = ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    assert r["applied"]["participation"] >= 1
    assert Participation.objects.filter(solicitacao__external_hash=eh, usuario=formador, role="FORMADOR").exists()


def test_apply_participation_name_only_preserves_guest_nome(tmp_path):
    mun, proj, tipo, _coord = _masters()
    eh = _hash(mun, proj, tipo)
    # pessoa que saiu: sem email, sem cpf, sem match → nome PRESERVADO (não descartado)
    part = f"{PART_HEADER}\n{eh},Fulana Que Saiu,FULANA QUE SAIU,,,FORMADOR\n"
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh), "participation": part})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    p = Participation.objects.get(solicitacao__external_hash=eh, role="FORMADOR", usuario__isnull=True)
    assert p.guest_nome == "Fulana Que Saiu"


def test_apply_participation_role_from_csv_not_cargo(tmp_path):
    """Papel vem do CSV (posição), não do cargo: pessoa de cargo coordenação em vaga FORMADOR."""
    mun, proj, tipo, _coord = _masters()
    pessoa = UsuarioFactory(username="p2", cpf="52998224725", email="p2@x.com", first_name="Pessoa", last_name="Dois")
    eh = _hash(mun, proj, tipo)
    part = f"{PART_HEADER}\n{eh},Pessoa Dois,PESSOA DOIS,52998224725,p2@x.com,FORMADOR\n"
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh), "participation": part})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    assert Participation.objects.filter(solicitacao__external_hash=eh, usuario=pessoa, role="FORMADOR").exists()
    assert not Participation.objects.filter(usuario=pessoa, role="COORDENADOR").exists()


def test_solicitacao_participation_classify_not_marked_not_implemented(tmp_path):
    mun, proj, tipo, _coord = _masters()
    eh = _hash(mun, proj, tipo)
    part = f"{PART_HEADER}\n{eh},Form Um,FORM UM,52998224725,form1@x.com,FORMADOR\n"
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh), "participation": part})
    r = ExportContractImporter(path=path, apply=False).run()
    assert "would_create" in r["por_entidade"]["solicitacao"], "solicitacao deve classificar (não not_implemented)"
    assert "would_create" in r["por_entidade"]["participation"]


def test_apply_solicitacao_uses_csv_evento_hash_natural_not_recompute(tmp_path):
    """FALLBACK (CSV sem evento_id): armazena o `evento_hash_natural` do CSV, não recomputa (o recompute
    usa IDs do Django que o sheets não conhece → participação orfanizaria). Guard de 'primeira execução'."""
    mun, proj, tipo, _coord = _masters()
    formador = UsuarioFactory(username="f9", cpf="52998224725", email="f9@x.com", first_name="F", last_name="Nove")
    # hash arbitrário do sheets.banco — NÃO é o _compute_external_hash (IDs do Django)
    sheets_hash = "sheetsbanco0001abcdef"
    assert sheets_hash != _hash(mun, proj, tipo), "fixture: o hash do sheets tem que diferir do recompute"
    part = f"{PART_HEADER}\n{sheets_hash},F Nove,F NOVE,52998224725,f9@x.com,FORMADOR\n"
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=sheets_hash), "participation": part})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    sol = Solicitacao.objects.get()
    assert sol.external_hash == sheets_hash, "fallback: armazena o evento_hash_natural do CSV, não recomputa"
    assert Participation.objects.filter(
        solicitacao=sol, usuario=formador, role="FORMADOR"
    ).exists(), "participação liga por evento_hash_natural → external_hash armazenado"


def test_apply_solicitacao_prefers_stable_evento_id_over_hash(tmp_path):
    """RELAY 52: identidade = `evento_id` (ledger estável), NÃO o `evento_hash_natural` (conteúdo, deriva
    ~2%/10 dias). Com ambos presentes e DIFERENTES, o import armazena o evento_id e a participation liga
    por ele — senão a cada carga ~44 eventos virariam 'novo' + órfão (RELAY 50 item 2)."""
    _masters()  # cria Municipio/Projeto/TipoEvento/coordenador (resolvidos pelos nomes hardcoded)
    formador = UsuarioFactory(username="f10", cpf="52998224725", email="f10@x.com", first_name="F", last_name="Dez")
    evento_id = "EVT-000123"
    hash_val = "hash_que_deriva_9999"  # diferente do evento_id de propósito
    sol_csv = (
        f"{SOL_HEADER},evento_id\n"
        f"Cidade X,CE,Projeto X,Formacao,2026-05-10,09:00,12:00,Fund I,Sim,Coord Um,11144477735,Nao,{hash_val},{evento_id}\n"
    )
    part = f"{PART_HEADER},evento_id\n{hash_val},F Dez,F DEZ,52998224725,f10@x.com,FORMADOR,{evento_id}\n"
    path = _write_export(tmp_path, {"solicitacao": sol_csv, "participation": part})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    sol = Solicitacao.objects.get()
    assert sol.external_hash == evento_id, "identidade = evento_id estável, não o hash de conteúdo"
    assert Participation.objects.filter(
        solicitacao=sol, usuario=formador, role="FORMADOR"
    ).exists(), "participation liga por evento_id → external_hash"


# ─────────────────────────────────────────────────────────────────────────────
# v16.4 (RELAY 57): o dono do evento vem RESOLVIDO em `solicitante_cpf`/`solicitante_email`
# (cascata coluna_n + escada-2-tokens + inferência), com `solicitante_procedencia` carimbando
# o degrau. `linha_completa=false` = fora de escopo (sem hora/dados) — não importa.
# ─────────────────────────────────────────────────────────────────────────────

SOL_HEADER_V16 = (
    "municipio,uf,projeto,tipo_evento,data,hora_inicio,hora_fim,segmento,"
    "coord_acompanha,is_online,linha_completa,solicitante_cpf,solicitante_email,"
    "solicitante_procedencia,coordenador_cpf,evento_id"
)


def _sol_row_v16(
    *,
    solicitante_cpf="",
    solicitante_email="",
    procedencia="coluna_n",
    linha_completa="true",
    coordenador_cpf="",
    evento_id="EVT-1",
):
    return (
        f"{SOL_HEADER_V16}\n"
        f"Cidade X,CE,Projeto X,Formacao,2026-05-10,09:00,12:00,Fund I,"
        f"Sim,Nao,{linha_completa},{solicitante_cpf},{solicitante_email},"
        f"{procedencia},{coordenador_cpf},{evento_id}\n"
    )


def test_apply_solicitacao_prefers_solicitante_cpf_over_coordenador_cpf(tmp_path):
    """v16.4: `solicitante_cpf` (dono já resolvido) tem prioridade sobre a coluna N crua
    (`coordenador_cpf`), que nos 130 casos-fila está errada/vazia."""
    _masters()  # semeia Municipio/Projeto/TipoEvento/coord (cpf 11144477735)
    outro = UsuarioFactory(
        username="outro", cpf="52998224725", email="outro@x.com", first_name="Outro", last_name="Pessoa"
    )
    csv = _sol_row_v16(solicitante_cpf="52998224725", coordenador_cpf="11144477735", evento_id="EVT-A")
    path = _write_export(tmp_path, {"solicitacao": csv})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    sol = Solicitacao.objects.get()
    assert sol.usuario_id == outro.id, "solicitante_cpf (v16.4) vence coordenador_cpf"
    assert sol.coordenador_id == outro.id, "grava a pessoa resolvida nos DOIS FKs"


def test_apply_solicitacao_falls_back_to_solicitante_email(tmp_path):
    """Quando `solicitante_cpf` não resolve (ausente no seed), cai para `solicitante_email`."""
    _mun, _proj, _tipo, coord = _masters()  # coord email coord1@x.com
    csv = _sol_row_v16(solicitante_cpf="", solicitante_email="coord1@x.com", evento_id="EVT-B")
    path = _write_export(tmp_path, {"solicitacao": csv})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    assert Solicitacao.objects.get().usuario_id == coord.id, "resolve por solicitante_email"


def test_apply_solicitacao_stamps_solicitante_procedencia(tmp_path):
    """`solicitante_procedencia` é carimbada no registro (auditoria: fato vs inferência)."""
    _masters()
    csv = _sol_row_v16(solicitante_cpf="11144477735", procedencia="cargo_unico", evento_id="EVT-C")
    path = _write_export(tmp_path, {"solicitacao": csv})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    assert Solicitacao.objects.get().solicitante_procedencia == "cargo_unico"


def test_apply_solicitacao_rejects_incomplete_line(tmp_path):
    """`linha_completa=false` não importa, mesmo com solicitante e hora resolvidos (v16.2)."""
    _masters()
    # resolvível pelos DOIS caminhos (solicitante_cpf E coordenador_cpf) — isola linha_completa
    csv = _sol_row_v16(
        solicitante_cpf="11144477735", coordenador_cpf="11144477735", linha_completa="false", evento_id="EVT-D"
    )
    path = _write_export(tmp_path, {"solicitacao": csv})
    r = ExportContractImporter(path=path, apply=True, allow=("solicitacao",)).run()
    assert r["applied"]["solicitacao"] == 0, "linha_completa=false → fora de escopo"
    assert Solicitacao.objects.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# v16.4 participation (RELAY 57): `match_procedencia` vazio = o sheets tentou CPF/e-mail +
# escada-2-tokens e ABSTEVE-SE. O importer NÃO pode cair no resolver-por-nome (Degrau 2 casa
# quem SAIU a um homônimo de nome mais longo) — preserva como guest_nome. Guarda de relay.
# ─────────────────────────────────────────────────────────────────────────────

PART_HEADER_V16 = "evento_id,evento_hash_natural,usuario,usuario_norm,usuario_cpf,usuario_email,match_procedencia,role"


def test_apply_participation_empty_match_procedencia_becomes_guest_nome(tmp_path):
    """match_procedencia vazio → não resolve por nome (evita casar a pessoa que saiu ao homônimo
    que ficou, via Degrau 2 token-subconjunto) → guest_nome."""
    mun, proj, tipo, _coord = _masters()
    # usuário que FICOU, nome mais longo: 'Manuela Fonseca' ⊆ tokens de 'Manuela Fonseca Silva'
    ficou = UsuarioFactory(
        username="mfs", cpf="52998224725", email="mfs@x.com", first_name="Manuela Fonseca", last_name="Silva"
    )
    eh = _hash(mun, proj, tipo)
    # match_procedencia vazio, sem cpf/email — a pessoa que saiu
    part = f"{PART_HEADER_V16}\n{eh},{eh},Manuela Fonseca,MANUELA FONSECA,,,,FORMADOR\n"
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh), "participation": part})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    assert not Participation.objects.filter(
        solicitacao__external_hash=eh, usuario=ficou
    ).exists(), "match vazio não pode casar por nome ao homônimo que ficou"
    p = Participation.objects.get(solicitacao__external_hash=eh, role="FORMADOR", usuario__isnull=True)
    assert p.guest_nome == "Manuela Fonseca", "preserva quem saiu como guest_nome"


def test_apply_participation_nonempty_match_still_resolves_by_name(tmp_path):
    """Guarda só age no match VAZIO: com match preenchido (ou coluna ausente, fixtures), o resolver
    por nome segue valendo — não quebra o caminho legítimo."""
    mun, proj, tipo, _coord = _masters()
    pessoa = UsuarioFactory(username="p3", cpf="52998224725", email="p3@x.com", first_name="Pessoa", last_name="Tres")
    eh = _hash(mun, proj, tipo)
    part = f"{PART_HEADER_V16}\n{eh},{eh},Pessoa Tres,PESSOA TRES,,,escada_2tokens,FORMADOR\n"
    path = _write_export(tmp_path, {"solicitacao": _sol_row(ehash=eh), "participation": part})
    ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    assert Participation.objects.filter(
        solicitacao__external_hash=eh, usuario=pessoa, role="FORMADOR"
    ).exists(), "match não-vazio → resolve por nome normalmente"
