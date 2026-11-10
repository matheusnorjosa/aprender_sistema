"""#2189 — a chave de identidade não se grava pela API.

`external_hash` (e `external_event_id`) é a chave que o importador e o Google usam para achar a linha de novo.
Quem chama a API não pode escrevê-la: um valor posto à mão colide com a carga da planilha ou adota a linha
errada. Os serializers de escrita de Solicitacao, Deslocamento, AcaoDAT e DATRegistro deixam o campo de fora
ou só leitura; o importador e o Google continuam gravando pelo ORM.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

import pytest

from apps.core.models import DATRegistro, ProjetoGeral
from apps.core.serializers.dat_registro import (
    DATRegistroCreateSerializer,
    DATRegistroUpdateSerializer,
)
from apps.core.serializers.solicitacao import SolicitacaoSerializer
from apps.core.serializers.workflow import AcaoDATCreateSerializer, DeslocamentoSerializer
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    UsuarioFactory,
    com_pacote_do_dat,
)

WRITE_SERIALIZERS = [
    DATRegistroCreateSerializer,
    DATRegistroUpdateSerializer,
    AcaoDATCreateSerializer,
    DeslocamentoSerializer,
    SolicitacaoSerializer,
]
CHAVES = ["external_hash", "external_event_id"]


@pytest.mark.parametrize("serializer_cls", WRITE_SERIALIZERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("campo", CHAVES)
def test_chave_de_identidade_nao_e_gravavel(serializer_cls, campo) -> None:
    fields = serializer_cls().fields
    assert campo not in fields or fields[campo].read_only, f"{serializer_cls.__name__}.{campo} gravável pela API"


class TestPostDatRegistroIgnoraExternalHash(APITestCase):
    @classmethod
    def setUpTestData(cls):
        suf = str(uuid.uuid4())[:8]
        cls.municipio = MunicipioFactory(nome=f"Cidade 2189 {suf}", uf="BA")
        cls.projeto_geral = ProjetoGeral.objects.create(nome=f"PG 2189 {suf}", tipo_calculo_codigos="por_aluno")
        cls.projeto = ProjetoFactory(
            nome=f"Projeto 2189 {suf}", codigo=f"P2189{suf}", fluxo="NAO_SUPER", projeto_geral=cls.projeto_geral
        )
        cls.dat_user = UsuarioFactory(username=f"dat2189_{suf}", cpf=f"444{suf}")
        com_pacote_do_dat(cls.dat_user)

    def test_post_com_external_hash_nao_grava_a_chave(self):
        self.client.force_authenticate(user=self.dat_user)
        data = {
            "municipio": self.municipio.id,
            "projeto_geral": self.projeto_geral.id,
            "projeto": self.projeto.id,
            "aluno_qtde": 100,
            "professor_qtde": 10,
            "external_hash": "EV-API-2189",
        }
        resp = self.client.post(reverse("core:dat-registro-list"), data)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertIsNone(DATRegistro.objects.get(pk=resp.json()["id"]).external_hash)
        self.assertIsNone(resp.json().get("external_hash"))
