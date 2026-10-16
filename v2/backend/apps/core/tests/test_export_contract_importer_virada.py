"""Carga da virada (`--mode virada`, plano do importador da virada, 16/10/2026, §1-§3 e §9).

Princípio do dono: a carga é uma só. O que foi mexido pela tela vence; o resto recebe o estado da
planilha do dia. Regras cobertas (numeração da §6.1 do plano):

- "tocado" (§2, R2 + decisões 1 e 6): pessoa = AuditLog com ip (texto) numa ação de edição/Google pela
  tela, ou LogEntry do admin; aprovação pela tela NÃO conta; publicado pelo sistema = qualquer rastro do
  Google; script = trava só os campos de dado que ele mudou (status nunca trava); o próprio importador não
  conta.
- Por evento: projeto (só pela disciplina) → data e hora → formadores → status (cancelado → reprovado;
  senão mudança material em SUPER aprovado → pendente; nunca aprova, nunca tira de reprovado) → AuditLog.
- Participantes: só FORMADOR troca; CONVIDADO só acrescenta; COORDENADOR e COORD_ACOMPANHA nunca mudam.
- Passado novo é criado. Evento apagado no sistema não é recriado. Linha incompleta não esconde o evento.
- Marca `publicado_fora_do_sistema` em quem está no Google pela planilha. A carga nunca chama o Google.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportArgumentType=false

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

import pytest

from apps.core.models import AuditLog, Municipio, TipoEvento, Usuario
from apps.core.models.solicitacao import Participation, Solicitacao
from apps.core.services import export_contract_importer
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.services.solicitacao_publish import motivo_nao_publicavel
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_FORTALEZA = ZoneInfo("America/Fortaleza")
HOJE = date(2026, 10, 16)
FUTURO = date(2026, 11, 5)
FUTURO_ISO = FUTURO.isoformat()
PASSADO = date(2026, 9, 10)
PASSADO_ISO = PASSADO.isoformat()

_SOL_COLS = [
    "evento_id",
    "municipio",
    "uf",
    "projeto",
    "disciplina",
    "tipo_evento",
    "data",
    "hora_inicio",
    "hora_fim",
    "segmento",
    "solicitante_cpf",
    "cancelado",
    "evento_ids_anteriores",
    "segmento_norm",
    "linha_completa",
    "aprovado",
    "na_agenda_google",
    "external_event_id",
    "external_event_id_confianca",
]
_PART_COLS = ["evento_id", "usuario", "usuario_cpf", "usuario_email", "role", "match_procedencia"]
_CPF_COORD = "11144477735"
_CPF_F1 = "52998224725"
_CPF_F2 = "39053344705"
_CPF_F3 = "86288366757"
_CPF_INATIVO = "71428793860"
_ADMIN_IP = "10.0.0.7"


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(export_contract_importer, "_hoje", lambda: HOJE)


@pytest.fixture
def m():
    """Mestres sintéticos. `m.nao_super`, `m.super`, agrupador Superativar e os dois irmãos de disciplina."""
    MunicipioFactory(nome="Cidade X", uf="CE", ativo=True)
    MunicipioFactory(nome="Cidade Y", uf="CE", ativo=True)
    TipoEventoFactory(nome="Formacao")

    class _M:
        coord = UsuarioFactory(username="coord1", cpf=_CPF_COORD, email="coord1@example.invalid")
        f1 = UsuarioFactory(username="form1", cpf=_CPF_F1, email="form1@example.invalid")
        f2 = UsuarioFactory(username="form2", cpf=_CPF_F2, email="form2@example.invalid")
        f3 = UsuarioFactory(username="form3", cpf=_CPF_F3, email="form3@example.invalid")
        inativo = UsuarioFactory(
            username="form_inativo", cpf=_CPF_INATIVO, email="inativo@example.invalid", is_active=False
        )
        nao_super = ProjetoFactory(nome="Projeto X", fluxo="NAO_SUPER")
        super = ProjetoFactory(nome="Projeto S", fluxo="SUPER")
        outro = ProjetoFactory(nome="Projeto Y", fluxo="NAO_SUPER")
        superativar = ProjetoFactory(nome="Superativar", fluxo="SUPER")
        sup_ling = ProjetoFactory(nome="Superativar Linguagens", fluxo="SUPER")
        sup_mat = ProjetoFactory(nome="Superativar Matemática", fluxo="SUPER")

    return _M


def _sol(**kw: str) -> dict[str, str]:
    base = {
        "evento_id": "EV1",
        "municipio": "Cidade X",
        "uf": "CE",
        "projeto": "Projeto X",
        "disciplina": "",
        "tipo_evento": "Formacao",
        "data": FUTURO_ISO,
        "hora_inicio": "08:00",
        "hora_fim": "12:00",
        "segmento": "3º ano",
        "solicitante_cpf": _CPF_COORD,
        "cancelado": "",
        "evento_ids_anteriores": "[]",
        "segmento_norm": "",
        "linha_completa": "true",
        "aprovado": "",
        "na_agenda_google": "",
        "external_event_id": "",
        "external_event_id_confianca": "",
    }
    base.update(kw)
    return base


def _part(evento_id: str, cpf: str = _CPF_F1, role: str = "FORMADOR", nome: str = "") -> dict[str, str]:
    return {
        "evento_id": evento_id,
        "usuario": nome,
        "usuario_cpf": cpf,
        "usuario_email": "",
        "role": role,
        "match_procedencia": "cpf" if cpf else "",
    }


def _csv(cols: list[str], rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


_seq = iter(range(1, 10_000))


def _export(tmp_path, sols: list[dict[str, str]], parts: list[dict[str, str]] | None = None) -> str:
    d = tmp_path / f"x{next(_seq)}"
    d.mkdir()
    parts = parts if parts is not None else []
    (d / "solicitacao.csv").write_text(_csv(_SOL_COLS, sols), encoding="utf-8")
    (d / "participation.csv").write_text(_csv(_PART_COLS, parts), encoding="utf-8")
    entities = {
        "solicitacao": {"file_csv": "solicitacao.csv", "rows": len(sols)},
        "participation": {"file_csv": "participation.csv", "rows": len(parts)},
    }
    (d / "manifest.json").write_text(json.dumps({"entities": entities}), encoding="utf-8")
    return str(d)


def _virada(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, mode="virada", apply=True, allow=("solicitacao", "participation")).run()


def _dry(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, mode="virada").run()["por_entidade"]["solicitacao"]["virada"]


def _aware(dia: date, h: int, mi: int = 0) -> datetime:
    return timezone.make_aware(datetime.combine(dia, time(h, mi)), _FORTALEZA)


def _existente(
    m,
    ext: str = "EV1",
    *,
    projeto=None,
    dia: date = FUTURO,
    horas: tuple[int, int] = (8, 12),
    status: str = "aprovado",
    formadores: tuple[Usuario, ...] = (),
    **kw: Any,
) -> Solicitacao:
    s = Solicitacao.objects.create(
        usuario=m.coord,
        coordenador=m.coord,
        municipio=Municipio.objects.get(nome="Cidade X"),
        projeto=projeto or m.nao_super,
        tipo_evento=TipoEvento.objects.get(),
        inicio=_aware(dia, horas[0]),
        fim=_aware(dia, horas[1]),
        status=status,
        external_hash=ext,
        segmento="3º ano",
        **kw,
    )
    Participation.objects.create(solicitacao=s, usuario=m.coord, role="COORDENADOR")
    for f in formadores:
        Participation.objects.create(solicitacao=s, usuario=f, role="FORMADOR")
    return s


def _formadores(s: Solicitacao) -> set[str]:
    return set(Participation.objects.filter(solicitacao=s, role="FORMADOR").values_list("usuario__username", flat=True))


def _log_tela(s: Solicitacao, action: str = "UPDATE", sid: Any = None, **details: Any) -> None:
    AuditLog.objects.create(
        usuario=None,
        action=action,
        model_name="Solicitacao",
        details={"solicitacao_id": s.id if sid is None else sid, "ip_address": _ADMIN_IP, **details},
    )


def _hora(s: Solicitacao) -> tuple[int, int]:
    s.refresh_from_db()
    ini = timezone.localtime(s.inicio, _FORTALEZA)
    fim = timezone.localtime(s.fim, _FORTALEZA)
    return ini.hour, fim.hour


# ---------- 1. create-only não mexe em evento existente ----------
def test_01_create_only_com_csv_divergente_nao_muda_nada(tmp_path, m):
    s = _existente(m, formadores=(m.f1,))
    path = _export(
        tmp_path,
        [_sol(hora_inicio="09:00", cancelado="true", na_agenda_google="true")],
        [_part("EV1", _CPF_F2)],
    )
    ExportContractImporter(path=path, apply=True, allow=("solicitacao", "participation")).run()
    assert _hora(s) == (8, 12)
    assert s.status == "aprovado"
    assert _formadores(s) == {"form1"}
    assert s.publicado_fora_do_sistema is False


# ---------- 2. dry-run espelha o apply ----------
def test_02_dry_run_nao_escreve_e_conta_igual_ao_apply(tmp_path, m):
    a = _existente(m, "EV1", formadores=(m.f1,))
    b = _existente(m, "EV2", projeto=m.super)
    c = _existente(m, "EV3", status="pendente")
    _log_tela(c)
    rows = [
        _sol(evento_id="EV1", hora_inicio="09:00"),
        _sol(evento_id="EV2", projeto="Projeto S", cancelado="true"),
        _sol(evento_id="EV3", hora_inicio="10:00"),
        _sol(evento_id="EV9", na_agenda_google="true"),
    ]
    path = _export(tmp_path, rows, [_part("EV1", _CPF_F2)])
    n_logs = AuditLog.objects.count()

    dry = _dry(path)
    assert AuditLog.objects.count() == n_logs
    assert _hora(a) == (8, 12) and _formadores(a) == {"form1"}
    b.refresh_from_db()
    assert b.status == "aprovado"
    assert Solicitacao.objects.count() == 3

    report = _virada(path)
    assert report["virada_aplicada"] == dry
    assert dry["tocado_pessoa"] == 1
    assert dry["cancelado_vira_reprovado"] == 1
    assert dry["would_update_virada"]["horario"] == 1
    assert dry["would_update_virada"]["formadores"] == 1


# ---------- 3. não tocado recebe a planilha ----------
def test_03_nao_tocado_hora_mudada_atualiza_com_auditlog_sem_ip(tmp_path, m):
    s = _existente(m)
    report = _virada(_export(tmp_path, [_sol(hora_inicio="09:00", hora_fim="11:00")]))
    assert _hora(s) == (9, 11)
    assert report["applied"]["solicitacao__virada_atualizada"] == 1
    log = AuditLog.objects.get(action="UPDATE", details__modo="virada")
    assert log.details["origem"] == "import_export_contract"
    assert log.details["solicitacao_id"] == s.id
    assert set(log.details["changed_fields"]) == {"inicio", "fim"}
    assert "ip_address" not in log.details


# ---------- 4/5. tocado por pessoa ----------
def test_04_auditlog_de_edicao_com_ip_trava(tmp_path, m):
    s = _existente(m)
    _log_tela(s)
    path = _export(tmp_path, [_sol(hora_inicio="09:00")])
    assert _dry(path)["tocado_pessoa"] == 1
    _virada(path)
    assert _hora(s) == (8, 12)


def test_05_logentry_do_admin_trava(tmp_path, m):
    s = _existente(m)
    LogEntry.objects.create(
        user=UsuarioFactory(username="admin_x", email="admin_x@example.invalid"),
        content_type=ContentType.objects.get_for_model(Solicitacao),
        object_id=str(s.id),
        object_repr="x",
        action_flag=CHANGE,
    )
    _virada(_export(tmp_path, [_sol(hora_inicio="09:00")]))
    assert _hora(s) == (8, 12)


def test_05b_logentry_do_admin_numa_participacao_do_evento_trava(tmp_path, m):
    s = _existente(m, formadores=(m.f1,))
    p = Participation.objects.get(solicitacao=s, role="FORMADOR")
    LogEntry.objects.create(
        user=UsuarioFactory(username="admin_y", email="admin_y@example.invalid"),
        content_type=ContentType.objects.get_for_model(Participation),
        object_id=str(p.id),
        object_repr="x",
        action_flag=CHANGE,
    )
    _virada(_export(tmp_path, [_sol(hora_inicio="09:00")]))
    assert _hora(s) == (8, 12)


def test_06_auditlog_do_proprio_importador_nao_conta(tmp_path, m):
    s = _existente(m)
    for action, extra in (("UPDATE", {"campo": "external_hash", "de": "EV0", "para": "EV1"}), ("REJECT", {})):
        AuditLog.objects.create(
            action=action,
            model_name="Solicitacao",
            details={"solicitacao_id": s.id, "origem": "import_export_contract", **extra},
        )
    _virada(_export(tmp_path, [_sol(hora_inicio="09:00")]))
    assert _hora(s) == (9, 12)


def test_06b_aprovacao_pela_tela_nao_trava_os_dados(tmp_path, m):
    """Decisão 6 do dono: só edição pela tela trava. A aprovação com ip não conta como 'mexeu'."""
    s = _existente(m, projeto=m.super)
    _log_tela(s, action="APPROVE")
    _virada(_export(tmp_path, [_sol(projeto="Projeto S", hora_inicio="09:00")]))
    assert _hora(s) == (9, 12)
    assert s.status == "pendente", "SUPER aprovado com data mudada volta para pendente (decisão 2)"


# ---------- 7. script trava só os campos que mudou ----------
def test_07_script_que_mudou_o_projeto_trava_so_o_projeto(tmp_path, m):
    s = _existente(m, projeto=m.superativar)
    AuditLog.objects.create(
        action="UPDATE",
        model_name="Solicitacao",
        details={"script": "acerta_normalizar", "solicitacao_id": s.id, "campo": "projeto_id", "de": 1, "para": 2},
    )
    _virada(_export(tmp_path, [_sol(projeto="Superativar", disciplina="LING", hora_inicio="09:00")]))
    assert _hora(s) == (9, 12), "horário não foi mexido pelo script: recebe a planilha"
    assert s.projeto_id == m.superativar.id, "projeto foi mexido pelo script: fica"


def test_07b_script_sem_campo_trava_todos_os_dados_mas_nao_o_status(tmp_path, m):
    s = _existente(m)
    AuditLog.objects.create(
        action="UPDATE", model_name="Solicitacao", details={"script": "x", "motivo": "y", "solicitacao_id": s.id}
    )
    path = _export(tmp_path, [_sol(hora_inicio="09:00", cancelado="true")])
    assert _dry(path)["tocado_script"] == 1
    _virada(path)
    assert _hora(s) == (8, 12)
    assert s.status == "reprovado", "o script não trava o status: cancelado vira reprovado"


# ---------- 8/28. publicado pelo sistema ----------
@pytest.mark.parametrize(
    "rastro",
    [
        {"gcal_status": "PUBLISHED"},
        {"external_event_id": "asv2x"},
        {"last_sync_action": "DELETE"},
        {"gcal_last_sync_at": timezone.make_aware(datetime(2026, 10, 1, 10, 0))},
    ],
)
def test_08_28_publicado_pelo_sistema_nao_muda(tmp_path, m, rastro):
    s = _existente(m, **rastro)
    path = _export(tmp_path, [_sol(hora_inicio="09:00", cancelado="true")])
    assert _dry(path)["publicado_pelo_sistema"] == 1
    _virada(path)
    assert _hora(s) == (8, 12)
    assert s.status == "aprovado"
    assert s.publicado_fora_do_sistema is False


# ---------- 9. cancelado ----------
def test_09_cancelado_vira_reprovado_e_descancelado_so_conta(tmp_path, m):
    pend = _existente(m, "EV1", status="pendente", projeto=m.super)
    apr = _existente(m, "EV2")
    rep = _existente(m, "EV3", status="reprovado")
    AuditLog.objects.create(
        action="REJECT",
        model_name="Solicitacao",
        details={"solicitacao_id": rep.id, "origem": "import_export_contract", "motivo": "cancelado_na_planilha"},
    )
    rows = [
        _sol(evento_id="EV1", projeto="Projeto S", cancelado="true"),
        _sol(evento_id="EV2", cancelado="true"),
        _sol(evento_id="EV3", cancelado="false"),
    ]
    path = _export(tmp_path, rows)
    assert _dry(path)["descancelado"] == 1
    _virada(path)
    for s, antes in ((pend, "pendente"), (apr, "aprovado")):
        s.refresh_from_db()
        assert s.status == "reprovado"
        log = AuditLog.objects.get(action="REJECT", details__solicitacao_id=s.id)
        assert log.details["motivo"] == "cancelado_na_planilha"
        assert log.details["status_anterior"] == antes
    rep.refresh_from_db()
    assert rep.status == "reprovado"


# ---------- 10/11/23. PA-01 e mudança material ----------
def test_10_super_pendente_com_aprovado_true_segue_pendente(tmp_path, m):
    s = _existente(m, status="pendente", projeto=m.super)
    _virada(_export(tmp_path, [_sol(projeto="Projeto S", aprovado="true", hora_inicio="09:00")]))
    s.refresh_from_db()
    assert s.status == "pendente"
    assert not AuditLog.objects.filter(action="APPROVE").exists()


def test_11_super_aprovado_com_data_mudada_volta_para_pendente(tmp_path, m):
    s = _existente(m, projeto=m.super)
    _virada(_export(tmp_path, [_sol(projeto="Projeto S", aprovado="true", data="2026-11-06")]))
    s.refresh_from_db()
    assert s.status == "pendente"
    log = AuditLog.objects.get(action="UPDATE", details__modo="virada")
    assert log.details["changed_fields"]["status"] == {"old": "aprovado", "new": "pendente"}
    assert set(log.details["reaprovacao"]["campos"]) >= {"inicio", "fim"}
    assert log.details["aprovada_como_super"] is True


def test_11b_nao_super_aprovado_com_data_mudada_segue_aprovado(tmp_path, m):
    s = _existente(m)
    _virada(_export(tmp_path, [_sol(data="2026-11-06")]))
    s.refresh_from_db()
    assert s.status == "aprovado"


def test_23_super_aprovado_so_com_formador_trocado_volta_para_pendente(tmp_path, m):
    s = _existente(m, projeto=m.super, formadores=(m.f1,))
    _virada(_export(tmp_path, [_sol(projeto="Projeto S")], [_part("EV1", _CPF_F2)]))
    s.refresh_from_db()
    assert s.status == "pendente"
    log = AuditLog.objects.get(action="UPDATE", details__modo="virada")
    assert "formador_ids" in log.details["changed_fields"]
    assert set(log.details["changed_fields"]["formador_ids"]["new"]) == {m.f2.id}


# ---------- 12/29. projeto só pela disciplina ----------
def test_12_disciplina_move_do_agrupador_para_o_irmao(tmp_path, m):
    s = _existente(m, projeto=m.superativar, status="pendente")
    _virada(_export(tmp_path, [_sol(projeto="Superativar", disciplina="LING")]))
    s.refresh_from_db()
    assert s.projeto_id == m.sup_ling.id


def test_12b_disciplina_troca_entre_irmaos(tmp_path, m):
    s = _existente(m, projeto=m.sup_mat, status="pendente")
    _virada(_export(tmp_path, [_sol(projeto="Superativar", disciplina="LING")]))
    s.refresh_from_db()
    assert s.projeto_id == m.sup_ling.id


def test_12c_projeto_diferente_sem_disciplina_nao_troca_e_conta(tmp_path, m):
    s = _existente(m)
    path = _export(tmp_path, [_sol(projeto="Projeto Y")])
    assert _dry(path)["projeto_diverge"] == 1
    _virada(path)
    s.refresh_from_db()
    assert s.projeto_id == m.nao_super.id


def test_29_petrolina_projeto_decidido_pelo_dono_fica(tmp_path, m):
    miudezas = ProjetoFactory(nome="Projeto Miudezas e Descobertas", fluxo="NAO_SUPER")
    ProjetoFactory(nome="UNI DUNI TÊ", fluxo="NAO_SUPER")
    s = _existente(m, projeto=miudezas)
    path = _export(tmp_path, [_sol(projeto="UNI DUNI TÊ")])
    assert _dry(path)["projeto_diverge"] == 1
    _virada(path)
    s.refresh_from_db()
    assert s.projeto_id == miudezas.id


# ---------- 13/24/25. formadores ----------
def test_13_formador_trocado_sai_o_antigo_entra_o_novo(tmp_path, m):
    s = _existente(m, formadores=(m.f1, m.f3))
    Participation.objects.filter(solicitacao=s, usuario=m.f3).update(ch_horas=Decimal("4.00"))
    path = _export(tmp_path, [_sol()], [_part("EV1", _CPF_F2), _part("EV1", _CPF_COORD, "COORDENADOR")])
    assert _dry(path)["remocao_bloqueada"] == 1
    _virada(path)
    assert _formadores(s) == {"form2", "form3"}, "f1 sai, f2 entra, f3 tem horas lançadas e fica"
    assert Participation.objects.filter(solicitacao=s, usuario=m.coord, role="COORDENADOR").exists()


def test_13b_formador_avaliado_nao_sai(tmp_path, m):
    s = _existente(m, formadores=(m.f1,), pretende_avaliar_formador=True)
    s.formador_avaliado = m.f1
    s.save(update_fields=["formador_avaliado"])
    _virada(_export(tmp_path, [_sol()], [_part("EV1", _CPF_F2)]))
    assert _formadores(s) == {"form1", "form2"}


def test_13c_convidado_so_acrescenta(tmp_path, m):
    s = _existente(m, formadores=(m.f1,))
    Participation.objects.create(solicitacao=s, usuario=m.f3, role="CONVIDADO")
    _virada(_export(tmp_path, [_sol()], [_part("EV1", _CPF_F1), _part("EV1", _CPF_F2, "CONVIDADO")]))
    convidados = set(
        Participation.objects.filter(solicitacao=s, role="CONVIDADO").values_list("usuario__username", flat=True)
    )
    assert convidados == {"form2", "form3"}


def test_13d_formador_inativo_nao_entra_em_evento_futuro(tmp_path, m):
    s = _existente(m, formadores=(m.f1,))
    path = _export(tmp_path, [_sol()], [_part("EV1", _CPF_F1), _part("EV1", _CPF_INATIVO)])
    assert _dry(path)["formador_inativo"] == 1
    _virada(path)
    assert _formadores(s) == {"form1"}


def test_24_coord_acompanha_continua(tmp_path, m):
    s = _existente(m, formadores=(m.f1,))
    Participation.objects.create(solicitacao=s, usuario=m.f3, role="COORD_ACOMPANHA")
    _virada(_export(tmp_path, [_sol()], [_part("EV1", _CPF_F2)]))
    assert Participation.objects.filter(solicitacao=s, usuario=m.f3, role="COORD_ACOMPANHA").exists()


def test_25_sem_linha_formador_ninguem_sai(tmp_path, m):
    s = _existente(m, formadores=(m.f1,))
    _virada(_export(tmp_path, [_sol()], [_part("EV1", _CPF_COORD, "COORDENADOR")]))
    assert _formadores(s) == {"form1"}


def test_25b_formador_que_nao_resolve_bloqueia_a_saida(tmp_path, m):
    s = _existente(m, formadores=(m.f1,))
    parts = [_part("EV1", _CPF_F2), _part("EV1", "", nome="Pessoa Sem Cadastro")]
    path = _export(tmp_path, [_sol()], parts)
    assert _dry(path)["remocao_bloqueada_resolucao"] == 1
    _virada(path)
    assert _formadores(s) == {"form1", "form2"}, "ninguém sai; o nome solto não entra"
    assert not Participation.objects.filter(solicitacao=s, guest_nome="Pessoa Sem Cadastro").exists()


# ---------- 14. passado novo ----------
def test_14_passado_novo_e_criado_no_modo_virada(tmp_path, m):
    rows = [
        _sol(evento_id="EVS", projeto="Projeto S", data=PASSADO_ISO),
        _sol(evento_id="EVN", data=PASSADO_ISO),
        _sol(evento_id="EVC", data=PASSADO_ISO, cancelado="true"),
    ]
    report = _virada(_export(tmp_path, rows, [_part("EVN", _CPF_F1)]))
    assert report["applied"]["solicitacao"] == 3
    status = dict(Solicitacao.objects.values_list("external_hash", "status"))
    assert status == {"EVS": "pendente", "EVN": "aprovado", "EVC": "reprovado"}
    assert _formadores(Solicitacao.objects.get(external_hash="EVN")) == {"form1"}


# ---------- 15. segunda execução ----------
def test_15_segunda_execucao_nao_muda_nada(tmp_path, m):
    s = _existente(m, projeto=m.super, formadores=(m.f1,))
    rows = [_sol(projeto="Projeto S", hora_inicio="09:00", na_agenda_google="true"), _sol(evento_id="EVN")]
    path = _export(tmp_path, rows, [_part("EV1", _CPF_F2), _part("EVN", _CPF_F1)])
    _virada(path)
    n_logs, n_part = AuditLog.objects.count(), Participation.objects.count()
    s.refresh_from_db()
    antes = (s.inicio, s.status, s.projeto_id, s.publicado_fora_do_sistema)
    report = _virada(path)
    s.refresh_from_db()
    assert (s.inicio, s.status, s.projeto_id, s.publicado_fora_do_sistema) == antes
    assert (AuditLog.objects.count(), Participation.objects.count()) == (n_logs, n_part)
    assert report["applied"].get("solicitacao__virada_atualizada", 0) == 0
    assert report["applied"]["solicitacao"] == 0


# ---------- 18. a carga não chama o Google ----------
def test_18_carga_nao_chama_o_google(tmp_path, m):
    _existente(m, projeto=m.super, formadores=(m.f1,))
    rows = [_sol(projeto="Projeto S", hora_inicio="09:00", na_agenda_google="true"), _sol(evento_id="EVN")]
    path = _export(tmp_path, rows, [_part("EV1", _CPF_F2)])
    with (
        patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task,
        patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id") as factory,
    ):
        _virada(path)
    assert task.call_count == 0 and factory.call_count == 0


# ---------- 22. rollback ----------
def test_22_erro_no_meio_desfaz_tudo(tmp_path, m, monkeypatch):
    s = _existente(m)
    path = _export(tmp_path, [_sol(hora_inicio="09:00"), _sol(evento_id="EVN")])

    def _explode(self, rows):
        raise RuntimeError("falha no meio")

    monkeypatch.setattr(ExportContractImporter, "_apply_participation", _explode)
    with pytest.raises(RuntimeError):
        _virada(path)
    assert _hora(s) == (8, 12)
    assert not Solicitacao.objects.filter(external_hash="EVN").exists()
    assert not AuditLog.objects.filter(details__modo="virada").exists()


# ---------- 26. linha incompleta ----------
def test_26_linha_incompleta_e_cancelada_reprova_sem_mudar_o_resto(tmp_path, m):
    s = _existente(m)
    linha = _sol(linha_completa="false", hora_inicio="", hora_fim="", cancelado="true", projeto="Projeto Y")
    path = _export(tmp_path, [linha])
    assert _dry(path)["existente_linha_incompleta"] == {"linha_incompleta": 1}
    _virada(path)
    assert _hora(s) == (8, 12)
    assert s.status == "reprovado"
    assert s.projeto_id == m.nao_super.id


# ---------- 27. regra do ip ----------
def test_27_ip_none_e_script(tmp_path, m):
    s = _existente(m)
    AuditLog.objects.create(
        action="APPROVE",
        model_name="Solicitacao",
        details={"solicitacao_id": s.id, "ip_address": None, "script": "pendentes16_resolver"},
    )
    AuditLog.objects.create(
        action="UPDATE",
        model_name="Solicitacao",
        details={"solicitacao_id": s.id, "ip_address": None, "script": "x"},
    )
    path = _export(tmp_path, [_sol(hora_inicio="09:00")])
    dry = _dry(path)
    assert dry["tocado_script"] == 1 and dry["tocado_pessoa"] == 0
    _virada(path)
    assert _hora(s) == (8, 12), "UPDATE de script sem campo trava os dados"


def test_27b_preview_com_ip_nao_trava(tmp_path, m):
    s = _existente(m)
    _log_tela(s, action="PREVIEW_GCAL")
    _virada(_export(tmp_path, [_sol(hora_inicio="09:00")]))
    assert _hora(s) == (9, 12)


def test_27c_solicitacao_id_em_texto_trava(tmp_path, m):
    s = _existente(m)
    _log_tela(s, sid=str(s.id))
    _virada(_export(tmp_path, [_sol(hora_inicio="09:00")]))
    assert _hora(s) == (8, 12)


def test_27d_resumo_com_lista_de_solicitacoes_trava(tmp_path, m):
    s = _existente(m)
    AuditLog.objects.create(
        action="UPDATE", model_name="Solicitacao", details={"script": "y", "solicitacoes": [s.id], "motivo": "z"}
    )
    _virada(_export(tmp_path, [_sol(hora_inicio="09:00")]))
    assert _hora(s) == (8, 12)


# ---------- 30. não recria apagado ----------
@pytest.mark.parametrize("modo", ["virada", "create-only"])
def test_30_evento_apagado_no_sistema_nao_volta(tmp_path, m, modo):
    AuditLog.objects.create(
        action="DELETE",
        model_name="Solicitacao",
        details={"solicitacao_data": {"id": 1, "external_hash": "EVT"}, "ip_address": _ADMIN_IP},
    )
    AuditLog.objects.create(
        action="DELETE",
        model_name="Solicitacao",
        details={"script": "pendentes16_resolver", "evento_id": "EVS", "backup": {"external_hash": "EVS"}},
    )
    AuditLog.objects.create(
        action="DELETE", model_name="Solicitacao", details={"script": "z", "backup": {"external_hash": "EVP"}}
    )
    rows = [_sol(evento_id="EVT"), _sol(evento_id="EVS"), _sol(evento_id="EVP", data=PASSADO_ISO)]
    path = _export(tmp_path, rows)
    tally = ExportContractImporter(path=path, mode=modo).run()["por_entidade"]["solicitacao"]
    assert tally["skip_reasons"]["apagado_no_sistema"] == 3
    ExportContractImporter(path=path, mode=modo, apply=True, allow=("solicitacao", "participation")).run()
    assert Solicitacao.objects.count() == 0


def _apagar_pela_tela_retrato_antigo(m, ext: str, dia: date) -> None:
    """DELETE pela tela antes do retrato com `external_hash`: só id, município, projeto, início, fim e status."""
    s = _existente(m, ext, dia=dia)
    AuditLog.objects.create(
        action="DELETE",
        model_name="Solicitacao",
        details={
            "solicitacao_data": {
                "id": s.id,
                "municipio_id": s.municipio_id,
                "projeto_id": s.projeto_id,
                "inicio": s.inicio.isoformat(),
                "fim": s.fim.isoformat(),
                "status": s.status,
            },
            "ip_address": _ADMIN_IP,
        },
    )
    s.delete()


@pytest.mark.parametrize(
    "modo,dia",
    [("virada", FUTURO), ("virada", PASSADO), ("create-only", FUTURO)],
)
def test_30b_retrato_antigo_sem_external_hash_nao_recria(tmp_path, m, modo, dia):
    _apagar_pela_tela_retrato_antigo(m, "EVDEL", dia)
    rows = [
        _sol(evento_id="EVDEL", data=dia.isoformat()),
        _sol(evento_id="EVOUTRO", hora_inicio="13:00", hora_fim="17:00"),
    ]
    path = _export(tmp_path, rows)
    tally = ExportContractImporter(path=path, mode=modo).run()["por_entidade"]["solicitacao"]
    assert tally["skip_reasons"]["apagado_no_sistema"] == 1
    ExportContractImporter(path=path, mode=modo, apply=True, allow=("solicitacao", "participation")).run()
    assert set(Solicitacao.objects.values_list("external_hash", flat=True)) == {"EVOUTRO"}


def test_30c_apagado_pelo_admin_entra_num_contador(tmp_path, m):
    from django.contrib.admin.models import DELETION

    s = _existente(m, "EVADM")
    LogEntry.objects.create(
        user_id=m.coord.id,
        content_type_id=ContentType.objects.get_for_model(Solicitacao).id,
        object_id=str(s.id),
        object_repr=str(Solicitacao.objects.get(id=s.id)),  # como o admin: lido do banco, início em UTC
        action_flag=DELETION,
    )
    s.delete()
    rows = [_sol(evento_id="EVADM"), _sol(evento_id="EVOUTRO", hora_inicio="13:00", hora_fim="17:00")]
    tally = ExportContractImporter(path=_export(tmp_path, rows), mode="virada").run()["por_entidade"]["solicitacao"]
    assert tally["possivel_apagado_pelo_admin"] == 1


# ---------- 31. remarcado por script ----------
def test_31_remarcado_por_script_recebe_formadores_e_fica_com_data(tmp_path, m):
    s = _existente(m, "EVNOVO", formadores=(m.f1,), horas=(13, 17))
    AuditLog.objects.create(
        action="UPDATE",
        model_name="Solicitacao",
        details={
            "script": "remarcados_v38_acertar",
            "solicitacao_id": s.id,
            "de": {"external_hash": "EVVELHO", "inicio": "x", "fim": "y", "projeto_id": 1},
            "para": {"external_hash": "EVNOVO", "inicio": "x2", "fim": "y2", "projeto_id": 2},
        },
    )
    _virada(_export(tmp_path, [_sol(evento_id="EVNOVO", projeto="Projeto Y")], [_part("EVNOVO", _CPF_F2)]))
    assert _formadores(s) == {"form2"}
    assert _hora(s) == (13, 17)
    assert s.projeto_id == m.nao_super.id


# ---------- 32. cache ----------
def test_32_apply_invalida_o_cache_de_disponibilidade_no_commit(tmp_path, m, django_capture_on_commit_callbacks):
    _existente(m)
    path = _export(tmp_path, [_sol(data="2026-11-06")])
    with patch.object(export_contract_importer, "invalidate_availability_cache") as inval:
        with django_capture_on_commit_callbacks(execute=True):
            _virada(path)
    inval.assert_called_with(None)


# ---------- 34. comando ----------
def test_34_comando_virada_com_allowlist_aplica(tmp_path, m):
    s = _existente(m)
    path = _export(tmp_path, [_sol(hora_inicio="09:00")])
    out = io.StringIO()
    call_command(
        "import_export_contract",
        "--path",
        path,
        "--mode",
        "virada",
        "--apply",
        "--allow-entity",
        "solicitacao",
        "--allow-entity",
        "participation",
        "--json",
        stdout=out,
    )
    report = json.loads(out.getvalue())
    assert report["applied"], "o modo virada tem de gravar e dizer o que gravou"
    assert report["applied"]["solicitacao__virada_atualizada"] == 1
    assert _hora(s) == (9, 12)


@pytest.mark.parametrize(
    "args",
    [
        ["--mode", "virada", "--apply", "--allow-entity", "solicitacao"],
        ["--mode", "virada", "--apply", "--allow-entity", "participation", "--allow-entity", "solicitacao"]
        + ["--allow-entity", "gcal_adocao"],
        ["--apply", "--allow-entity", "gcal_adocao"],
    ],
)
def test_34b_comando_recusa_allowlist_invalida(tmp_path, m, args):
    with pytest.raises(CommandError):
        call_command("import_export_contract", "--path", _export(tmp_path, [_sol()]), *args)


# ---------- 35. marca publicado_fora_do_sistema ----------
def test_35_na_agenda_google_sem_event_id_marca_e_publicar_recusa(tmp_path, m):
    tocado = _existente(m, "EV1")
    _log_tela(tocado)
    rows = [
        _sol(evento_id="EV1", na_agenda_google="true"),
        _sol(evento_id="EVN", na_agenda_google="true"),
        _sol(evento_id="EVE", external_event_id="0a1b2c3d4e5f6g7h8i9j0k1l2m", external_event_id_confianca="media"),
        _sol(evento_id="EVF"),
    ]
    _virada(_export(tmp_path, rows))
    marca = dict(Solicitacao.objects.values_list("external_hash", "publicado_fora_do_sistema"))
    assert marca == {"EV1": True, "EVN": True, "EVE": True, "EVF": False}, "a marca vale mesmo no tocado por pessoa"
    assert motivo_nao_publicavel(Solicitacao.objects.get(external_hash="EVN")) == "publicado_fora_do_sistema"


# ---------- extras ----------
def test_fim_antes_do_inicio_nao_muda_o_horario(tmp_path, m):
    s = _existente(m)
    path = _export(tmp_path, [_sol(hora_inicio="12:00", hora_fim="09:00")])
    assert _dry(path)["fim_antes_do_inicio"] == 1
    _virada(path)
    assert _hora(s) == (8, 12)


def test_fora_do_escopo_so_conta(tmp_path, m):
    s = _existente(m)
    path = _export(tmp_path, [_sol(municipio="Cidade Y", segmento="5º ano")])
    assert _dry(path)["fora_do_escopo"] == {"municipio": 1, "segmento": 1}
    _virada(path)
    s.refresh_from_db()
    assert s.municipio.nome == "Cidade X" and s.segmento == "3º ano"


def test_existente_fora_do_csv_conta(tmp_path, m):
    _existente(m, "EVSUMIU", status="pendente")
    _existente(m, "EVVELHO")
    rows = [_sol(evento_id="EVNOVO", evento_ids_anteriores='["EVVELHO"]')]
    tally = ExportContractImporter(path=_export(tmp_path, rows), mode="virada").run()["por_entidade"]["solicitacao"]
    assert tally["existente_fora_do_csv"] == {"futuro:pendente:nao_tocado": 1}


def test_34c_comando_virada_em_texto_mostra_os_contadores(tmp_path, m):
    _existente(m)
    path = _export(tmp_path, [_sol(hora_inicio="09:00", external_event_id="x" * 26)])
    out = io.StringIO()
    call_command("import_export_contract", "--path", path, "--mode", "virada", stdout=out)
    texto = out.getvalue()
    assert "[solicitacao] virada=" in texto
    assert "[gcal_adocao] rows=1" in texto
