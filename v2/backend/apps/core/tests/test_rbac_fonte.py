"""
PR 12 das permissões (ADR-020): o corte. O poder vem só do lugar onde a pessoa trabalha.

`settings.RBAC_FONTE` escolhe a fonte das capacidades e das telas de escopo:
- "lotacao" (padrão, também com a variável vazia): pacote do perfil da gerência (vínculo EQUIPE/GERENTE
  vigente) ∪ direitos do papel vigente. O grupo Django é só etiqueta.
- "uniao": a volta de emergência (`RBAC_FONTE=uniao` no Portainer). Soma também os grupos.

Regras que estes testes travam:
- canário: todos os grupos e nenhum vínculo = nenhuma capacidade, policy, tela ou aprovação;
- o grupo só vale no modo soma; o vínculo vale nos dois;
- a chave do cache inclui a fonte (trocar o modo não serve o poder do modo anterior);
- o simulador recebe a fonte por parâmetro (sem `override_settings` em código de produção, K17) e bate
  com a API no mesmo modo;
- o padrão do código é "lotacao" (K14) e o valor vazio também (K5);
- catraca: as leituras de grupo no código de produção são uma lista fechada (K4).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import re
from collections import Counter
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from rest_framework.test import APIClient

import pytest

from apps.core.constants import FUNCAO_GROUPS, SETOR_GROUPS
from apps.core.models import Gerencia, PermissaoFuncional, Usuario
from apps.core.rbac.policies import (
    COMPOSITE_POLICY_KEYS,
    TELAS_DE_ESCOPO,
    resolve_public_policies,
    solicitation_approval_basis,
    user_has_policy,
)
from apps.core.services.rbac_pacotes import PACOTE
from apps.core.services.rbac_permissions import (
    capacidades_sem_cache,
    get_user_functional_permissions,
    grupos_dao_poder,
)
from apps.core.services.rbac_snapshot import snapshot_de_poder
from apps.core.tests.factories import UsuarioFactory, com_pacote_do_controle, com_pacote_do_dat
from config.settings import ler_rbac_fonte

pytestmark = pytest.mark.django_db

UNIAO = override_settings(RBAC_FONTE="uniao")
LOTACAO = override_settings(RBAC_FONTE="lotacao")


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


def _so_grupos(*nomes: str) -> Usuario:
    """Pessoa com os grupos e sem nenhum vínculo (`groups__vinculo=False`)."""
    return UsuarioFactory(groups=list(nomes), groups__vinculo=False)


def _do_grupo(nome: str) -> set[str]:
    return set(PermissaoFuncional.objects.filter(groups__name=nome).values_list("codename", flat=True))


class TestSetting:
    def test_padrao_do_codigo_e_lotacao(self):
        """K14: a CI roda no modo que vai para produção. Trocar o padrão para "uniao" quebra aqui."""
        assert settings.RBAC_FONTE == "lotacao"
        assert ler_rbac_fonte(None) == "lotacao"

    def test_vazio_vale_o_padrao(self):
        """K5: `RBAC_FONTE=` no Portainer (o jeito comum de desfazer a volta) não derruba a subida."""
        assert ler_rbac_fonte("") == "lotacao"
        assert ler_rbac_fonte("   ") == "lotacao"

    def test_aceita_os_dois_modos_sem_caixa_nem_espaco(self):
        assert ler_rbac_fonte("uniao") == "uniao"
        assert ler_rbac_fonte(" UNIAO ") == "uniao"
        assert ler_rbac_fonte("Lotacao") == "lotacao"

    @pytest.mark.parametrize("valor", ["união", "grupos", "soma", "1"])
    def test_valor_invalido_derruba_a_subida(self, valor):
        with pytest.raises(ImproperlyConfigured):
            ler_rbac_fonte(valor)

    def test_predicado_segue_a_setting_ou_o_parametro(self):
        with UNIAO:
            assert grupos_dao_poder() is True
            assert grupos_dao_poder("lotacao") is False
        with LOTACAO:
            assert grupos_dao_poder() is False
            assert grupos_dao_poder("uniao") is True


class TestCanario:
    def test_todos_os_grupos_sem_vinculo_nao_dao_nada(self):
        """6.1: nenhuma leitura de grupo vaza para capacidades, policies, telas ou aprovação."""
        for nome in ("Gestor Tecnologico", "Programador"):
            Group.objects.get_or_create(name=nome)
        pessoa = _so_grupos(*SETOR_GROUPS, *FUNCAO_GROUPS, "Gestor Tecnologico", "Programador")
        assert pessoa.groups.count() == len(set(SETOR_GROUPS) | set(FUNCAO_GROUPS)) + 2
        with LOTACAO:
            assert capacidades_sem_cache(pessoa.id) == set()
            assert get_user_functional_permissions(pessoa) == set()
            assert resolve_public_policies(pessoa) == []
            for chave in COMPOSITE_POLICY_KEYS:
                assert not user_has_policy(pessoa, chave), chave
            assert solicitation_approval_basis(pessoa) is None

    def test_no_modo_soma_o_mesmo_canario_tem_os_grupos(self):
        """Controle positivo do canário: o modo soma ainda lê os grupos (a volta funciona)."""
        pessoa = _so_grupos("DAT", "Controle", "Diretoria")
        with UNIAO:
            assert capacidades_sem_cache(pessoa.id) == _do_grupo("DAT") | _do_grupo("Controle") | _do_grupo("Diretoria")
            for chave in TELAS_DE_ESCOPO:
                assert user_has_policy(pessoa, chave), chave


class TestCapacidades:
    def test_grupo_dat_sozinho_nada_no_corte_e_o_grupo_na_soma(self):
        pessoa = _so_grupos("DAT")
        with LOTACAO:
            assert capacidades_sem_cache(pessoa.id) == set()
        with UNIAO:
            assert capacidades_sem_cache(pessoa.id) == _do_grupo("DAT")
            assert _do_grupo("DAT")

    def test_grupo_dat_com_vinculo_na_g19_da_exatamente_o_pacote(self):
        pessoa = _so_grupos("DAT")
        com_pacote_do_dat(pessoa)
        with LOTACAO:
            assert capacidades_sem_cache(pessoa.id) == set(PACOTE["ADMIN_OPERACIONAL"])
        with UNIAO:
            assert capacidades_sem_cache(pessoa.id) == set(PACOTE["ADMIN_OPERACIONAL"]) | _do_grupo("DAT")

    def test_grupo_controle_sozinho_nada_e_com_vinculo_o_pacote(self):
        pessoa = _so_grupos("Controle")
        with LOTACAO:
            assert capacidades_sem_cache(pessoa.id) == set()
        com_pacote_do_controle(pessoa)
        with LOTACAO:
            assert capacidades_sem_cache(pessoa.id) == set(PACOTE["CONTROLE"])

    def test_vinculo_sem_grupo_vale_nos_dois_modos(self):
        pessoa = UsuarioFactory()
        com_pacote_do_controle(pessoa)
        for modo in (LOTACAO, UNIAO):
            with modo:
                assert capacidades_sem_cache(pessoa.id) == set(PACOTE["CONTROLE"])

    def test_parametro_fonte_vence_a_setting(self):
        pessoa = _so_grupos("DAT")
        with LOTACAO:
            assert capacidades_sem_cache(pessoa.id, fonte="uniao") == _do_grupo("DAT")
        with UNIAO:
            assert capacidades_sem_cache(pessoa.id, fonte="lotacao") == set()


class TestTelasDeEscopo:
    def test_grupo_controle_sozinho_fecha_as_telas_no_corte(self):
        pessoa = _so_grupos("Controle")
        with LOTACAO:
            for chave in TELAS_DE_ESCOPO:
                assert not user_has_policy(pessoa, chave), chave
        with UNIAO:
            for chave in TELAS_DE_ESCOPO:
                assert user_has_policy(pessoa, chave), chave

    def test_parametro_fonte_chega_nas_telas(self):
        pessoa = _so_grupos("Controle")
        with LOTACAO:
            assert set(TELAS_DE_ESCOPO) <= set(resolve_public_policies(pessoa, capacidades=set(), fonte="uniao"))
        with UNIAO:
            assert not set(TELAS_DE_ESCOPO) & set(resolve_public_policies(pessoa, capacidades=set(), fonte="lotacao"))


class TestCache:
    def test_trocar_a_fonte_nao_serve_o_cache_do_outro_modo(self):
        """Sem bump: a chave inclui a fonte (R9)."""
        pessoa = _so_grupos("DAT")
        with UNIAO:
            assert get_user_functional_permissions(pessoa) == _do_grupo("DAT")
        with LOTACAO:
            assert get_user_functional_permissions(pessoa) == set()
        with UNIAO:
            assert get_user_functional_permissions(pessoa) == _do_grupo("DAT")

    def test_invalidar_limpa_os_dois_modos(self):
        """Uma mudança de vínculo feita num modo não deixa o outro modo com o poder velho no cache."""
        from apps.core.services.rbac_permissions import invalidate_user_functional_permissions_cache

        pessoa = UsuarioFactory()
        with UNIAO:
            assert get_user_functional_permissions(pessoa) == set()
        with LOTACAO:
            com_pacote_do_controle(pessoa)  # invalida no modo lotação
            invalidate_user_functional_permissions_cache(pessoa.pk)
        with UNIAO:
            assert get_user_functional_permissions(pessoa) == set(PACOTE["CONTROLE"])


class TestSuperusuario:
    def test_igual_nos_dois_modos(self):
        su = UsuarioFactory(superuser=True)
        resultados = []
        for modo in (LOTACAO, UNIAO):
            with modo:
                resultados.append(resolve_public_policies(su))
        assert resultados[0] == resultados[1]
        assert resultados[0]


class TestSimuladorEApi:
    @pytest.mark.parametrize("fonte", ["lotacao", "uniao"])
    def test_snapshot_com_fonte_igual_a_api_no_mesmo_modo(self, fonte):
        so_grupo = _so_grupos("DAT", "Controle")
        lotada = UsuarioFactory()
        com_pacote_do_dat(lotada)
        pessoas = [so_grupo, lotada]
        retrato = snapshot_de_poder(Usuario.objects.filter(id__in=[p.id for p in pessoas]), fonte=fonte)
        with override_settings(RBAC_FONTE=fonte):
            for pessoa in pessoas:
                client = APIClient()
                client.force_authenticate(user=pessoa)
                me = client.get("/api/me/")
                policies = client.get("/api/me/policies/")
                assert me.status_code == 200 and policies.status_code == 200
                assert retrato[f"u{pessoa.id}"]["capacidades"] == me.json()["permissions"]
                assert retrato[f"u{pessoa.id}"]["policies"] == policies.json()
                assert me.json()["permissions"] == sorted(capacidades_sem_cache(pessoa.id))

    def test_snapshot_simulado_nao_depende_da_setting(self):
        so_grupo = _so_grupos("Controle")
        qs = Usuario.objects.filter(id=so_grupo.id)
        with UNIAO:
            simulado = snapshot_de_poder(qs, fonte="lotacao")[f"u{so_grupo.id}"]
        assert simulado["capacidades"] == []
        assert not set(TELAS_DE_ESCOPO) & set(simulado["policies"])
        with LOTACAO:
            simulado = snapshot_de_poder(qs, fonte="uniao")[f"u{so_grupo.id}"]
        assert simulado["capacidades"] == sorted(_do_grupo("Controle"))
        assert set(TELAS_DE_ESCOPO) <= set(simulado["policies"])


class TestComandoRbacDiff:
    def test_salvar_simulando_a_fonte(self, tmp_path):
        """K3 (passo 0 da volta): `--salvar --simular-fonte uniao` mostra o que a volta daria, sem trocar o modo."""
        import json

        from django.core.management import call_command

        so_grupo = _so_grupos("DAT")
        uniao, lotacao = tmp_path / "uniao.json", tmp_path / "lotacao.json"
        with LOTACAO:
            call_command("rbac_diff", "--salvar", str(uniao), "--simular-fonte", "uniao", stdout=StringIO())
            call_command("rbac_diff", "--salvar", str(lotacao), stdout=StringIO())
        chave = f"u{so_grupo.id}"
        assert json.loads(uniao.read_text(encoding="utf-8"))[chave]["capacidades"] == sorted(_do_grupo("DAT"))
        assert json.loads(lotacao.read_text(encoding="utf-8"))[chave]["capacidades"] == []

    def test_simular_fonte_so_com_salvar(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command("rbac_diff", "--diagnostico", "--simular-fonte", "uniao", stdout=StringIO())

    @pytest.mark.parametrize("fonte", ["lotacao", "uniao"])
    def test_diagnostico_mostra_a_fonte_ativa(self, fonte):
        from django.core.management import call_command

        saida = StringIO()
        with override_settings(RBAC_FONTE=fonte):
            call_command("rbac_diff", "--diagnostico", stdout=saida)
        assert f"fonte ativa: {fonte}" in saida.getvalue()


def test_gerencia_diretoria_da_o_pacote_diretoria():
    """C8 (dúvida 2 do dono: sim): o caminho da Diretoria pelo lugar."""
    from apps.core.services.rbac_pacotes import PERFIL_PERMITIDO

    assert PERFIL_PERMITIDO["DIRETORIA"] == Gerencia.Perfil.DIRETORIA
    pessoa = UsuarioFactory()
    gerencia = Gerencia.objects.create(nome="DIRETORIA", nome_setor="Diretoria", perfil=Gerencia.Perfil.DIRETORIA)
    from apps.core.tests.factories import com_papel

    com_papel(pessoa, "EQUIPE", gerencia)
    with LOTACAO:
        assert capacidades_sem_cache(pessoa.id) == set(PACOTE["DIRETORIA"])


# ---------------------------------------------------------------------------
# Catraca das leituras de grupo (K4, teste 11 do plano)
# ---------------------------------------------------------------------------
# `scripts/rbac_lint.py` não serve: isenta `apps/core/rbac/` inteira e só vê `groups.filter(name=…)`.
# Cada arquivo de produção do backend que lê grupo aparece aqui com o número de ocorrências e o motivo.
# Leitura nova = este teste vermelho: ou ela é exibição/escopo e entra na lista, ou ela dá poder e tem de
# passar por `grupos_dao_poder()`.
_PADROES_DE_LEITURA = re.compile(r"\.groups\.filter\(|groups__name|groups__id|groups__user|\.groups\.values_list\(")

LEITURAS_DE_GRUPO: dict[str, tuple[int, str]] = {
    "apps/core/admin.py": (2, "auditoria: grupos antes e depois do save no /admin/"),
    "apps/core/rbac/__init__.py": (1, "docstring (exemplo do que não fazer)"),
    "apps/core/rbac/helpers.py": (4, "2 em docstring + 2 de escopo de dado: avaliáveis por cargo (PR 13)"),
    "apps/core/rbac/policies.py": (1, "poder: telas de escopo, só com grupos_dao_poder()"),
    "apps/core/rbac_signals.py": (2, "cache: limpa quem muda de grupo"),
    "apps/core/serializers/usuario.py": (1, "auditoria: grupos antes do save do usuário"),
    "apps/core/services/audit.py": (1, "auditoria: grupos da capacidade"),
    "apps/core/services/bloqueios_import.py": (1, "escopo de dado: quem é formadora no import (PR 13)"),
    "apps/core/services/lgpd_export_service.py": (1, "exibição: export LGPD do titular"),
    "apps/core/services/notificacoes_acoes_service.py": (4, "escopo de dado: destinatários (PR 13)"),
    "apps/core/services/rbac_permissions.py": (2, "poder: parcela dos grupos (só com grupos_dao_poder) + cache"),
    "apps/core/services/rbac_snapshot.py": (2, "diagnóstico e auditoria do rbac_diff (só leitura)"),
    "apps/core/signals.py": (1, "cache: limpa quem tem a capacidade alterada"),
    "apps/core/views/admin.py": (2, "auditoria: grupos antes e depois do assign_groups"),
    "apps/core/views/stats.py": (1, "escopo de dado: has_formador_group do painel (PR 13)"),
    "apps/core/views_auth.py": (1, "exibição: groups/setores/funcoes do login"),
    "apps/core/views_basic.py": (1, "exibição: groups/setores/funcoes do /api/me/"),
    "apps/dev_tools/management/commands/migrate_rbac_groups.py": (2, "dev_tools (prod desligado)"),
    "apps/dev_tools/management/commands/seed_gerentes.py": (1, "dev_tools (prod desligado)"),
}


def _leituras_de_grupo_no_codigo() -> dict[str, int]:
    raiz = Path(__file__).resolve().parents[3]  # .../backend
    contagem: Counter[str] = Counter()
    for arquivo in (raiz / "apps").rglob("*.py"):
        relativo = arquivo.relative_to(raiz).as_posix()
        if "/tests/" in relativo or "/migrations/" in relativo:
            continue
        n = len(_PADROES_DE_LEITURA.findall(arquivo.read_text(encoding="utf-8")))
        if n:
            contagem[relativo] = n
    return dict(contagem)


def test_catraca_das_leituras_de_grupo():
    achadas = _leituras_de_grupo_no_codigo()
    esperadas = {arquivo: n for arquivo, (n, _motivo) in LEITURAS_DE_GRUPO.items()}
    assert achadas == esperadas, (
        "Leitura de grupo nova ou removida no código de produção. Se dá poder, passe por "
        "grupos_dao_poder(); se é exibição ou escopo de dado, atualize LEITURAS_DE_GRUPO com o motivo."
    )
