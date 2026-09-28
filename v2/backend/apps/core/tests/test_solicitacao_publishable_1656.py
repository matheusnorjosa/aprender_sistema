"""`?publishable=true`: a lista de Solicitações devolve só o que a pessoa pode publicar no Google (#1656).

Contrato FE-first pela fonte de dados (o precedente do S2): a página da Apoio lista com
`?status=aprovado&publishable=true`, e toda linha que vem é aceita pelas 4 ações GCal. O filtro usa a
MESMA regra da guarda de objeto (`can_publish_solicitacao`), extraída em `_publish_tier` — a paridade
entre a lista e o objeto fica travada aqui. Sem o parâmetro, nada muda.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao
from apps.core.services.solicitacao_scope import can_publish_solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _aprovada(owner, projeto) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=3)
    return SolicitacaoFactory(
        usuario=owner,
        municipio=MunicipioFactory(),
        projeto=projeto,
        tipo_evento=TipoEventoFactory(nome="Formacao PUB"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="aprovado",
    )


def _usuario(*grupos, gerencia=None):
    user = UsuarioFactory()
    for nome in grupos:
        user.groups.add(GroupFactory(name=nome))
    if gerencia is not None:
        EquipeGerencia.objects.create(usuario=user, gerencia=gerencia, papel="APOIO")
    return user


@pytest.fixture
def mundo():
    """Forma de prod: `Projeto.setor` preenchido, `gerencia` NULL."""
    fluir = Gerencia.objects.create(nome="GERENCIA 3 PUB", nome_setor="Fluir", setor_canonico="Fluir", ativo=True)
    atores = {
        "apoio_fluir": _usuario("Apoio de Coordenação", gerencia=fluir),
        "coordenador": _usuario("Coordenador"),
        "controle": _usuario("Controle"),
        "dat_apoio": _usuario("DAT", "Apoio de Coordenação", gerencia=fluir),
    }
    terceiro = _usuario("Coordenador")
    projeto_fluir = ProjetoFactory(nome="Fluir PUB", setor="Fluir", gerencia=None)
    projeto_vidas = ProjetoFactory(nome="Vidas PUB", setor="Vidas", gerencia=None)
    projeto_sem_setor = ProjetoFactory(nome="Sem setor PUB", setor="", gerencia=None)
    eventos = {
        "fluir_terceiro": _aprovada(terceiro, projeto_fluir),
        "fluir_propria": _aprovada(atores["apoio_fluir"], projeto_fluir),
        "vidas_terceiro": _aprovada(terceiro, projeto_vidas),
        "vidas_propria": _aprovada(atores["apoio_fluir"], projeto_vidas),  # própria, mas de outro setor
        "sem_setor_propria": _aprovada(atores["apoio_fluir"], projeto_sem_setor),
        "coord_propria": _aprovada(atores["coordenador"], projeto_fluir),
    }
    return atores, eventos


def _ids(user, **extra):
    client = APIClient()
    client.force_authenticate(user)
    resp = client.get("/api/solicitacoes/", {"status": "aprovado", "page_size": 100, **extra})
    assert resp.status_code == 200
    return {row["id"] for row in resp.data["results"]}


def test_publishable_true_apoio_so_eventos_do_setor(mundo):
    atores, eventos = mundo

    ids = _ids(atores["apoio_fluir"], publishable="true")

    assert ids == {eventos["fluir_terceiro"].id, eventos["fluir_propria"].id, eventos["coord_propria"].id}
    # sem o filtro, a própria de outro setor e a sem setor aparecem (são dela) — mas não são publicáveis
    assert eventos["vidas_propria"].id in _ids(atores["apoio_fluir"])


def test_publishable_true_sem_policy_retorna_vazio(mundo):
    atores, eventos = mundo
    assert eventos["coord_propria"].id in _ids(atores["coordenador"])  # vê a própria sem o filtro

    assert _ids(atores["coordenador"], publishable="true") == set()


def test_publishable_true_global_retorna_todo_o_escopo(mundo):
    atores, eventos = mundo

    assert _ids(atores["controle"], publishable="true") == _ids(atores["controle"])
    assert {e.id for e in eventos.values()} <= _ids(atores["controle"], publishable="true")


@pytest.mark.parametrize("ator", ["apoio_fluir", "coordenador", "controle", "dat_apoio"])
def test_paridade_publishable_x_can_publish(ator, mundo):
    """Para todo evento visível, estar em `?publishable=true` ⇔ `can_publish_solicitacao` (guarda das 4 ações)."""
    atores, eventos = mundo
    user = atores[ator]
    visiveis = _ids(user)
    publicaveis = _ids(user, publishable="true")

    for nome, evento in eventos.items():
        if evento.id not in visiveis:
            continue
        assert (evento.id in publicaveis) is can_publish_solicitacao(user, evento), f"{ator} × {nome}"
