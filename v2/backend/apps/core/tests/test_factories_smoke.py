"""
Smoke test das factories (#1404).

Garante que cada factory instancia um objeto válido e persistido, e que os
traits/params principais funcionam. Roda sob `pytest --no-migrations`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Solicitacao
from apps.core.tests.factories import (
    GerenciaFactory,
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
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


def test_usuario_factory_password_is_hashed_and_authenticates():
    # default
    assert UsuarioFactory().check_password("testpass123")
    # override (drop-in para create_user(password=...) em testes de login)
    u = UsuarioFactory(password="s3cr3t")
    assert u.check_password("s3cr3t")
    assert u.password != "s3cr3t"  # hasheada, não raw


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


def test_grupo_de_funcao_vem_com_vinculo_vigente_em_gerencia_neutra():
    """PR 8.0: `UsuarioFactory(groups=[...])` cria o vínculo do papel junto do grupo de função."""
    user = UsuarioFactory(groups=["Coordenador", "DAT"])

    vinculo = EquipeGerencia.vigentes_em().get(usuario=user)
    assert vinculo.papel == "COORDENADOR"
    assert vinculo.gerencia.ativo and vinculo.gerencia.perfil == Gerencia.Perfil.PADRAO
    assert vinculo.gerencia.setor_canonico == ""


def test_grupo_sem_vinculo_e_gerencia_escolhida():
    gerencia = GerenciaFactory()
    so_grupo = UsuarioFactory(groups=["Gerente"], groups__vinculo=False)
    na_gerencia = UsuarioFactory(groups=["Apoio de Coordenação"], groups__gerencia=gerencia)

    assert not EquipeGerencia.objects.filter(usuario=so_grupo).exists()
    assert EquipeGerencia.vigentes_em().filter(usuario=na_gerencia, gerencia=gerencia, papel="APOIO").exists()


def test_com_papel_da_grupo_e_vinculo_e_equipe_so_vinculo():
    user = UsuarioFactory()
    com_papel(user, "FORMADOR")
    com_papel(user, "EQUIPE")

    assert set(user.groups.values_list("name", flat=True)) == {"Formador"}
    assert set(EquipeGerencia.vigentes_em().filter(usuario=user).values_list("papel", flat=True)) == {
        "FORMADOR",
        "EQUIPE",
    }
