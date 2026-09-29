"""
PR A — `/api/me/` ganha `gerencias: [{id, rotulo, papeis}]` (PLANOS_LIBERACAO_2026-09-29 §2).

Origem: vínculo `EquipeGerencia` VIGENTE (`vigentes_em()`) em gerência ATIVA, numa
query só, agrupado por gerência e ordenado pelo rótulo. `setores`,
`is_superintendencia` e `can_approve_super` continuam como estão (grupos Django).

A FiltersBar da Grade escolhe a gerência por este campo; a caracterização no fim
garante que ele bate com o acesso real do backend (`HasSectorAccess`, por vínculo).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnusedFunction=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_SEQ = itertools.count(1)


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    cache.clear()
    yield
    cache.clear()


def _gerencia(**kwargs) -> Gerencia:
    n = next(_SEQ)
    kwargs.setdefault("nome", f"GERENCIA ME {n}")
    kwargs.setdefault("nome_setor", f"Setor ME {n}")
    return Gerencia.objects.create(**kwargs)


def _me(user: Usuario) -> dict:
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/me/")
    assert resp.status_code == 200, resp.data
    return resp.json()


def test_vinculo_sem_grupo_aparece_em_gerencias():
    g4 = _gerencia(nome="GERENCIA 4 ME", nome_setor="ACerta", nome_exibicao="Superativar")
    user = UsuarioFactory()
    EquipeGerencia.objects.create(usuario=user, gerencia=g4, papel="COORDENADOR")

    data = _me(user)

    assert data["gerencias"] == [{"id": g4.id, "rotulo": "Superativar", "papeis": ["COORDENADOR"]}]
    assert data["setores"] == []


def test_vinculos_expirado_futuro_ou_desligado_ficam_de_fora():
    hoje = timezone.localdate()
    vigente = _gerencia(nome_exibicao="Vigente")
    user = UsuarioFactory()
    EquipeGerencia.objects.create(usuario=user, gerencia=vigente, papel="COORDENADOR")
    EquipeGerencia.objects.create(
        usuario=user,
        gerencia=_gerencia(nome_exibicao="Expirado"),
        papel="COORDENADOR",
        valid_from=hoje - timedelta(days=30),
        valid_to=hoje - timedelta(days=1),
    )
    EquipeGerencia.objects.create(
        usuario=user,
        gerencia=_gerencia(nome_exibicao="Futuro"),
        papel="COORDENADOR",
        valid_from=hoje + timedelta(days=1),
    )
    EquipeGerencia.objects.create(
        usuario=user, gerencia=_gerencia(nome_exibicao="Desligado"), papel="COORDENADOR", ativo=False
    )

    assert [g["rotulo"] for g in _me(user)["gerencias"]] == ["Vigente"]


def test_gerencia_inativa_fica_de_fora():
    user = UsuarioFactory()
    EquipeGerencia.objects.create(usuario=user, gerencia=_gerencia(nome_exibicao="Ativa"), papel="GERENTE")
    EquipeGerencia.objects.create(
        usuario=user, gerencia=_gerencia(nome_exibicao="Inativa", ativo=False), papel="GERENTE"
    )

    assert [g["rotulo"] for g in _me(user)["gerencias"]] == ["Ativa"]


def test_dois_papeis_na_mesma_gerencia_viram_um_item():
    g = _gerencia(nome_exibicao="Fluir")
    user = UsuarioFactory()
    EquipeGerencia.objects.create(usuario=user, gerencia=g, papel="GERENTE")
    EquipeGerencia.objects.create(usuario=user, gerencia=g, papel="COORDENADOR")

    assert _me(user)["gerencias"] == [{"id": g.id, "rotulo": "Fluir", "papeis": ["COORDENADOR", "GERENTE"]}]


def test_duas_gerencias_saem_ordenadas_pelo_rotulo():
    user = UsuarioFactory()
    EquipeGerencia.objects.create(usuario=user, gerencia=_gerencia(nome_exibicao="Vidas"), papel="COORDENADOR")
    # Sem nome_exibicao: o rótulo cai para nome_setor (e ordena por ele).
    EquipeGerencia.objects.create(
        usuario=user, gerencia=_gerencia(nome="A PRIMEIRA PELO NOME", nome_setor="Fluir"), papel="COORDENADOR"
    )

    assert [g["rotulo"] for g in _me(user)["gerencias"]] == ["Fluir", "Vidas"]


def test_superuser_sem_vinculo_recebe_lista_vazia():
    assert _me(UsuarioFactory(superuser=True))["gerencias"] == []


def test_gerencias_sem_n_mais_1():
    """Uma query só para montar `gerencias`: 3 vínculos custam o mesmo que 1."""
    um = UsuarioFactory()
    EquipeGerencia.objects.create(usuario=um, gerencia=_gerencia(), papel="COORDENADOR")
    tres = UsuarioFactory()
    for _ in range(3):
        EquipeGerencia.objects.create(usuario=tres, gerencia=_gerencia(), papel="COORDENADOR")

    _me(um)  # aquece caches de RBAC/ContentType fora da medição
    _me(tres)
    cache.clear()
    with CaptureQueriesContext(connection) as q_um:
        data_um = _me(um)
    cache.clear()
    with CaptureQueriesContext(connection) as q_tres:
        data_tres = _me(tres)

    assert len(data_um["gerencias"]) == 1
    assert len(data_tres["gerencias"]) == 3
    assert len(q_tres.captured_queries) == len(q_um.captured_queries)


def test_caracterizacao_grupo_vidas_com_vinculo_em_fluir():
    """Rede de regressão: o acesso da Grade vem do vínculo, não do grupo de setor.

    Quem tem o grupo Vidas e vínculo só em Fluir recebe 403 na Vidas e 200 na Fluir —
    por isso a FiltersBar oferece só `me.gerencias` (Fluir) e não o grupo.
    """
    vidas = _gerencia(nome_setor="Vidas")
    fluir = _gerencia(nome_setor="Fluir")
    user = UsuarioFactory()
    user.groups.add(GroupFactory(name="Vidas"))
    EquipeGerencia.objects.create(usuario=user, gerencia=fluir, papel="COORDENADOR")
    client = APIClient()
    client.force_authenticate(user=user)
    params = {"year": 2026, "month": 9, "role": "FORMADOR"}

    assert client.get("/api/availability/monthly/", {**params, "gerencia_id": vidas.id}).status_code == 403
    assert client.get("/api/availability/monthly/", {**params, "gerencia_id": fluir.id}).status_code == 200
    assert [g["id"] for g in _me(user)["gerencias"]] == [fluir.id]
