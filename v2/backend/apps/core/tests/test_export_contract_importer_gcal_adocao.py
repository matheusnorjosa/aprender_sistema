"""Adoção do Event ID do Google (`gcal_adocao`, plano do importador da virada, 16/10/2026, §4).

Roda à parte, depois da carga e do A5, lendo o mesmo solicitacao.csv. Só adota `confianca=alta`, de
evento aprovado, marcado `publicado_fora_do_sistema`, sem rastro de publicação pelo sistema, com Event ID
que nenhum outro evento tem; o evento mexido por alguém só entra com data, hora e formadores iguais aos
da planilha. NÃO grava o hash do payload: o Google pode ter outro horário, e o primeiro Reapply depois da
virada manda o UPDATE pelo id adotado (decisão do dono de 20/10, relay 65). A adoção nunca chama o Google:
só grava o id que o `conferir_gcal_adocao` achou confirmado e na mesma data no Google, há menos de 24 h
(decisão D63, 20/10); o resto fica com a marca.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportArgumentType=false

from __future__ import annotations

import io
import json
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

import pytest

from apps.core.models import AuditLog
from apps.core.models.solicitacao import Solicitacao
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.services.gcal.payload import build_event_payload
from apps.core.services.gcal.sync import apply_one_solicitacao
from apps.core.services.gcal.utils import _payload_hash
from apps.core.tests.test_export_contract_importer_virada import (  # noqa: F401 (fixtures)
    _CPF_F1,
    _CPF_F2,
    FUTURO,
    _existente,
    _export,
    _log_tela,
    _part,
    _sol,
    hoje_fixo,
    m,
)

pytestmark = pytest.mark.django_db

EID = "0a1b2c3d4e5f6g7h8i9j0k1l2m"
EID2 = "1b2c3d4e5f6g7h8i9j0k1l2m3n"


def _linha(**kw: str) -> dict[str, str]:
    base = {"external_event_id": EID, "external_event_id_confianca": "alta", "na_agenda_google": "true"}
    base.update(kw)
    return _sol(**base)


def _conferido(*sols: Solicitacao, eid: str = EID, quando: datetime | None = None) -> dict[str, dict[str, str]]:
    """O arquivo do `conferir_gcal_adocao`: estes eventos conferidos no Google com o id `eid`."""
    em = (quando or timezone.now()).isoformat()
    return {str(s.id): {"event_id": eid, "verificado_em": em, "inicio_google": s.inicio.isoformat()} for s in sols}


def _adocao(path: str, verificado: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    """Adoção com o arquivo da conferência; sem `verificado`, todo evento do banco conferido com EID."""
    if verificado is None:
        verificado = _conferido(*Solicitacao.objects.all())
    return ExportContractImporter(
        path=path, mode="virada", apply=True, allow=("gcal_adocao",), gcal_verificado=verificado
    ).run()


def _dry(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, mode="virada").run()["por_entidade"]["gcal_adocao"]


def _pronto(m, ext: str = "EV1", **kw: Any) -> Solicitacao:
    """Evento depois da carga e do A5: aprovado e marcado como publicado fora do sistema."""
    return _existente(m, ext, publicado_fora_do_sistema=True, **kw)


class _Cliente:
    def __init__(self, store: set[str]) -> None:
        self.store = store
        self.updates: list[str] = []
        self.inserts: list[str] = []

    def get(self, calendar_id, event_id):  # noqa: ARG002
        return {"id": event_id} if event_id in self.store else None

    def insert(self, calendar_id, event_id, payload):  # noqa: ARG002
        self.inserts.append(event_id)
        return {"id": event_id}

    def update(self, calendar_id, event_id, payload):  # noqa: ARG002
        self.updates.append(event_id)
        return {"id": event_id}


# ---------- 16. adoção ----------
def test_16_adota_alta_aprovado_marcado(tmp_path, m):
    s = _pronto(m)
    path = _export(tmp_path, [_linha()])
    assert _dry(path)["would_adopt_gcal"] == 1
    report = _adocao(path)
    assert report["applied"]["gcal_adocao"] == 1
    s.refresh_from_db()
    assert s.external_event_id == EID
    assert s.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert s.last_sync_action == "ADOPT"
    assert s.last_synced_at is not None and s.gcal_last_sync_at is not None
    assert s.publicado_fora_do_sistema is False
    assert s.gcal_payload_hash is None, "sem hash, o próximo Reapply atualiza o Google"
    log = AuditLog.objects.get(action="UPDATE", details__campo="external_event_id")
    assert log.details["origem"] == "import_export_contract"
    assert log.details["para"] == EID
    assert "ip_address" not in log.details


# ---------- 17. recusas ----------
@pytest.mark.parametrize(
    ("linha", "evento", "motivo"),
    [
        ({"external_event_id_confianca": "media"}, {}, "confianca_media"),
        ({"external_event_id_confianca": "colisao"}, {}, "confianca_colisao"),
        ({"external_event_id": ""}, {}, "sem_event_id"),
        ({"cancelado": "true"}, {}, "cancelado"),
        ({}, {"status": "pendente"}, "nao_aprovado"),
        ({}, {"status": "reprovado"}, "nao_aprovado"),
        ({}, {"external_event_id": EID2, "gcal_status": "PUBLISHED"}, "ja_tem_event_id"),
        ({}, {"last_sync_action": "DELETE"}, "publicado_pelo_sistema"),
        ({}, {"publicado_fora_do_sistema": False}, "sem_marca"),
    ],
)
def test_17_adocao_recusada(tmp_path, m, linha, evento, motivo):
    kw = {"publicado_fora_do_sistema": True, **evento}
    s = _existente(m, **kw)
    path = _export(tmp_path, [_linha(**linha)])
    tally = _dry(path)
    assert tally["would_adopt_gcal"] == 0
    assert tally["skip_reasons"][motivo] == 1
    _adocao(path)
    s.refresh_from_db()
    assert s.external_event_id == evento.get("external_event_id")
    assert s.last_sync_action == evento.get("last_sync_action")


def test_17b_event_id_ja_usado_por_outro_evento(tmp_path, m):
    _existente(m, "EVOUTRO", external_event_id=EID, gcal_status="PUBLISHED")
    s = _pronto(m)
    path = _export(tmp_path, [_linha()])
    assert _dry(path)["skip_reasons"]["id_em_outro_evento"] == 1
    _adocao(path)
    s.refresh_from_db()
    assert s.external_event_id is None


def test_17c_tocado_com_data_diferente_nao_adota(tmp_path, m):
    s = _pronto(m, horas=(13, 17))
    _log_tela(s)
    path = _export(tmp_path, [_linha()])
    assert _dry(path)["skip_reasons"]["tocado_com_diferenca"] == 1
    _adocao(path)
    s.refresh_from_db()
    assert s.external_event_id is None and s.publicado_fora_do_sistema is True


def test_17d_tocado_com_formador_diferente_nao_adota(tmp_path, m):
    s = _pronto(m, formadores=(m.f1,))
    _log_tela(s)
    path = _export(tmp_path, [_linha()], [_part("EV1", _CPF_F2)])
    assert _dry(path)["skip_reasons"]["tocado_com_diferenca"] == 1


def test_17f_nao_tocado_que_a_carga_nao_igualou_nao_adota(tmp_path, m):
    """Formador sem cadastro na planilha: a carga não tira ninguém (decisão 5) e o evento fica {f1, f2},
    enquanto o Google (= planilha) tem outros convidados. Adotar gravaria um hash "igual ao sistema"."""
    s = _pronto(m, formadores=(m.f1,))
    parts = [_part("EV1", _CPF_F2), _part("EV1", "", nome="Pessoa Sem Cadastro")]
    path = _export(tmp_path, [_linha()], parts)
    ExportContractImporter(path=path, mode="virada", apply=True, allow=("solicitacao", "participation")).run()
    tally = _dry(path)
    assert tally["would_adopt_gcal"] == 0
    assert tally["skip_reasons"]["diverge_da_planilha"] == 1
    _adocao(path)
    s.refresh_from_db()
    assert s.external_event_id is None and s.publicado_fora_do_sistema is True


def test_17e_tocado_igual_a_planilha_adota(tmp_path, m):
    s = _pronto(m, formadores=(m.f1,))
    _log_tela(s)
    _adocao(_export(tmp_path, [_linha()], [_part("EV1", _CPF_F1)]))
    s.refresh_from_db()
    assert s.external_event_id == EID


# ---------- 15. segunda execução ----------
def test_15_adocao_de_novo_nao_faz_nada(tmp_path, m):
    _pronto(m)
    path = _export(tmp_path, [_linha()])
    _adocao(path)
    n_logs = AuditLog.objects.count()
    report = _adocao(path)
    assert report["applied"]["gcal_adocao"] == 0
    assert AuditLog.objects.count() == n_logs


# ---------- 18. não chama o Google ----------
def test_18_adocao_nao_chama_o_google(tmp_path, m):
    _pronto(m)
    with (
        patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay") as task,
        patch("apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id") as factory,
    ):
        _adocao(_export(tmp_path, [_linha()]))
    assert task.call_count == 0 and factory.call_count == 0


# ---------- 33. o Reapply seguinte atualiza o Google pelo id adotado ----------
def test_33_reapply_depois_da_adocao_faz_update_pelo_id_adotado(tmp_path, m):
    """Caso EV003991: o Google estava com outro horário. O primeiro Reapply manda o UPDATE pelo id adotado
    (sem criar outro evento) e grava o hash; o Reapply seguinte pula."""
    s = _pronto(m, formadores=(m.f1,))
    _adocao(_export(tmp_path, [_linha()], [_part("EV1", _CPF_F1)]))
    s = Solicitacao.objects.get(id=s.id)
    client = _Cliente(store={EID})
    out = apply_one_solicitacao(s, apply_blocked=True, client=client)
    assert out.action == "UPDATE"
    assert client.updates == [EID] and client.inserts == []
    s = Solicitacao.objects.get(id=s.id)
    assert s.external_event_id == EID
    assert s.gcal_payload_hash == _payload_hash(build_event_payload(s, enable_meet=False))
    assert apply_one_solicitacao(s, apply_blocked=True, client=client).action == "SKIP"
    assert client.updates == [EID]


def test_adocao_e_dry_run_por_padrao(tmp_path, m):
    s = _pronto(m)
    ExportContractImporter(path=_export(tmp_path, [_linha()]), mode="virada").run()
    s.refresh_from_db()
    assert s.external_event_id is None
    assert timezone.now()  # sem escrita no dry-run


# ---------- D63. só adota o id conferido no Google ----------
def test_d63_dry_run_sem_arquivo_classifica_e_avisa(tmp_path, m):
    _pronto(m)
    tally = _dry(_export(tmp_path, [_linha()]))
    assert tally["would_adopt_gcal"] == 1
    assert "--gcal-verificado" in tally["nota"]


def test_d63_apply_sem_arquivo_e_command_error(tmp_path, m):
    s = _pronto(m)
    path = _export(tmp_path, [_linha()])
    with pytest.raises(CommandError, match="--gcal-verificado"):
        call_command(
            "import_export_contract", "--path", path, "--mode", "virada", "--apply", "--allow-entity", "gcal_adocao"
        )
    with pytest.raises(ValueError, match="conferir_gcal_adocao"):
        ExportContractImporter(path=path, mode="virada", apply=True, allow=("gcal_adocao",)).run()
    s.refresh_from_db()
    assert s.external_event_id is None and s.publicado_fora_do_sistema is True


def _arquivo_do_caso(caso: str, s: Solicitacao) -> dict[str, dict[str, str]]:
    agora = timezone.now()
    if caso == "ausente":
        return {}
    if caso == "outro_id":
        return _conferido(s, eid=EID2)
    if caso == "vencido":
        return _conferido(s, quando=agora - timedelta(hours=25))
    if caso == "no_futuro":
        return _conferido(s, quando=agora + timedelta(hours=1))
    if caso == "sem_fuso":
        return _conferido(s, quando=agora.replace(tzinfo=None))
    if caso == "data_ilegivel":
        return {str(s.id): {"event_id": EID, "verificado_em": "ontem"}}
    arquivo = _conferido(s)
    inicio_google = {
        "inicio_outra_data": (s.inicio + timedelta(days=1)).isoformat(),
        "inicio_ilegivel": "amanhã cedo",
        "inicio_sem_fuso": s.inicio.replace(tzinfo=None).isoformat(),
    }.get(caso)
    if inicio_google is None:
        del arquivo[str(s.id)]["inicio_google"]
    else:
        arquivo[str(s.id)]["inicio_google"] = inicio_google
    return arquivo


@pytest.mark.parametrize(
    ("caso", "motivo"),
    [
        ("ausente", "sem_conferencia_no_google"),
        ("outro_id", "conferencia_com_outro_id"),
        ("vencido", "conferencia_vencida"),
        ("no_futuro", "conferencia_vencida"),
        ("sem_fuso", "conferencia_vencida"),
        ("data_ilegivel", "conferencia_vencida"),
        ("inicio_outra_data", "conferencia_outra_data"),
        ("inicio_ilegivel", "conferencia_outra_data"),
        ("inicio_sem_fuso", "conferencia_outra_data"),
        ("inicio_ausente", "conferencia_outra_data"),
    ],
)
def test_d63_conferencia_que_nao_bate_nao_adota(tmp_path, m, caso, motivo):
    s = _pronto(m)
    path = _export(tmp_path, [_linha()])
    verificado = _arquivo_do_caso(caso, s)
    dry = ExportContractImporter(path=path, mode="virada", gcal_verificado=verificado).run()
    assert dry["por_entidade"]["gcal_adocao"]["skip_reasons"][motivo] == 1
    report = _adocao(path, verificado)
    assert report["applied"]["gcal_adocao"] == 0
    s.refresh_from_db()
    assert s.external_event_id is None and s.publicado_fora_do_sistema is True
    assert s.gcal_status != Solicitacao.GCalStatus.PUBLISHED


def test_d63_marca_so_sai_dos_adotados(tmp_path, m):
    a = _pronto(m, "EV1")
    b = _pronto(m, "EV2")
    path = _export(tmp_path, [_linha(evento_id="EV1"), _linha(evento_id="EV2", external_event_id=EID2)])
    report = _adocao(path, _conferido(a))
    assert report["applied"]["gcal_adocao"] == 1
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.external_event_id, a.publicado_fora_do_sistema) == (EID, False)
    assert (b.external_event_id, b.publicado_fora_do_sistema) == (None, True)


def test_d63_comando_com_arquivo_adota(tmp_path, m):
    s = _pronto(m)
    path = _export(tmp_path, [_linha()])
    arq = tmp_path / "conferido.json"
    arq.write_text(json.dumps(_conferido(s)), encoding="utf-8")
    out = io.StringIO()
    call_command(
        "import_export_contract",
        *("--path", path, "--mode", "virada", "--apply", "--allow-entity", "gcal_adocao"),
        *("--gcal-verificado", str(arq), "--json"),
        stdout=out,
    )
    assert json.loads(out.getvalue())["applied"]["gcal_adocao"] == 1
    s.refresh_from_db()
    assert s.external_event_id == EID


def test_d63_arquivo_ilegivel_e_command_error(tmp_path, m):
    _pronto(m)
    path = _export(tmp_path, [_linha()])
    arq = tmp_path / "ruim.json"
    arq.write_text("[1, 2", encoding="utf-8")
    for alvo in (str(arq), str(tmp_path / "nao_existe.json")):
        with pytest.raises(CommandError, match="--gcal-verificado"):
            call_command(
                "import_export_contract",
                *("--path", path, "--mode", "virada", "--apply", "--allow-entity", "gcal_adocao"),
                *("--gcal-verificado", alvo),
            )


def test_d63_evento_movido_depois_da_conferencia_nao_adota(tmp_path, m):
    """A conferência aprovou o evento no dia D1; outra carga da virada o moveu para D2 no sistema dentro das
    24 h. O CSV e o sistema dizem D2, mas o Google (conferido) está em D1: a adoção não grava."""
    s = _pronto(m)
    conferido = _conferido(s)
    d2 = (FUTURO + timedelta(days=1)).isoformat()
    path = _export(tmp_path, [_linha(data=d2)])
    ExportContractImporter(path=path, mode="virada", apply=True, allow=("solicitacao", "participation")).run()
    s.refresh_from_db()
    assert timezone.localtime(s.inicio).date().isoformat() == d2
    report = _adocao(path, conferido)
    assert report["applied"]["gcal_adocao"] == 0
    assert report["por_entidade"]["gcal_adocao"]["skip_reasons"]["conferencia_outra_data"] == 1
    s.refresh_from_db()
    assert s.external_event_id is None and s.publicado_fora_do_sistema is True


def test_d63_inicio_google_de_dia_inteiro_na_mesma_data_adota(tmp_path, m):
    s = _pronto(m)
    conferido = _conferido(s)
    conferido[str(s.id)]["inicio_google"] = FUTURO.isoformat()
    assert _adocao(_export(tmp_path, [_linha()]), conferido)["applied"]["gcal_adocao"] == 1
