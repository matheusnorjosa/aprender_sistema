"""
Smoke test das factories (#1404).

Garante que cada factory instancia um objeto válido e persistido, e que os
traits/params principais funcionam. Roda sob `pytest --no-migrations`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import pytest

from apps.core.models import Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def test_usuario_factory_unique_cpf():
    u1 = UsuarioFactory()
    u2 = UsuarioFactory()
    assert u1.pk and u2.pk
    assert u1.cpf != u2.cpf
    assert len(u1.cpf) == 11 and u1.cpf.isdigit()


def test_usuario_factory_superuser_trait_and_groups():
    admin = UsuarioFactory(superuser=True)
    assert admin.is_superuser and admin.is_staff

    user = UsuarioFactory(groups=["Coordenador", "DAT"])
    assert set(user.groups.values_list("name", flat=True)) == {"Coordenador", "DAT"}


def test_municipio_factory_unique():
    m1 = MunicipioFactory()
    m2 = MunicipioFactory()
    assert m1.nome != m2.nome
    assert m1.uf == "CE"


def test_projeto_factory_fluxo_default_and_super_trait():
    assert ProjetoFactory().fluxo == "NAO_SUPER"
    assert ProjetoFactory(super=True).fluxo == "SUPER"


def test_tipo_evento_factory_get_or_create():
    t1 = TipoEventoFactory()
    t2 = TipoEventoFactory()
    # django_get_or_create no nome → mesma instância reutilizada
    assert t1.pk == t2.pk
    assert TipoEventoFactory(nome="Reunião").pk != t1.pk


def test_group_factory_get_or_create():
    assert GroupFactory(name="Controle").pk == GroupFactory(name="Controle").pk


def test_solicitacao_factory_is_pendente_with_fks():
    s = SolicitacaoFactory()
    assert s.pk
    assert s.status == Solicitacao.Status.PENDENTE
    assert s.usuario_id and s.tipo_evento_id and s.municipio_id and s.projeto_id
    assert s.fim > s.inicio
