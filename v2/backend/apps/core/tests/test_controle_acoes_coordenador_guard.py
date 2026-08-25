"""Opção A #1837 · Wave 2 — o 2º resolvedor de coordenador precisa do MESMO guard.

`controle_acoes_import._resolve_dat_coordenador` (import operacional de ações via DRF) casava
email→nome com `.order_by("id").first()` — sem guard de ambiguidade. Email de coordenador é chave
de CARGO (migra de dono): `.first()` atrelaria a ação ao ocupante ATUAL da caixa. Guard: 0 ou 2+ → None.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import pytest

from apps.core.models import DATCoordenador
from apps.core.services.controle_acoes_import import _resolve_dat_coordenador
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_resolve_unico_por_nome():
    actor = UsuarioFactory()
    c = DATCoordenador.objects.create(nome="Maria Souza", area="DAT", created_by=actor)
    assert _resolve_dat_coordenador("Maria Souza").id == c.id


def test_resolve_email_de_cargo_ambiguo_retorna_none():
    actor = UsuarioFactory()
    DATCoordenador.objects.create(nome="Coord Antiga", email="coordenacao11@x.com", area="DAT", created_by=actor)
    DATCoordenador.objects.create(nome="Coord Nova", email="coordenacao11@x.com", area="DAT", created_by=actor)
    assert _resolve_dat_coordenador("coordenacao11@x.com") is None  # cargo migrou → não chuta o dono atual


def test_resolve_nome_ambiguo_retorna_none():
    actor = UsuarioFactory()
    DATCoordenador.objects.create(nome="Homonimo", email="a@x.com", area="DAT", created_by=actor)
    DATCoordenador.objects.create(nome="Homonimo", email="b@x.com", area="DAT", created_by=actor)
    assert _resolve_dat_coordenador("Homonimo") is None


def test_resolve_nao_encontrado_retorna_none():
    assert _resolve_dat_coordenador("Ninguem Aqui") is None
    assert _resolve_dat_coordenador("") is None
