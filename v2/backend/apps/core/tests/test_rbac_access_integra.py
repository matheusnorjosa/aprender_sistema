"""
Integra (protótipo para a validação de 07/12/2026): policy `access_integra`.

Decisão do dono (24/11/2026, Q9): abrem a Integra o superusuário, a Diretoria e a gerente da
Superintendência. O PR 2-b (24/11/2026) soma a gerência SPE, cujo pacote é só a Integra (o GERENTE nela leva
também os direitos do papel, que vêm em qualquer gerência). Ninguém mais.
A concessão segue os dois caminhos que já existem:

- a capacidade `access_integra` nos pacotes DIRETORIA e SPE (`rbac_pacotes.PACOTE`), pelo vínculo
  EQUIPE/GERENTE vigente numa gerência de perfil DIRETORIA ou SPE;
- o vínculo GERENTE vigente na gerência aprovadora (`user_is_gerente_superintendencia`), o mesmo
  vínculo que dá a aprovação (`solicitation_approval_basis`). A Superintendência tem perfil PADRAO
  (pacote vazio), então o vínculo entra pela policy composta, não pelo pacote.

Os controles negativos cobrem quem está perto da regra: EQUIPE e COORDENADOR na Superintendência,
GERENTE de outra gerência, os pacotes DAT e Controle, o grupo Diretoria sem vínculo, o vínculo
GERENTE encerrado e, na SPE, FORMADOR, COORDENADOR, APOIO e o vínculo encerrado. Quem está na SPE não
aprova nem ganha outra capacidade, e a lotação nela é só do superusuário.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportUnusedFunction=false

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.rbac import CanAccessIntegra
from apps.core.rbac.helpers import GERENCIA_APROVADORA_NOME
from apps.core.rbac.policies import (
    ACCESS_POLICIES,
    COMPOSITE_POLICY_KEYS,
    PUBLIC_POLICY_KEYS,
    resolve_public_policies,
    solicitation_approval_basis,
    user_has_policy,
)
from apps.core.services.equipe_gerencia_import import gerencia_reservada, vinculo_exige_superusuario
from apps.core.services.rbac_pacotes import DIREITOS_PAPEL, PACOTE
from apps.core.services.rbac_permissions import capacidades_sem_cache
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

CHAVE = "access_integra"


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


def _gerencia(nome: str, perfil: str = Gerencia.Perfil.PADRAO) -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(nome=nome, defaults={"nome_setor": nome.title()})
    gerencia.perfil = perfil
    gerencia.save()
    return gerencia


def _com_vinculo(nome: str, papel: str, perfil: str = Gerencia.Perfil.PADRAO, **extra: Any) -> Usuario:
    usuario = UsuarioFactory()
    extra.setdefault("ativo", True)
    gerencia = _gerencia(nome, perfil)
    if papel == "APOIO":
        supervisor = UsuarioFactory()
        EquipeGerencia.objects.create(usuario=supervisor, gerencia=gerencia, papel="COORDENADOR", ativo=True)
        extra["coordenador_supervisor"] = supervisor
    EquipeGerencia.objects.create(usuario=usuario, gerencia=gerencia, papel=papel, **extra)
    return usuario


# ----------------------------------------------------------------------------
# Quem tem
# ----------------------------------------------------------------------------


def test_superusuario_tem():
    assert user_has_policy(UsuarioFactory(superuser=True), CHAVE) is True


@pytest.mark.parametrize("papel", ["EQUIPE", "GERENTE"])
def test_diretoria_pelo_pacote(papel):
    pessoa = _com_vinculo("DIRETORIA", papel, Gerencia.Perfil.DIRETORIA)
    assert CHAVE in capacidades_sem_cache(pessoa.id)
    assert user_has_policy(pessoa, CHAVE) is True


@pytest.mark.parametrize("papel", ["EQUIPE", "GERENTE"])
def test_spe_pelo_pacote(papel):
    pessoa = _com_vinculo("SPE", papel, Gerencia.Perfil.SPE)
    assert CHAVE in capacidades_sem_cache(pessoa.id)
    assert user_has_policy(pessoa, CHAVE) is True


def test_gerente_vigente_da_superintendencia_pelo_vinculo():
    pessoa = _com_vinculo(GERENCIA_APROVADORA_NOME, "GERENTE")
    # Não vem de capacidade: a Superintendência tem perfil PADRAO (pacote vazio).
    assert CHAVE not in capacidades_sem_cache(pessoa.id)
    assert user_has_policy(pessoa, CHAVE) is True


# ----------------------------------------------------------------------------
# Quem NÃO tem
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("papel", ["EQUIPE", "COORDENADOR", "APOIO", "FORMADOR"])
def test_superintendencia_sem_ser_gerente_nao_tem(papel):
    assert user_has_policy(_com_vinculo(GERENCIA_APROVADORA_NOME, papel), CHAVE) is False


def test_gerente_de_outra_gerencia_nao_tem():
    assert user_has_policy(_com_vinculo("GERENCIA 2", "GERENTE"), CHAVE) is False


@pytest.mark.parametrize("papel", ["COORDENADOR", "APOIO", "FORMADOR"])
def test_papeis_de_campo_nao_tem(papel):
    assert user_has_policy(_com_vinculo("GERENCIA 2", papel), CHAVE) is False


@pytest.mark.parametrize(
    ("nome", "perfil"),
    [("GERENCIA DAT", Gerencia.Perfil.ADMIN_OPERACIONAL), ("CONTROLE", Gerencia.Perfil.CONTROLE)],
)
def test_pacotes_do_dat_e_do_controle_nao_tem(nome, perfil):
    assert user_has_policy(_com_vinculo(nome, "GERENTE", perfil), CHAVE) is False


@pytest.mark.parametrize("papel", ["FORMADOR", "COORDENADOR", "APOIO"])
def test_spe_sem_ser_equipe_ou_gerente_nao_tem(papel):
    """D3 (a): só EQUIPE e GERENTE recebem o pacote."""
    assert user_has_policy(_com_vinculo("SPE", papel, Gerencia.Perfil.SPE), CHAVE) is False


def test_spe_com_vinculo_encerrado_nao_tem():
    ontem = timezone.localdate() - timedelta(days=1)
    pessoa = _com_vinculo("SPE", "EQUIPE", Gerencia.Perfil.SPE, valid_from=ontem - timedelta(days=30), valid_to=ontem)
    assert user_has_policy(pessoa, CHAVE) is False


@pytest.mark.parametrize("papel", ["EQUIPE", "GERENTE"])
def test_spe_nao_aprova_nem_ganha_outra_capacidade(papel):
    """O pacote da SPE é só a Integra. O GERENTE leva também os direitos de evento do papel, como em qualquer
    gerência (`DIREITOS_PAPEL`); isso não vem da SPE."""
    pessoa = _com_vinculo("SPE", papel, Gerencia.Perfil.SPE)
    assert capacidades_sem_cache(pessoa.id) == {CHAVE} | DIREITOS_PAPEL[papel]
    assert solicitation_approval_basis(pessoa) is None


def test_equipe_na_spe_so_abre_a_integra_nas_telas():
    """Nas policies de tela (`/api/me/policies/`), a EQUIPE na SPE fica só com a Integra."""
    pessoa = _com_vinculo("SPE", "EQUIPE", Gerencia.Perfil.SPE)
    assert resolve_public_policies(pessoa) == [CHAVE]


def test_gerente_na_spe_e_o_gerente_de_qualquer_gerencia_mais_a_integra():
    """O GERENTE na SPE vê as telas que o papel GERENTE abre em qualquer gerência (eventos, Grade, Bloqueios,
    Deslocamentos), sem alcance porque a SPE não tem projeto nem formador. A SPE soma só a Integra."""
    na_spe = set(resolve_public_policies(_com_vinculo("SPE", "GERENTE", Gerencia.Perfil.SPE)))
    em_outra = set(resolve_public_policies(_com_vinculo("GERENCIA 2", "GERENTE")))
    assert na_spe - em_outra == {CHAVE}
    assert em_outra <= na_spe


def test_lotacao_na_spe_e_so_do_superusuario():
    """O nome reservado vale antes do perfil (`PERFIL_PERMITIDO`), na tela e nos importadores. Nos importadores,
    a SPE trava todos os papéis: ela não tem projeto nem formador, e o papel de campo traria os direitos de
    evento e as telas de escopo."""
    antes_do_perfil = _gerencia("SPE")
    assert gerencia_reservada(antes_do_perfil) is True
    for papel in ("EQUIPE", "GERENTE", "FORMADOR", "COORDENADOR", "APOIO"):
        assert vinculo_exige_superusuario(antes_do_perfil, papel) is True, papel
    spe = _gerencia("SPE", Gerencia.Perfil.SPE)
    assert gerencia_reservada(spe) is True
    for papel in ("EQUIPE", "GERENTE", "FORMADOR", "COORDENADOR", "APOIO"):
        assert vinculo_exige_superusuario(spe, papel) is True, papel


def test_usuario_comum_nao_tem():
    assert user_has_policy(UsuarioFactory(), CHAVE) is False


def test_grupo_diretoria_sem_vinculo_nao_tem():
    """Desde o PR 12 o grupo é etiqueta: só o vínculo na gerência DIRETORIA dá o pacote."""
    pessoa = UsuarioFactory(groups=["Diretoria"], groups__vinculo=False)
    assert user_has_policy(pessoa, CHAVE) is False


def test_grupos_superintendencia_e_gerente_sem_vinculo_nao_tem():
    pessoa = UsuarioFactory(groups=["Superintendência", "Gerente"], groups__vinculo=False)
    assert user_has_policy(pessoa, CHAVE) is False


def test_seed_poe_a_capacidade_so_no_grupo_diretoria():
    """No modo `uniao` o grupo do seed dá poder: outro grupo aqui abriria a Integra a quem a decisão Q9 deixa fora."""
    from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED

    item = next(i for i in FUNCTIONAL_PERMISSIONS_SEED if i.codename == CHAVE)
    assert item.group_names == ("Diretoria",)


@pytest.mark.usefixtures("modo_uniao")  # a volta de emergência do PR 12: o grupo soma capacidade
def test_modo_uniao_so_o_grupo_diretoria_abre():
    assert user_has_policy(UsuarioFactory(groups=["Diretoria"], groups__vinculo=False), CHAVE) is True
    for grupos in (["Superintendência"], ["Gerente"], ["Superintendência", "Gerente"]):
        assert user_has_policy(UsuarioFactory(groups=grupos, groups__vinculo=False), CHAVE) is False, grupos


def test_gerente_da_superintendencia_com_vinculo_encerrado_nao_tem():
    ontem = timezone.localdate() - timedelta(days=1)
    pessoa = _com_vinculo(GERENCIA_APROVADORA_NOME, "GERENTE", valid_from=ontem - timedelta(days=30), valid_to=ontem)
    assert user_has_policy(pessoa, CHAVE) is False


def test_gerente_da_superintendencia_com_vinculo_desligado_nao_tem():
    assert user_has_policy(_com_vinculo(GERENCIA_APROVADORA_NOME, "GERENTE", ativo=False), CHAVE) is False


def test_anonimo_nao_tem():
    from django.contrib.auth.models import AnonymousUser

    assert user_has_policy(AnonymousUser(), CHAVE) is False


# ----------------------------------------------------------------------------
# Registro, classe, contrato público e simulador
# ----------------------------------------------------------------------------


def test_registro_da_policy():
    assert ACCESS_POLICIES[CHAVE] == frozenset({CHAVE})
    assert CHAVE in COMPOSITE_POLICY_KEYS
    assert CHAVE in PUBLIC_POLICY_KEYS
    assert CanAccessIntegra.policy == CHAVE


def test_pacotes_que_dao_a_capacidade():
    """Só os pacotes DIRETORIA e SPE têm a capacidade."""
    assert {perfil for perfil, caps in PACOTE.items() if CHAVE in caps} == {
        Gerencia.Perfil.DIRETORIA,
        Gerencia.Perfil.SPE,
    }


def _request(usuario: Usuario) -> Any:
    class _Req:
        user = usuario

    return _Req()


def test_classe_drf_segue_a_policy():
    permissao = CanAccessIntegra()
    assert permissao.has_permission(_request(_com_vinculo(GERENCIA_APROVADORA_NOME, "GERENTE")), None) is True
    assert permissao.has_permission(_request(_com_vinculo(GERENCIA_APROVADORA_NOME, "EQUIPE")), None) is False


def test_me_policies_entrega_a_chave_so_a_quem_tem():
    def policies(usuario: Usuario) -> list[str]:
        cache.clear()
        client = APIClient()
        client.force_authenticate(user=usuario)
        return client.get(reverse("core:me-policies")).json()

    assert CHAVE in policies(_com_vinculo(GERENCIA_APROVADORA_NOME, "GERENTE"))
    assert CHAVE in policies(_com_vinculo("DIRETORIA", "EQUIPE", Gerencia.Perfil.DIRETORIA))
    assert CHAVE not in policies(_com_vinculo("GERENCIA 2", "COORDENADOR"))


def test_simulador_le_capacidades_e_o_vinculo_de_hoje():
    """`rbac_diff` passa `capacidades=`: a capacidade simulada abre; o vínculo GERENTE de hoje também."""
    comum = UsuarioFactory()
    assert CHAVE in resolve_public_policies(comum, capacidades={CHAVE})
    assert CHAVE not in resolve_public_policies(comum, capacidades=set())
    gerente = _com_vinculo(GERENCIA_APROVADORA_NOME, "GERENTE")
    assert CHAVE in resolve_public_policies(gerente, capacidades=set())
