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
- catraca: cada acesso a grupo no código de produção (lido pela árvore sintática, não por linha) está numa
  lista fechada, e os de poder estão sob `grupos_dao_poder()` (K4); todos os grupos sem vínculo = sem grupo
  (status e, nos GET, corpo) em cada recurso de `RESOURCES`, com linhas de outra gerência no banco.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import ast
from collections import Counter
from datetime import date
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
from apps.core.models import Deslocamento, Gerencia, PermissaoFuncional, Usuario
from apps.core.rbac.matrix import RESOURCES
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
from apps.core.tests.factories import (
    GerenciaFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    UsuarioFactory,
    com_pacote_do_controle,
    com_pacote_do_dat,
    com_papel,
)
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
        """Controle positivo do canário: o modo soma ainda lê os grupos (a volta funciona). E a volta não traz
        de volta a aprovação por grupo (PR 11): nem os pares Controle + Assistente Administrativo e
        Superintendência + Gerente aprovam."""
        grupos = ("DAT", "Controle", "Diretoria", "Assistente Administrativo", "Superintendência", "Gerente")
        pessoa = _so_grupos(*grupos)
        with UNIAO:
            assert capacidades_sem_cache(pessoa.id) == set().union(*(_do_grupo(nome) for nome in grupos))
            for chave in TELAS_DE_ESCOPO:
                assert user_has_policy(pessoa, chave), chave
            assert solicitation_approval_basis(pessoa) is None


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
    com_papel(pessoa, "EQUIPE", gerencia)
    with LOTACAO:
        assert capacidades_sem_cache(pessoa.id) == set(PACOTE["DIRETORIA"])


# ---------------------------------------------------------------------------
# Catraca das leituras de grupo (K4, teste 11 do plano)
# ---------------------------------------------------------------------------
# `scripts/rbac_lint.py` não serve: isenta `apps/core/rbac/` inteira e só vê `groups.filter(name=…)`.
# A varredura é pela árvore sintática dos .py de produção do backend, não por regex de linha: o formato
# que o Black quebra em várias linhas, o apelido (`grupos = user.groups`) e `getattr(user, "groups")`
# também aparecem. Conta como acesso a grupo: atributo `groups` ou `user_set`; argumento nomeado `groups`
# ou `groups__*` em qualquer chamada; `user` ou `user__*` numa chamada sobre `Group.objects`; e
# `getattr(_, "groups" | "user_set")`. Cada acesso vira o trecho normalizado (`ast.unparse`) da expressão
# que o contém (a cadeia de atributos e chamadas), e cada trecho aparece aqui com o motivo. A conferência é
# por trecho, não por contagem por arquivo: trocar uma leitura com portão por outra sem portão, no mesmo
# arquivo, também fica vermelho. Os trechos PODER ainda precisam estar sob `grupos_dao_poder(...)` (dentro
# do `if` ou à direita do `and`). Trecho novo = este teste vermelho: ou ele é exibição/escopo e entra na
# lista, ou ele dá poder e tem de passar por `grupos_dao_poder()`.
_ATRIBUTOS_DE_GRUPO = frozenset({"groups", "user_set"})

PODER = "poder: só com grupos_dao_poder()"
EXIBICAO = "exibição: etiqueta, contagem ou export do titular"
AUDITORIA = "auditoria: grupos antes e depois da gravação"
CACHE = "cache: limpa quem muda de grupo ou de capacidade"
ESCRITA = "escrita: grava a etiqueta (sem poder no corte; recusar é o PR 13)"
ESCOPO = "escopo de dado por cargo (PR 13)"
DIAGNOSTICO = "diagnóstico do rbac_diff (só leitura)"
SEED = "seed das capacidades dos grupos (a volta)"
DEV_TOOLS = "dev_tools (desligado em produção)"

LEITURAS_DE_GRUPO: tuple[tuple[str, str, str], ...] = (
    ("apps/core/admin.py", "obj.groups.values_list('pk', flat=True)", AUDITORIA),
    ("apps/core/admin.py", "obj.groups.values_list('pk', flat=True)", AUDITORIA),
    ("apps/core/admin.py", "obj.groups.count()", EXIBICAO),
    (
        "apps/core/rbac/helpers.py",
        "qs.filter(groups__name__in=FORMADOR_ROLE_GROUPS).exclude(groups__name__in=FUNCAO_COORDENADOR_GROUPS)"
        ".distinct()",
        ESCOPO,
    ),
    ("apps/core/rbac/policies.py", "user.groups.filter(name__in=setores_da_tela).exists()", PODER),
    ("apps/core/rbac_signals.py", "receiver(m2m_changed, sender=User.groups.through)", CACHE),
    ("apps/core/rbac_signals.py", "instance.user_set.values_list('id', flat=True)", CACHE),
    ("apps/core/rbac_signals.py", "instance.user_set.values_list('id', flat=True)", CACHE),
    ("apps/core/rbac_signals.py", "receiver(m2m_changed, sender=PermissaoFuncional.groups.through)", CACHE),
    ("apps/core/rbac_signals.py", "instance.groups.values_list('id', flat=True)", CACHE),
    ("apps/core/rbac_signals.py", "instance.groups.values_list('id', flat=True)", CACHE),
    ("apps/core/serializers/usuario.py", "obj.groups.all()", EXIBICAO),
    ("apps/core/serializers/usuario.py", "user.groups.all()", AUDITORIA),
    ("apps/core/serializers/usuario.py", "user.groups.set(final)", ESCRITA),
    ("apps/core/serializers/usuario.py", "instance.groups.values_list('pk', flat=True)", AUDITORIA),
    ("apps/core/serializers/usuario.py", "obj.user_set.count()", EXIBICAO),
    ("apps/core/serializers/usuario.py", "obj.groups.all().order_by('name')", EXIBICAO),
    ("apps/core/services/audit.py", "cap.groups.values_list('pk', flat=True)", AUDITORIA),
    ("apps/core/services/bloqueios_import.py", "usuario.groups.filter(name='Formador').exists()", ESCOPO),
    ("apps/core/services/export_contract_importer.py", "usuario.groups.add(grupo)", ESCRITA),
    (
        "apps/core/services/functional_permissions_seed.py",
        "perm.groups.set([groups_by_name[name] for name in item.group_names])",
        SEED,
    ),
    ("apps/core/services/functional_permissions_seed.py", "perm.groups.exists()", SEED),
    ("apps/core/services/functional_permissions_seed.py", "perm.groups.clear()", SEED),
    ("apps/core/services/lgpd_export_service.py", "user.groups.values_list('name', flat=True)", EXIBICAO),
    (
        "apps/core/services/notificacoes_acoes_service.py",
        "Usuario.objects.filter(is_active=True, groups__id__in=list(executor_group_ids)).values_list('id', flat=True)",
        ESCOPO,
    ),
    (
        "apps/core/services/notificacoes_acoes_service.py",
        "Usuario.objects.filter(is_active=True, id__in=executor_user_ids, groups__name__in=list(role_group_names))"
        ".distinct()",
        ESCOPO,
    ),
    (
        "apps/core/services/notificacoes_acoes_service.py",
        "Usuario.objects.filter(is_active=True, groups__name__in=list(role_group_names)).distinct()",
        ESCOPO,
    ),
    (
        "apps/core/services/rbac_permissions.py",
        "User.objects.filter(groups__id__in=normalized_ids).values_list('id', flat=True).distinct()",
        CACHE,
    ),
    (
        "apps/core/services/rbac_permissions.py",
        "PermissaoFuncional.objects.filter(groups__user__id=user_id).order_by().values_list('codename', flat=True)",
        PODER,
    ),
    ("apps/core/services/rbac_snapshot.py", "usuario.groups.all()", DIAGNOSTICO),
    (
        "apps/core/services/rbac_snapshot.py",
        "Usuario.objects.filter(is_active=True, groups__name=setor).values_list('id', flat=True)",
        DIAGNOSTICO,
    ),
    (
        "apps/core/services/rbac_snapshot.py",
        "PermissaoFuncional.objects.filter(groups__isnull=False).values_list('groups__name', 'codename')",
        DIAGNOSTICO,
    ),
    ("apps/core/services/usuarios_import.py", "usuario.groups.add(*permitidos)", ESCRITA),
    ("apps/core/signals.py", "receiver(m2m_changed, sender=PermissaoFuncional.groups.through)", CACHE),
    ("apps/core/signals.py", "instance.groups.values_list('pk', flat=True)", CACHE),
    ("apps/core/views/admin.py", "usuario.groups.values_list('id', flat=True)", AUDITORIA),
    ("apps/core/views/admin.py", "usuario.groups.set(groups)", ESCRITA),
    ("apps/core/views/admin.py", "usuario.groups.values_list('id', flat=True)", AUDITORIA),
    ("apps/core/views/admin.py", "group.user_set.values_list('id', flat=True)", AUDITORIA),
    ("apps/core/views/admin.py", "group.user_set.set(users)", ESCRITA),
    ("apps/core/views/stats.py", "user.groups.filter(name__in=FORMADOR_ROLE_GROUPS).exists()", ESCOPO),
    ("apps/core/views_auth.py", "user.groups.values_list('name', flat=True)", EXIBICAO),
    ("apps/core/views_basic.py", "user.groups.values_list('name', flat=True)", EXIBICAO),
    (
        "apps/dev_tools/management/commands/migrate_rbac_groups.py",
        "user.groups.values_list('name', flat=True)",
        DEV_TOOLS,
    ),
    (
        "apps/dev_tools/management/commands/migrate_rbac_groups.py",
        "user.groups.values_list('name', flat=True)",
        DEV_TOOLS,
    ),
    ("apps/dev_tools/management/commands/migrate_rbac_groups.py", "user.groups.add(gerente_group)", DEV_TOOLS),
    ("apps/dev_tools/management/commands/migrate_rbac_groups.py", "user.groups.add(gerente_group)", DEV_TOOLS),
    ("apps/dev_tools/management/commands/seed_e2e_users.py", "usuario.groups.all()", DEV_TOOLS),
    ("apps/dev_tools/management/commands/seed_e2e_users.py", "user.groups.set(user_data['groups'])", DEV_TOOLS),
    (
        "apps/dev_tools/management/commands/seed_frontend_contract_data.py",
        "dat_user.groups.set([dat_group])",
        DEV_TOOLS,
    ),
    (
        "apps/dev_tools/management/commands/seed_frontend_contract_data.py",
        "pessoa_longa.groups.set(Group.objects.filter(name='Formador'))",
        DEV_TOOLS,
    ),
    (
        "apps/dev_tools/management/commands/seed_gerentes.py",
        "usuario.groups.filter(name='Gerente').exists()",
        DEV_TOOLS,
    ),
    ("apps/dev_tools/management/commands/seed_gerentes.py", "usuario.groups.add(gerente_group)", DEV_TOOLS),
    (
        "apps/dev_tools/management/commands/seed_gerentes.py",
        "Group.objects.get(name='Gerente').user_set.count()",
        DEV_TOOLS,
    ),
)

_RAIZ_DO_BACKEND = Path(__file__).resolve().parents[3]


def _sobre_group_objects(func: ast.expr) -> bool:
    """A chamada sai de `Group.objects` (ex.: `Group.objects.filter(...)`, `Group.objects.all().exclude(...)`)."""
    no: ast.expr = func
    while isinstance(no, (ast.Attribute, ast.Call)):
        if isinstance(no, ast.Call):
            no = no.func
        elif no.attr == "objects" and isinstance(no.value, ast.Name) and no.value.id == "Group":
            return True
        else:
            no = no.value
    return False


def _eh_acesso_a_grupo(no: ast.AST, pais: dict[ast.AST, ast.AST]) -> bool:
    pai = pais.get(no)
    if isinstance(no, ast.Attribute):
        # `x.groups()` é método (ex.: `re.Match.groups()`); o gerenciador de grupos do Django não é chamado.
        return no.attr in _ATRIBUTOS_DE_GRUPO and not (isinstance(pai, ast.Call) and pai.func is no)
    if isinstance(no, ast.keyword) and no.arg and isinstance(pai, ast.Call):
        if no.arg.startswith("groups__"):
            return True
        if no.arg == "groups":
            # `"...{groups}".format(groups=n)` é texto.
            return not (isinstance(pai.func, ast.Attribute) and pai.func.attr == "format")
        return (no.arg == "user" or no.arg.startswith("user__")) and _sobre_group_objects(pai.func)
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "getattr" and len(no.args) >= 2:
        nome = no.args[1]
        return isinstance(nome, ast.Constant) and nome.value in _ATRIBUTOS_DE_GRUPO
    return False


def _expressao_do_acesso(no: ast.AST, pais: dict[ast.AST, ast.AST]) -> ast.AST:
    """Sobe pela cadeia de atributos e chamadas: `user.groups` → `user.groups.filter(...).exists()`."""
    while True:
        pai = pais.get(no)
        if isinstance(pai, ast.Attribute | ast.Subscript) and pai.value is no:
            no = pai
        elif isinstance(pai, ast.Call) and (pai.func is no or no in pai.keywords):
            no = pai
        elif isinstance(pai, ast.keyword):
            no = pai
        else:
            return no


def _acessos_a_grupo(fonte: str) -> list[tuple[str, ast.AST, dict[ast.AST, ast.AST]]]:
    """(trecho normalizado, expressão, mapa de pais) de cada expressão do código que toca grupo, na ordem."""
    arvore = ast.parse(fonte)
    pais = {filho: pai for pai in ast.walk(arvore) for filho in ast.iter_child_nodes(pai)}
    expressoes: dict[int, ast.AST] = {}
    for no in ast.walk(arvore):
        if _eh_acesso_a_grupo(no, pais):
            expressao = _expressao_do_acesso(no, pais)
            expressoes[id(expressao)] = expressao
    ordem = sorted(expressoes.values(), key=lambda e: (getattr(e, "lineno", 0), getattr(e, "col_offset", 0)))
    return [(ast.unparse(expressao), expressao, pais) for expressao in ordem]


def _arquivos_de_producao() -> list[tuple[str, str]]:
    arquivos = []
    for arquivo in sorted((_RAIZ_DO_BACKEND / "apps").rglob("*.py")):
        relativo = arquivo.relative_to(_RAIZ_DO_BACKEND).as_posix()
        if "/tests/" not in relativo and "/migrations/" not in relativo:
            arquivos.append((relativo, arquivo.read_text(encoding="utf-8")))
    return arquivos


def _trechos_que_tocam_grupo() -> Counter[tuple[str, str]]:
    return Counter(
        (relativo, trecho)
        for relativo, fonte in _arquivos_de_producao()
        for trecho, _expressao, _pais in _acessos_a_grupo(fonte)
    )


def _trechos(fonte: str) -> list[str]:
    return [trecho for trecho, _expressao, _pais in _acessos_a_grupo(fonte)]


class TestDetectorDaCatraca:
    """O detector lê a árvore sintática, não a linha: o formato do Black, o apelido e o `getattr` não escapam."""

    def test_formato_do_black_em_varias_linhas(self):
        fonte = 've_tudo_pelo_grupo = Group.objects.filter(\n    user=user, name__in=["Controle", "DAT"]\n).exists()\n'
        assert _trechos(fonte) == ["Group.objects.filter(user=user, name__in=['Controle', 'DAT']).exists()"]

    def test_mesmo_trecho_em_uma_linha_ou_em_varias(self):
        uma = "x = user.groups.filter(name__in=NOMES).exists()\n"
        varias = "x = (\n    user.groups.filter(\n        name__in=NOMES,\n    )\n    .exists()\n)\n"
        assert _trechos(uma) == _trechos(varias) == ["user.groups.filter(name__in=NOMES).exists()"]

    def test_apelido_aparece_onde_nasce(self):
        fonte = "grupos = user.groups\nif grupos.filter(name='DAT').exists():\n    pass\n"
        assert _trechos(fonte) == ["user.groups"]

    def test_getattr(self):
        assert _trechos("g = getattr(user, 'groups')\nm = getattr(grupo, 'user_set')\n") == [
            "getattr(user, 'groups')",
            "getattr(grupo, 'user_set')",
        ]

    def test_membro_em_group_objects_e_lookup_por_grupo(self):
        fonte = (
            "Group.objects.filter(user__id=uid)\n"
            "Group.objects.all().exclude(user=u)\n"
            "Usuario.objects.filter(\n    groups__name='DAT'\n)\n"
            "Usuario.objects.filter(groups=g)\n"
        )
        assert _trechos(fonte) == [
            "Group.objects.filter(user__id=uid)",
            "Group.objects.all().exclude(user=u)",
            "Usuario.objects.filter(groups__name='DAT')",
            "Usuario.objects.filter(groups=g)",
        ]

    def test_o_que_nao_e_grupo_django_fica_de_fora(self):
        fonte = (
            '"""user.groups.filter(name="X") no texto."""\n'
            "# user.groups.filter(name='X') no comentário\n"
            "re.match(p, s).groups()\n"
            "'{groups}'.format(groups=n)\n"
            "Group.objects.filter(name='DAT')\n"
            "Projeto.objects.filter(user=u)\n"
        )
        assert _trechos(fonte) == []


def test_catraca_das_leituras_de_grupo():
    achadas = _trechos_que_tocam_grupo()
    esperadas = Counter((arquivo, trecho) for arquivo, trecho, _motivo in LEITURAS_DE_GRUPO)
    novas, sumidas = sorted(achadas - esperadas), sorted(esperadas - achadas)
    assert not novas and not sumidas, (
        "Acesso a grupo novo ou removido no código de produção. Se dá poder, passe por grupos_dao_poder() e "
        "marque PODER; se é exibição, auditoria ou escopo de dado, atualize LEITURAS_DE_GRUPO com o motivo.\n"
        f"novas: {novas}\nsumidas: {sumidas}"
    )


def _eh_portao(no: ast.AST) -> bool:
    return isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "grupos_dao_poder"


def _sob_o_portao(expressao: ast.AST, pais: dict[ast.AST, ast.AST]) -> bool:
    """A expressão está dentro de `if grupos_dao_poder(...):` ou à direita de `grupos_dao_poder(...) and`,
    sem sair da função."""
    no = expressao
    while no in pais:
        pai = pais[no]
        if isinstance(pai, ast.If) and no in pai.body and _eh_portao(pai.test):
            return True
        if isinstance(pai, ast.BoolOp) and isinstance(pai.op, ast.And):
            if _eh_portao(pai.values[0]) and no is not pai.values[0]:
                return True
        if isinstance(pai, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return False
        no = pai
    return False


def test_leituras_que_dao_poder_estao_sob_o_portao():
    """Tirar a leitura de poder do `if`/`and`, mesmo sem mudar o trecho, também fica vermelho."""
    de_poder = [(arquivo, trecho) for arquivo, trecho, motivo in LEITURAS_DE_GRUPO if motivo == PODER]
    assert len(de_poder) == 2  # capacidades (rbac_permissions) e telas de escopo (policies)
    for arquivo, trecho in de_poder:
        fonte = (_RAIZ_DO_BACKEND / arquivo).read_text(encoding="utf-8")
        achadas = [(expressao, pais) for t, expressao, pais in _acessos_a_grupo(fonte) if t == trecho]
        assert achadas, f"{arquivo}: a leitura de poder sumiu: {trecho}"
        for expressao, pais in achadas:
            linha = getattr(expressao, "lineno", "?")
            assert _sob_o_portao(expressao, pais), f"{arquivo}:{linha} lê grupo fora de grupos_dao_poder()"


def test_portao_conferido_pela_arvore():
    """Controle do teste acima: a mesma leitura com e sem o portão."""
    leitura = "user.groups.filter(name__in=s).exists()"
    com = f"def f(user, s, fonte):\n    if grupos_dao_poder(fonte) and {leitura}:\n        return True\n"
    sem = f"def f(user, s, fonte):\n    ok = {leitura}\n    if grupos_dao_poder(fonte) and ok:\n        return True\n"
    for fonte, esperado in ((com, True), (sem, False)):
        [(trecho, expressao, pais)] = _acessos_a_grupo(fonte)
        assert trecho == leitura
        assert _sob_o_portao(expressao, pais) is esperado


@pytest.mark.parametrize("recurso", RESOURCES, ids=lambda r: r.name)
def test_todos_os_grupos_sem_vinculo_igual_a_sem_grupo_na_api(recurso):
    """Canário no nível HTTP (K4): no corte, ter todos os grupos e nenhum vínculo dá a mesma resposta de não
    ter grupo nenhum em cada recurso de `RESOURCES` (a matriz viva: 13 rotas, não todas). O banco tem linhas
    de outra pessoa, de outra gerência (um deslocamento e uma solicitação), e nos GET que respondem 200 o
    corpo também é comparado: um escopo alargado pelo grupo aparece como linha a mais. Rota fora de
    `RESOURCES` não é coberta aqui; a catraca acima é quem pega a leitura de grupo nova no código."""
    for nome in ("Gestor Tecnologico", "Programador"):
        Group.objects.get_or_create(name=nome)
    outra_gerencia = GerenciaFactory()
    outra = UsuarioFactory()
    com_papel(outra, "FORMADOR", outra_gerencia)
    Deslocamento.objects.create(
        usuario=outra, origem="Fortaleza", destino="Sobral", start_date=date(2026, 5, 1), end_date=date(2026, 5, 3)
    )
    SolicitacaoFactory(usuario=outra, projeto=ProjetoFactory(gerencia=outra_gerencia))
    todos = _so_grupos(*SETOR_GROUPS, *FUNCAO_GROUPS, "Gestor Tecnologico", "Programador")
    nenhum = UsuarioFactory()
    respostas = []
    with LOTACAO:
        for pessoa in (todos, nenhum):
            client = APIClient()
            client.force_authenticate(user=pessoa)
            if recurso.method == "GET":
                respostas.append(client.get(recurso.full_url()))
            else:
                respostas.append(client.post(recurso.full_url(), data=recurso.body or {}, format="json"))
    com_grupos, sem_grupo = respostas
    assert (
        com_grupos.status_code == sem_grupo.status_code
    ), f"{recurso.name}: todos os grupos={com_grupos.status_code}, sem grupo={sem_grupo.status_code}"
    if recurso.method == "GET" and sem_grupo.status_code == 200:
        assert com_grupos.json() == sem_grupo.json(), f"{recurso.name}: o grupo mudou o que a pessoa vê"
