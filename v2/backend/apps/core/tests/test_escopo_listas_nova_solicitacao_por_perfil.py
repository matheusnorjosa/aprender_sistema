"""
Prova pedida pelo dono (05/10/2026): as listas de formadores e de coordenadores responsáveis
que a Nova Solicitação oferece (`/api/lookup/usuarios/`) e as que o salvar aceita
(`formador_ids` e `coordenador`) ficam no SETOR de quem cria — exceto o superusuário e quem a
regra atual já deixa ver tudo (`user_is_solicitacao_global`: DAT, Controle, Superintendência).

Um cenário com dois setores (Vidas e Fluir) e cada perfil que usa a tela.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

import itertools
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, EquipeGerencia, Gerencia
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_TZ = ZoneInfo("America/Fortaleza")
_N = itertools.count(1)
_HORA = itertools.count(7)


def _pessoa(grupos, gerencia=None, papel="FORMADOR", **kw):
    n = next(_N)
    u = UsuarioFactory(
        username=f"escopo_{n}", email=f"escopo_{n}@example.invalid", first_name=f"P{n}", groups=grupos, **kw
    )
    if gerencia is not None:
        EquipeGerencia.objects.create(usuario=u, gerencia=gerencia, papel=papel, ativo=True)
    return u


@pytest.fixture
def mundo():
    vidas = Gerencia.objects.create(nome="G-ESC-VIDAS", nome_setor="Vidas", setor_canonico="Vidas")
    fluir = Gerencia.objects.create(nome="G-ESC-FLUIR", nome_setor="Fluir", setor_canonico="Fluir")
    municipio = MunicipioFactory(nome="Municipio Ficticio Escopo", uf="CE")
    projeto = ProjetoFactory(
        nome="Projeto Ficticio Vidas", codigo="PFESC", fluxo="NAO_SUPER", gerencia=vidas, setor="Vidas"
    )
    Compra.objects.create(
        codigo="C-ESC",
        projeto=projeto,
        municipio=municipio,
        quantidade=1,
        data=date(2026, 3, 1),
        uso="teste",
        external_hash=f"{1:064d}",
    )
    return {
        "municipio": municipio,
        "projeto": projeto,
        "tipo": TipoEventoFactory(nome="Formacao Ficticia Escopo"),
        "formador_vidas": _pessoa(["Formador"], vidas),
        "formador_fluir": _pessoa(["Formador"], fluir),
        "coord_vidas": _pessoa(["Coordenador"], vidas, "COORDENADOR"),
        "coord_fluir": _pessoa(["Coordenador"], fluir, "COORDENADOR"),
        "perfis": {
            "coordenador": _pessoa(["Coordenador"], vidas, "COORDENADOR"),
            "gerente": _pessoa(["Gerente"], vidas, "GERENTE"),
            "apoio": _pessoa(["Apoio de Coordenação"], vidas, "APOIO"),
            "dat": _pessoa(["DAT"]),
            "controle": _pessoa(["Controle", "Assistente Administrativo"]),
            "superusuario": _pessoa([], is_staff=True, is_superuser=True),
        },
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def _ids_oferecidos(user, role) -> set[int] | None:
    resp = _client(user).get("/api/lookup/usuarios/", {"role": role})
    if resp.status_code == 403:
        return None
    assert resp.status_code == 200, resp.data
    return {u["id"] for u in resp.data}


def _criar(m, user, *, formador, coordenador) -> int:
    hora = next(_HORA) % 12 + 7
    inicio = datetime(2031, 5, 5 + hora, 9, tzinfo=_TZ)
    payload: dict[str, Any] = {
        "municipio": m["municipio"].id,
        "projeto": m["projeto"].id,
        "tipo_evento": m["tipo"].id,
        "inicio": inicio.isoformat(),
        "fim": inicio.replace(hour=10).isoformat(),
        "coordenador": coordenador.id,
        "coordenador_acompanha": False,
        "pretende_avaliar_formador": False,
        "extra_participants": {"formador_ids": [formador.id]},
    }
    return _client(user).post("/api/solicitacoes/", payload, format="json").status_code


# (perfil, vê/aceita só o próprio setor?, pode criar?)
_PERFIS = [
    ("coordenador", True, True),
    ("gerente", True, True),
    ("apoio", True, True),
    ("dat", False, False),
    ("controle", None, False),  # sem acesso às listas
    ("superusuario", False, True),
]


@pytest.mark.parametrize(("perfil", "so_o_setor", "_cria"), _PERFIS)
def test_listas_oferecidas(mundo, perfil, so_o_setor, _cria):
    user = mundo["perfis"][perfil]
    formadores = _ids_oferecidos(user, "Formador,Coordenador")
    responsaveis = _ids_oferecidos(user, "Coordenador")
    if so_o_setor is None:
        assert formadores is None and responsaveis is None, "perfil sem acesso às listas da Nova Solicitação"
        return
    assert formadores is not None and responsaveis is not None
    assert {mundo["formador_vidas"].id, mundo["coord_vidas"].id} <= formadores
    assert mundo["coord_vidas"].id in responsaveis
    de_fora = {mundo["formador_fluir"].id, mundo["coord_fluir"].id}
    if so_o_setor:
        assert not (de_fora & formadores), f"{perfil}: lista de formadores vazou outro setor"
        assert mundo["coord_fluir"].id not in responsaveis, f"{perfil}: lista de responsáveis vazou outro setor"
    else:
        assert de_fora <= formadores
        assert mundo["coord_fluir"].id in responsaveis


@pytest.mark.parametrize(("perfil", "so_o_setor", "cria"), _PERFIS)
def test_salvar_aceita_so_o_setor(mundo, perfil, so_o_setor, cria):
    user = mundo["perfis"][perfil]
    mesmo = _criar(mundo, user, formador=mundo["formador_vidas"], coordenador=mundo["coord_vidas"])
    formador_fora = _criar(mundo, user, formador=mundo["formador_fluir"], coordenador=mundo["coord_vidas"])
    responsavel_fora = _criar(mundo, user, formador=mundo["formador_vidas"], coordenador=mundo["coord_fluir"])
    if not cria:
        assert (mesmo, formador_fora, responsavel_fora) == (403, 403, 403)
        return
    assert mesmo == 201
    if so_o_setor:
        assert (formador_fora, responsavel_fora) == (400, 400)
    else:
        assert (formador_fora, responsavel_fora) == (201, 201)
