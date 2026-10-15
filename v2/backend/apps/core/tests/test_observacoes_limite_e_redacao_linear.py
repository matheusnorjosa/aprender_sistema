"""
S6 (auditoria de segurança 14/10, achado C5): `observacoes` com teto e redação de e-mail linear.

A regex de e-mail `[\\w.+-]+@[\\w-]+\\.[\\w.-]+`, sem âncora, recomeça em cada posição de uma sequência
longa de letras e a percorre até o fim: tempo quadrático (medido: 20 mil caracteres = 0,6 s; 50 mil
= 4,2 s). `observacoes` não tinha teto e era redigida ANTES do corte em 5000 da descrição do GCal,
então um texto grande travava a prévia, o painel de drift e o worker de publicação.

Regras:
- `observacoes`: no máximo 5000 caracteres (model + serializer).
- `payload.py` corta `observacoes` em 5000 ANTES de redigir.
- A regex de `minimize.py` e `logging_filters.py` só começa no início de uma sequência (lookbehind)
  e redige exatamente o que a antiga redigia (equivalência medida contra a regex antiga).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import logging
import random
import re
import time

from rest_framework import serializers

import pytest

from apps.core.logging_filters import PIIRedactionFilter
from apps.core.models import Solicitacao
from apps.core.serializers.solicitacao import SolicitacaoSerializer
from apps.core.services.gcal import payload as payload_mod
from apps.core.services.gcal.minimize import _PLACEHOLDER, minimize_free_text

# A regex de antes (referência para a equivalência). Quadrática: só roda em texto curto aqui.
_EMAIL_ANTIGO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CPF_MINIMIZE = re.compile(r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})\b")
_CPF_LOG = re.compile(r"\b\d{11}\b")

_ADVERSARIOS = [
    "a" * 200_000,
    "a+" * 100_000,
    "a@" * 100_000,
    "a@b." * 50_000,
    "x@" + "a." * 100_000,
    "a@b.c+" * 33_333,
    "a@b.c+" + "a" * 200_000,
    ".@a-" * 50_000,
    "1" * 200_000,
]


def _minimize_antigo(texto: str) -> str:
    return _CPF_MINIMIZE.sub(_PLACEHOLDER, _EMAIL_ANTIGO.sub(_PLACEHOLDER, texto))


def _log_antigo(texto: str) -> str:
    mascarado = _EMAIL_ANTIGO.sub(lambda m: "***@" + m.group(0).split("@", 1)[1], texto)
    return _CPF_LOG.sub("<cpf>", mascarado)


def _log_novo(texto: str) -> str:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, texto, None, None)
    PIIRedactionFilter().filter(record)
    return record.getMessage()


_CASOS_REAIS = [
    "contato joao@gmail.com para ajustes",
    "joao.silva+tag@escola.ce.gov.br, maria-souza@prefeitura.com.br.",
    "(ana_paula@x.com) e <bia@y.org>; fim",
    "dois juntos a@b.c+d@e.f e um+mais@dominio.com",
    "sem dominio joao@localhost nem ponto",
    "e-mail no fim: z@z.zz",
    "acentuação josé@escola.com.br ok",
    "CPF 11144477735 e 111.444.777-35 e email x.y@z.com",
    "",
]


class TestLimiteObservacoes:
    def test_model_tem_max_length_5000(self):
        assert Solicitacao._meta.get_field("observacoes").max_length == 5000

    def test_serializer_recusa_mais_de_5000(self):
        campo = SolicitacaoSerializer().fields["observacoes"]
        assert campo.run_validation("a" * 5000) == "a" * 5000
        with pytest.raises(serializers.ValidationError):
            campo.run_validation("a" * 5001)


@pytest.mark.django_db
def test_payload_corta_observacoes_antes_de_redigir(monkeypatch):
    from apps.core.tests.factories import SolicitacaoFactory

    recebido: list[int] = []
    original = payload_mod.minimize_free_text

    def _espiao(texto):
        recebido.append(len(texto or ""))
        return original(texto)

    monkeypatch.setattr(payload_mod, "minimize_free_text", _espiao)
    s = SolicitacaoFactory(observacoes="a" * 20_000)

    payload_mod.build_event_payload(s)

    assert recebido and max(recebido) <= 5000


class TestRedacaoLinear:
    @pytest.mark.parametrize("texto", _ADVERSARIOS, ids=lambda t: f"{t[:6]!r}x{len(t)}")
    def test_minimize_em_200_mil_caracteres_leva_menos_de_meio_segundo(self, texto):
        inicio = time.perf_counter()
        minimize_free_text(texto)
        assert time.perf_counter() - inicio < 0.5

    @pytest.mark.parametrize("texto", _ADVERSARIOS, ids=lambda t: f"{t[:6]!r}x{len(t)}")
    def test_filtro_de_log_em_200_mil_caracteres_leva_menos_de_meio_segundo(self, texto):
        inicio = time.perf_counter()
        _log_novo(texto)
        assert time.perf_counter() - inicio < 0.5


class TestEquivalenciaDaRedacao:
    @pytest.mark.parametrize("texto", _CASOS_REAIS)
    def test_casos_reais(self, texto):
        assert minimize_free_text(texto) == _minimize_antigo(texto)
        assert _log_novo(texto) == _log_antigo(texto)

    def test_textos_aleatorios_redigem_igual_a_regex_antiga(self):
        rnd = random.Random(20261015)
        alfabeto = "ab.+-@ _é1#"
        for _ in range(20_000):
            texto = "".join(rnd.choice(alfabeto) for _ in range(rnd.randint(0, 24)))
            assert minimize_free_text(texto) == _minimize_antigo(texto), texto
            assert _log_novo(texto) == _log_antigo(texto), texto
