"""`conferir_gcal_adocao`: confere no Google, só lendo, os Event IDs que a adoção da virada gravaria.

Decisão do dono D63 (20/10/2026): a adoção só grava o id depois de conferir no Google que o evento existe,
está confirmado e tem a mesma data (em America/Fortaleza). O comando monta os mesmos candidatos do
`gcal_adocao`, faz só GET de cada id e grava o arquivo que o `--gcal-verificado` da adoção exige. Erro de
leitura não aprova (falha fechada). Cliente Google falso: nada de rede.

Fixtures sintéticos, sem dado pessoal.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportArgumentType=false

from __future__ import annotations

import io
import json
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

import httplib2
import pytest
from googleapiclient.errors import HttpError

from apps.core.models.solicitacao import Solicitacao
from apps.core.services.export_contract_importer import ExportContractImporter
from apps.core.services.gcal_oauth_client import OAuthCalendarClient
from apps.core.tests.test_export_contract_importer_virada import (  # noqa: F401 (fixtures)
    FUTURO,
    _existente,
    _export,
    _sol,
    hoje_fixo,
    m,
)

pytestmark = pytest.mark.django_db

AGENDA = "formacoes@group.calendar.google.invalid"
DIA = FUTURO.isoformat()
DIA_SEGUINTE = (FUTURO + timedelta(days=1)).isoformat()
_ALVO_CLIENTE = "apps.core.management.commands.conferir_gcal_adocao.get_oauth_client_for_user"


def _linha(ext: str, eid: str, **kw: str) -> dict[str, str]:
    base = {
        "evento_id": ext,
        "external_event_id": eid,
        "external_event_id_confianca": "alta",
        "na_agenda_google": "true",
    }
    base.update(kw)
    return _sol(**base)


def _evento(inicio: str, status: str = "confirmed") -> dict[str, Any]:
    return {"id": "x", "status": status, "summary": "Titulo Secreto", "start": {"dateTime": inicio}}


def _http(status: int) -> HttpError:
    return HttpError(resp=httplib2.Response({"status": status}), content=b"")


def _google(eventos: dict[str, Any], acessivel: bool = True) -> MagicMock:
    """Cliente falso com a interface do OAuthCalendarClient: `get` responde de `eventos` (exceção = erro)."""
    client = MagicMock(spec=OAuthCalendarClient)
    client.calendar_accessible.return_value = acessivel

    def _get(calendar_id: str, event_id: str) -> Any:
        assert calendar_id == AGENDA
        v = eventos.get(event_id)
        if isinstance(v, BaseException):
            raise v
        return v

    client.get.side_effect = _get
    return client


def _conferir(m, path: str, saida: str, client: MagicMock) -> str:
    out = io.StringIO()
    with override_settings(GCAL_OAUTH_CALENDAR_ID=AGENDA), patch(_ALVO_CLIENTE, return_value=(client, AGENDA)):
        call_command(
            "conferir_gcal_adocao", "--path", path, "--saida", saida, "--operador", str(m.coord.id), stdout=out
        )
    return out.getvalue()


def _cenario(tmp_path, m) -> tuple[str, dict[str, Solicitacao]]:
    """Oito eventos prontos para a adoção (aprovados, marcados), um por caso da conferência."""
    casos = {
        "ok": ("EV1", "id1", (8, 12)),
        "cancelado": ("EV2", "id2", (8, 12)),
        "ausente": ("EV3", "id3", (8, 12)),
        "outra_data": ("EV4", "id4", (8, 12)),
        "fuso_ok": ("EV5", "id5", (22, 23)),
        "fuso_outra_data": ("EV6", "id6", (22, 23)),
        "erro_5xx": ("EV7", "id7", (8, 12)),
        "timeout": ("EV8", "id8", (8, 12)),
    }
    sols: dict[str, Solicitacao] = {}
    linhas: list[dict[str, str]] = []
    for nome, (ext, eid, horas) in casos.items():
        sols[nome] = _existente(m, ext, horas=horas, publicado_fora_do_sistema=True)
        linhas.append(_linha(ext, eid, hora_inicio=f"{horas[0]:02d}:00", hora_fim=f"{horas[1]:02d}:00"))
    return _export(tmp_path, linhas), sols


_GOOGLE = {
    "id1": _evento(f"{DIA}T09:00:00-03:00"),  # outro horário, mesma data: aprova (o Reapply atualiza)
    "id2": _evento(f"{DIA}T08:00:00-03:00", status="cancelled"),
    "id3": None,  # 404: o cliente devolve None
    "id4": _evento(f"{DIA_SEGUINTE}T08:00:00-03:00"),
    # 22h em Fortaleza é 01h do dia seguinte em UTC: mesma data em Fortaleza, aprova.
    "id5": _evento(f"{DIA_SEGUINTE}T01:00:00Z"),
    # Mesma data UTC do evento do sistema (dia seguinte), mas outro dia em Fortaleza: não aprova.
    "id6": _evento(f"{DIA_SEGUINTE}T00:30:00-03:00"),
    "id7": _http(503),
    "id8": TimeoutError("timed out"),
}


def test_conferencia_aprova_so_confirmado_na_mesma_data(tmp_path, m):
    path, sols = _cenario(tmp_path, m)
    saida = tmp_path / "conferido.json"
    client = _google(_GOOGLE)
    antes = timezone.now()
    out = _conferir(m, path, str(saida), client)

    arquivo = json.loads(saida.read_text(encoding="utf-8"))
    ok, fuso_ok = sols["ok"], sols["fuso_ok"]
    assert set(arquivo) == {str(ok.id), str(fuso_ok.id)}
    assert arquivo[str(ok.id)]["event_id"] == "id1"
    assert arquivo[str(ok.id)]["inicio_google"] == f"{DIA}T09:00:00-03:00"
    assert arquivo[str(fuso_ok.id)]["event_id"] == "id5"
    em = datetime.fromisoformat(arquivo[str(ok.id)]["verificado_em"])
    assert antes <= em <= timezone.now()

    esperado: dict[str, list[Solicitacao]] = {
        "aprovado": [ok, fuso_ok],
        "cancelado_no_google": [sols["cancelado"]],
        "ausente_no_google": [sols["ausente"]],
        "outra_data": [sols["outra_data"], sols["fuso_outra_data"]],
        "erro_de_leitura": [sols["erro_5xx"], sols["timeout"]],
    }
    for motivo, lista in esperado.items():
        ids = " ".join(f"s{i}" for i in sorted(s.id for s in lista))
        assert f"{motivo}: {len(lista)} [{ids}]" in out


def test_conferencia_so_le_o_google(tmp_path, m):
    path, _ = _cenario(tmp_path, m)
    client = _google(_GOOGLE)
    _conferir(m, path, str(tmp_path / "c.json"), client)
    chamados = {c[0] for c in client.method_calls}
    assert chamados == {"calendar_accessible", "get"}, chamados
    assert client.get.call_count == 8


def test_conferencia_nao_imprime_dado_pessoal(tmp_path, m):
    path, _ = _cenario(tmp_path, m)
    out = _conferir(m, path, str(tmp_path / "c.json"), _google(_GOOGLE))
    for proibido in ("Titulo Secreto", "@", m.coord.cpf, m.coord.username, "Cidade X", "Projeto X"):
        assert proibido not in out


def test_conferencia_le_os_mesmos_candidatos_da_adocao(tmp_path, m):
    """Evento que a adoção recusa (média confiança, pendente) nem é lido no Google."""
    pronto = _existente(m, "EV1", publicado_fora_do_sistema=True)
    _existente(m, "EV2", publicado_fora_do_sistema=True, status="pendente")
    _existente(m, "EV3", publicado_fora_do_sistema=True)
    path = _export(
        tmp_path,
        [_linha("EV1", "id1"), _linha("EV2", "id2"), _linha("EV3", "id3", external_event_id_confianca="media")],
    )
    client = _google({"id1": _evento(f"{DIA}T08:00:00-03:00")})
    _conferir(m, path, str(tmp_path / "c.json"), client)
    assert [c.args[1] for c in client.get.call_args_list] == ["id1"]
    candidatos = ExportContractImporter(path=path, mode="virada").candidatos_gcal_adocao()
    assert [(sid, eid) for sid, eid, _ in candidatos] == [(pronto.id, "id1")]


def test_conferencia_e_adocao_de_ponta_a_ponta(tmp_path, m):
    path, sols = _cenario(tmp_path, m)
    saida = tmp_path / "conferido.json"
    _conferir(m, path, str(saida), _google(_GOOGLE))
    call_command(
        "import_export_contract",
        *("--path", path, "--mode", "virada", "--apply", "--allow-entity", "gcal_adocao"),
        *("--gcal-verificado", str(saida)),
        stdout=io.StringIO(),
    )
    adotados = {nome for nome, s in sols.items() if Solicitacao.objects.get(id=s.id).external_event_id}
    assert adotados == {"ok", "fuso_ok"}
    travados = Solicitacao.objects.filter(publicado_fora_do_sistema=True).count()
    assert travados == 6


def test_conferencia_sem_acesso_a_agenda_e_command_error(tmp_path, m):
    path, _ = _cenario(tmp_path, m)
    saida = tmp_path / "c.json"
    with pytest.raises(CommandError, match="não enxerga"):
        _conferir(m, path, str(saida), _google(_GOOGLE, acessivel=False))
    assert not saida.exists()


@pytest.mark.parametrize("agenda", ["", "primary"])
def test_conferencia_sem_agenda_da_organizacao_e_command_error(tmp_path, m, agenda):
    path, _ = _cenario(tmp_path, m)
    with override_settings(GCAL_OAUTH_CALENDAR_ID=agenda), pytest.raises(CommandError, match="GCAL_OAUTH"):
        call_command(
            "conferir_gcal_adocao",
            *("--path", path, "--saida", str(tmp_path / "c.json"), "--operador", str(m.coord.id)),
        )


def _um_evento(tmp_path, m, evento: Any) -> tuple[str, dict[str, Any], Solicitacao]:
    """Um evento pronto (08h-12h do dia FUTURO) conferido contra `evento` (o que o Google devolve)."""
    s = _existente(m, "EV1", publicado_fora_do_sistema=True)
    path = _export(tmp_path, [_linha("EV1", "id1")])
    saida = tmp_path / "um.json"
    out = _conferir(m, path, str(saida), _google({"id1": evento}))
    return out, json.loads(saida.read_text(encoding="utf-8")), s


@pytest.mark.parametrize(
    ("evento", "motivo"),
    [
        (_evento(f"{DIA}T08:00:00-03:00", status="tentative"), "nao_confirmado"),
        ({"id": "x", "start": {"dateTime": f"{DIA}T08:00:00-03:00"}}, "nao_confirmado"),
        ({"id": "x", "status": "confirmed", "start": {"date": DIA}}, "aprovado"),
        ({"id": "x", "status": "confirmed", "start": {"date": DIA_SEGUINTE}}, "outra_data"),
        ({"id": "x", "status": "confirmed"}, "erro_de_leitura"),
        ({"id": "x", "status": "confirmed", "start": {}}, "erro_de_leitura"),
        # Sem fuso não dá para saber o dia: não usa o fuso do servidor.
        (_evento(f"{DIA}T08:00:00"), "erro_de_leitura"),
    ],
)
def test_conferencia_status_e_formas_do_inicio(tmp_path, m, evento, motivo):
    out, arquivo, s = _um_evento(tmp_path, m, evento)
    assert f"{motivo}: 1 [s{s.id}]" in out
    assert (str(s.id) in arquivo) is (motivo == "aprovado")


def test_conferencia_que_falha_nao_deixa_o_arquivo_velho(tmp_path, m):
    path, _ = _cenario(tmp_path, m)
    saida = tmp_path / "c.json"
    _conferir(m, path, str(saida), _google(_GOOGLE))
    assert json.loads(saida.read_text(encoding="utf-8"))
    with pytest.raises(CommandError):
        _conferir(m, path, str(saida), _google(_GOOGLE, acessivel=False))
    assert not saida.exists()
    _conferir(m, path, str(saida), _google(_GOOGLE))
    with override_settings(GCAL_OAUTH_CALENDAR_ID=""), pytest.raises(CommandError):
        call_command("conferir_gcal_adocao", *("--path", path, "--saida", str(saida), "--operador", str(m.coord.id)))
    assert not saida.exists()
    assert [p.name for p in tmp_path.iterdir() if p.suffix != ".json" and p.is_file()] == []
