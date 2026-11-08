"""
A importação de EVENTOS pela tela saiu de uso (#1628; decisão do dono de 07/11/2026).

Depois da virada, o evento nasce só pela Nova Solicitação e pela carga única. A tela buscava o evento
pelo SHA1 da vaga (`services/eventos_import.py`), e a carga da virada grava `external_hash` = evento_id.
Reimportar pela tela um evento da virada, ou um que nasceu na Nova Solicitação (hash nulo), criava uma
segunda Solicitacao. Sem a rota, a tela não duplica mais nada.

O serviço `eventos_import.py` fica: a carga da virada usa `_compute_external_hash` dele.

Este arquivo prova:
- o POST na rota antiga não grava, inclusive para o superusuário, e o evento existente fica sozinho;
- o GET na rota antiga responde 404.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Solicitacao
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

ROTA_ANTIGA = "/api/solicitacoes/import/"
_TZ_FORTALEZA = ZoneInfo("America/Fortaleza")


def _superusuario() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    return client


@pytest.mark.parametrize("external_hash", ["EV000123", None], ids=["veio_da_virada", "nasceu_na_tela"])
def test_import_pela_tela_nao_duplica_evento_existente(external_hash: str | None):
    municipio = MunicipioFactory(nome="Acarape", uf="CE")
    projeto = ProjetoFactory(nome="Projeto Vaga", fluxo="SUPER")
    tipo_evento = TipoEventoFactory(nome="Formacao")
    coordenador = UsuarioFactory(email="coord_vaga@example.invalid")
    dia = date.today() + timedelta(days=30)
    SolicitacaoFactory(
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.make_aware(datetime.combine(dia, time(8)), _TZ_FORTALEZA),
        fim=timezone.make_aware(datetime.combine(dia, time(12)), _TZ_FORTALEZA),
        segmento="Fundamental I",
        external_hash=external_hash,
    )
    csv = (
        "municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,segmento\n"
        f"{municipio.nome},{projeto.nome},{tipo_evento.nome},{dia.isoformat()},08:00,12:00,"
        f"{coordenador.email},Fundamental I\n"
    )
    arquivo = SimpleUploadedFile("eventos.csv", csv.encode(), content_type="text/csv")

    resposta = _superusuario().post(f"{ROTA_ANTIGA}?dry_run=false", {"file": arquivo}, format="multipart")

    # A URL cai no detalhe do router de solicitações ("import" vira pk): o POST ali não existe (405).
    assert resposta.status_code in {404, 405}, f"POST {ROTA_ANTIGA} respondeu {resposta.status_code}"
    assert Solicitacao.objects.count() == 1


def test_get_na_rota_antiga_responde_404():
    resposta = _superusuario().get(ROTA_ANTIGA)

    assert resposta.status_code == 404, f"GET {ROTA_ANTIGA} respondeu {resposta.status_code}"
