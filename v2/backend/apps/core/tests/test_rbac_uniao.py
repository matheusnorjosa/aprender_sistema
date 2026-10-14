"""
PR B da arquitetura de permissões (ADR-020, PR 6 do relatório): fórmula em modo união.

Capacidades = grupos ∪ pacote do perfil (`services/rbac_pacotes.PACOTE`) de cada gerência onde a
pessoa tem vínculo VIGENTE com papel EQUIPE ou GERENTE (D3). Enquanto toda gerência for PADRAO o
pacote é vazio e ninguém muda, por construção (`rbac_diff` 0/0).

Regras que estes testes travam:
- uma fórmula só: a da API (`get_user_functional_permissions`) e a do simulador
  (`rbac_snapshot.capacidades_de_hoje`) são a mesma função (`capacidades_sem_cache`);
- FORMADOR, COORDENADOR e APOIO nunca recebem pacote; vínculo inativo, vencido ou futuro também não;
- o pacote não depende de `Gerencia.ativo` (mesmo critério de `user_is_gerente_superintendencia`);
- o cache cai quando o vínculo ou o perfil muda, só depois do commit (o ensaio com rollback não mexe
  no cache).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, PermissaoFuncional, Usuario
from apps.core.rbac.helpers import GERENCIA_APROVADORA_NOME
from apps.core.rbac.matrix import ACTOR_GROUPS, SUPERUSER
from apps.core.rbac.policies import PUBLIC_POLICY_KEYS, resolve_public_policies, solicitation_approval_basis
from apps.core.services.rbac_pacotes import PACOTE
from apps.core.services.rbac_permissions import get_user_functional_permissions
from apps.core.services.rbac_snapshot import capacidades_de_hoje, snapshot_de_poder
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

ADMIN_OPERACIONAL = PACOTE["ADMIN_OPERACIONAL"]


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def g19() -> Gerencia:
    """A gerência do DAT de produção (`nome` = código interno), já com o perfil do PR 5."""
    g, _ = Gerencia.objects.get_or_create(nome="GERENCIA DAT", defaults={"nome_setor": "DAT"})
    g.perfil = Gerencia.Perfil.ADMIN_OPERACIONAL
    g.save()
    return g


def _vincula(usuario: Usuario, gerencia: Gerencia, papel: str, **extra: Any) -> EquipeGerencia:
    extra.setdefault("ativo", True)
    return EquipeGerencia.objects.create(usuario=usuario, gerencia=gerencia, papel=papel, **extra)


def _dos_grupos(usuario: Usuario) -> set[str]:
    """Capacidades só pelos grupos: a fórmula de antes do PR B."""
    return set(PermissaoFuncional.objects.filter(groups__user__id=usuario.id).values_list("codename", flat=True))


def _caps(usuario: Usuario) -> set[str]:
    cache.clear()
    return get_user_functional_permissions(usuario)


class TestFormula:
    def test_uniao_igual_grupos_com_todas_gerencias_padrao(self):
        padrao = Gerencia.objects.create(nome="GERENCIA UNIAO PADRAO", nome_setor="Uniao")
        for ator, grupos in ACTOR_GROUPS.items():
            if ator == SUPERUSER:
                continue
            usuario = UsuarioFactory(groups=grupos)
            _vincula(usuario, padrao, "EQUIPE")
            _vincula(usuario, padrao, "GERENTE")
            assert _caps(usuario) == _dos_grupos(usuario), ator
            assert capacidades_de_hoje(usuario) == _dos_grupos(usuario), ator

    def test_equipe_em_gerencia_admin_operacional_recebe_exatamente_o_pacote(self, g19):
        pessoa = UsuarioFactory()
        _vincula(pessoa, g19, "EQUIPE")
        assert ADMIN_OPERACIONAL
        assert _caps(pessoa) == set(ADMIN_OPERACIONAL)

    def test_gerente_em_gerencia_com_perfil_recebe_pacote(self, g19):
        gerente = UsuarioFactory(groups=["Gerente"])
        _vincula(gerente, g19, "GERENTE")
        assert _caps(gerente) == _dos_grupos(gerente) | ADMIN_OPERACIONAL
        assert ADMIN_OPERACIONAL - _dos_grupos(gerente), "o grupo Gerente não pode já cobrir o pacote"

    @pytest.mark.parametrize("papel", ["FORMADOR", "COORDENADOR", "APOIO"])
    def test_formador_coordenador_apoio_nao_recebem_pacote(self, g19, papel):
        pessoa = UsuarioFactory()
        _vincula(pessoa, g19, papel)
        assert _caps(pessoa) == set()

    def test_vinculo_inativo_vencido_ou_futuro_nao_da_pacote(self, g19):
        hoje = timezone.localdate()
        inativo, vencido, futuro = UsuarioFactory(), UsuarioFactory(), UsuarioFactory()
        _vincula(inativo, g19, "EQUIPE", ativo=False)
        _vincula(vencido, g19, "EQUIPE", valid_from=hoje - timedelta(days=30), valid_to=hoje - timedelta(days=1))
        _vincula(futuro, g19, "EQUIPE", valid_from=hoje + timedelta(days=1))
        for pessoa in (inativo, vencido, futuro):
            assert _caps(pessoa) == set(), pessoa.id

    def test_pacote_independe_de_gerencia_ativo(self, g19):
        g19.ativo = False
        g19.save()
        pessoa = UsuarioFactory()
        _vincula(pessoa, g19, "EQUIPE")
        assert _caps(pessoa) == set(ADMIN_OPERACIONAL)

    def test_aprovador_inalterado_com_aprovacao_vazio(self):
        g1, _ = Gerencia.objects.get_or_create(nome=GERENCIA_APROVADORA_NOME, defaults={"nome_setor": "Super"})
        g1.perfil = Gerencia.Perfil.APROVACAO
        g1.save()
        gerente = UsuarioFactory()
        _vincula(gerente, g1, "GERENTE")
        assert solicitation_approval_basis(gerente) == "gerente_superintendencia"
        assert _caps(gerente) == set()

    def test_superusuario_inalterado(self, g19):
        superusuario = UsuarioFactory(is_superuser=True)
        assert _caps(superusuario) == _dos_grupos(superusuario)
        assert resolve_public_policies(superusuario) == sorted(PUBLIC_POLICY_KEYS)


class TestCache:
    def test_cache_invalida_ao_criar_e_encerrar_vinculo(self, g19, django_capture_on_commit_callbacks):
        pessoa = UsuarioFactory()
        assert get_user_functional_permissions(pessoa) == set()  # cache quente, vazio

        with django_capture_on_commit_callbacks(execute=True):
            vinculo = _vincula(pessoa, g19, "EQUIPE")
        assert get_user_functional_permissions(pessoa) == set(ADMIN_OPERACIONAL)

        with django_capture_on_commit_callbacks(execute=True):
            vinculo.valid_to = timezone.localdate() - timedelta(days=1)
            vinculo.valid_from = vinculo.valid_to
            vinculo.save()
        assert get_user_functional_permissions(pessoa) == set()

    def test_cache_invalida_ao_excluir_vinculo(self, g19, django_capture_on_commit_callbacks):
        pessoa = UsuarioFactory()
        vinculo = _vincula(pessoa, g19, "EQUIPE")
        assert get_user_functional_permissions(pessoa) == set(ADMIN_OPERACIONAL)
        with django_capture_on_commit_callbacks(execute=True):
            vinculo.delete()
        assert get_user_functional_permissions(pessoa) == set()

    def test_cache_invalida_ao_mudar_perfil(self, django_capture_on_commit_callbacks):
        gerencia = Gerencia.objects.create(nome="GERENCIA UNIAO PERFIL", nome_setor="Perfil")
        pessoa = UsuarioFactory()
        _vincula(pessoa, gerencia, "EQUIPE")
        assert get_user_functional_permissions(pessoa) == set()  # cache quente, vazio

        with django_capture_on_commit_callbacks(execute=True):
            gerencia.perfil = Gerencia.Perfil.ADMIN_OPERACIONAL
            gerencia.save()
        assert get_user_functional_permissions(pessoa) == set(ADMIN_OPERACIONAL)

        with django_capture_on_commit_callbacks(execute=True):
            gerencia.perfil = Gerencia.Perfil.PADRAO
            gerencia.save()
        assert get_user_functional_permissions(pessoa) == set()

    def test_cache_intacto_quando_transacao_faz_rollback(self, g19, django_capture_on_commit_callbacks):
        pessoa = UsuarioFactory()
        assert get_user_functional_permissions(pessoa) == set()  # cache quente, vazio

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    _vincula(pessoa, g19, "EQUIPE")
                    g19.perfil = Gerencia.Perfil.CONTROLE
                    g19.save()
                    raise RuntimeError("ensaio")
            except RuntimeError:
                pass
        assert callbacks == []
        # Nem o vínculo nem o perfil ficaram; o cache também não foi tocado.
        assert not EquipeGerencia.objects.filter(usuario=pessoa).exists()
        assert get_user_functional_permissions(pessoa) == set()

    def test_ensaio_nao_invalida_antes_do_commit(self, g19):
        # Dentro da transação (sem commit), a invalidação fica pendente: um request concorrente
        # não repovoa o cache com o estado velho entre a invalidação e o commit.
        pessoa = UsuarioFactory()
        assert get_user_functional_permissions(pessoa) == set()
        _vincula(pessoa, g19, "EQUIPE")
        assert get_user_functional_permissions(pessoa) == set()  # ainda o cache de antes


class TestQuemLeCapacidade:
    def test_snapshot_reflete_pacote(self, g19):
        pessoa, formador = UsuarioFactory(), UsuarioFactory()
        _vincula(pessoa, g19, "EQUIPE")
        _vincula(formador, g19, "FORMADOR")
        retrato = snapshot_de_poder(Usuario.objects.filter(id__in=[pessoa.id, formador.id]))
        assert retrato[f"u{pessoa.id}"]["capacidades"] == sorted(ADMIN_OPERACIONAL)
        assert "manage_admin_registries" in retrato[f"u{pessoa.id}"]["policies"]
        assert retrato[f"u{formador.id}"]["capacidades"] == []
        assert capacidades_de_hoje(pessoa) == _caps(pessoa)

    def test_api_me_permissions_reflete_pacote(self, g19):
        pessoa = UsuarioFactory()
        _vincula(pessoa, g19, "EQUIPE")
        client = APIClient()
        client.force_authenticate(user=pessoa)
        resposta = client.get("/api/me/")
        assert resposta.status_code == 200
        assert resposta.json()["permissions"] == sorted(ADMIN_OPERACIONAL)
