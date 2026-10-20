"""Adoção do Event ID do Google (`gcal_adocao`, plano do importador da virada, 16/10/2026, §4).

Roda à parte, depois da carga e do A5, lendo o mesmo solicitacao.csv. Só adota `confianca=alta`, de
evento aprovado, marcado `publicado_fora_do_sistema`, sem rastro de publicação pelo sistema, com Event ID
que nenhum outro evento tem; o evento mexido por alguém só entra com data, hora e formadores iguais aos
da planilha. NÃO grava o hash do payload: o Google pode ter outro horário, e o primeiro Reapply depois da
virada manda o UPDATE pelo id adotado (decisão do dono de 20/10, relay 65). A adoção nunca chama o Google.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportArgumentType=false

from __future__ import annotations

from typing import Any
from unittest.mock import patch

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


def _adocao(path: str) -> dict[str, Any]:
    return ExportContractImporter(path=path, mode="virada", apply=True, allow=("gcal_adocao",)).run()


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
