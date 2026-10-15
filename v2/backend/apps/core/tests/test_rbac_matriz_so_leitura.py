"""
PR A da arquitetura de permissões, D4 (a) do ADR-020: a matriz Grupo×Capacidade muda só por PR.

- A API de grupos responde 400 quando `permissao_funcional_ids` difere do conjunto atual
  ("capacidades mudam por PR"). O mesmo conjunto, ou o campo ausente, segue aceito: a aba aberta
  com o bundle antigo manda `[]` ao criar e os ids atuais ao editar.
- O admin Django não altera `PermissaoFuncional`.
- `rbac_diff --auditar` (só leitura, sem dado pessoal) sai com exit 1 quando os pares
  (grupo, capacidade) do banco diferem dos do seed, ou quando há gerência com perfil ≠ PADRAO
  fora de `PERFIL_PERMITIDO`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import importlib
import re
from io import StringIO

from django.apps import apps as django_apps
from django.contrib.auth.models import Group
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

import pytest

from apps.core.admin_site import admin_site
from apps.core.models import Gerencia, PermissaoFuncional
from apps.core.services.rbac_snapshot import auditoria_de_matriz
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def _root() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    return client


def _ids(grupo: Group) -> set[int]:
    return set(grupo.permissoes_funcionais.values_list("id", flat=True))


def _auditar() -> str:
    out = StringIO()
    call_command("rbac_diff", "--auditar", stdout=out)
    return out.getvalue()


# =============================================================================
# API de grupos
# =============================================================================


def test_api_grupos_recusa_mudar_capacidades():
    grupo = Group.objects.get(name="Controle")
    antes = _ids(grupo)
    outra = PermissaoFuncional.objects.get(codename="approve_solicitation")
    root = _root()

    editar = root.patch(
        f"/api/grupos/{grupo.id}/", {"permissao_funcional_ids": sorted(antes | {outra.id})}, format="json"
    )
    criar = root.post(
        "/api/grupos/",
        {"name": "Grupo Novo Matriz", "group_type_input": "funcao", "permissao_funcional_ids": [outra.id]},
        format="json",
    )

    assert editar.status_code == 400, editar.content
    assert "capacidades mudam por PR" in editar.content.decode()
    assert _ids(grupo) == antes
    assert criar.status_code == 400, criar.content
    assert not Group.objects.filter(name="Grupo Novo Matriz").exists()


def test_api_grupos_aceita_mesmo_conjunto_e_ausencia():
    grupo = Group.objects.get(name="Controle")
    antes = _ids(grupo)
    root = _root()

    mesmo = root.patch(f"/api/grupos/{grupo.id}/", {"permissao_funcional_ids": sorted(antes)}, format="json")
    sem_campo = root.patch(f"/api/grupos/{grupo.id}/", {"name": "Controle"}, format="json")
    criar_vazio = root.post(
        "/api/grupos/",
        {"name": "Grupo Vazio Matriz", "group_type_input": "funcao", "permissao_funcional_ids": []},
        format="json",
    )

    assert mesmo.status_code == 200, mesmo.content
    assert sem_campo.status_code == 200, sem_campo.content
    assert criar_vazio.status_code == 201, criar_vazio.content
    assert _ids(grupo) == antes
    assert not Group.objects.get(name="Grupo Vazio Matriz").permissoes_funcionais.exists()


# =============================================================================
# Admin Django
# =============================================================================


def test_admin_permissaofuncional_sem_alteracao():
    request = RequestFactory().get("/admin/")
    request.user = UsuarioFactory(superuser=True)
    model_admin = admin_site._registry[PermissaoFuncional]
    perm = PermissaoFuncional.objects.get(codename="approve_solicitation")

    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_change_permission(request, perm) is False
    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_delete_permission(request, perm) is False
    assert model_admin.has_view_permission(request, perm) is True


# =============================================================================
# rbac_diff --auditar
# =============================================================================


def test_rbac_diff_auditar_exit0_quando_banco_igual_seed():
    Gerencia.objects.update_or_create(
        nome="GERENCIA DAT", defaults={"nome_setor": "DAT", "perfil": "ADMIN_OPERACIONAL"}
    )

    saida = _auditar()

    assert "rbac_diff --auditar: 0 divergência(s)" in saida


# Pares que o PR A pôs no seed (matriz medida em produção em 02/10) e que nenhuma migration até a
# 0120 grava. Num banco montado só por `migrate`, eles faltam.
_PARES_DO_PR_A = (
    ("Assistente Administrativo", "manage_purchases_and_materials"),
    ("Assistente Administrativo", "operate_preagenda"),
    ("Assistente Administrativo", "run_daily_operations"),
    ("DAT", "view_map_metrics"),
)


@pytest.mark.migrations
def test_migration_0121_leva_o_banco_das_migrations_ate_o_seed():
    """D4: a matriz muda por PR, com a migration de dados. Sem a 0121, `migrate` + `--auditar` = exit 1.

    PR 8: a 0125 tira as capacidades dos grupos de função, então os três pares do Assistente
    Administrativo que a 0121 grava saem de novo. A cadeia 0121 → 0125 chega ao seed.
    """
    migracao = importlib.import_module("apps.core.migrations.0121_matriz_assistente_administrativo_e_dat")
    pr8 = importlib.import_module("apps.core.migrations.0125_funcoes_sem_capacidade")
    for grupo, codename in _PARES_DO_PR_A:
        Group.objects.get(name=grupo).permissoes_funcionais.remove(PermissaoFuncional.objects.get(codename=codename))
    assert auditoria_de_matriz()["so_no_seed"] == [["DAT", "view_map_metrics"]]

    migracao.forwards(django_apps, None)
    migracao.forwards(django_apps, None)  # reaplicar não muda nada
    assert auditoria_de_matriz()["so_no_banco"] == sorted(
        [list(par) for par in _PARES_DO_PR_A if par[0] == "Assistente Administrativo"]
    )

    pr8.forwards(django_apps, None)
    assert "rbac_diff --auditar: 0 divergência(s)" in _auditar()


def test_rbac_diff_auditar_exit1_grupo_com_capacidade_a_mais():
    Group.objects.get(name="Formador").permissoes_funcionais.add(
        PermissaoFuncional.objects.get(codename="approve_solicitation")
    )

    with pytest.raises(CommandError, match="divergência"):
        _auditar()


def test_rbac_diff_auditar_exit1_grupo_com_capacidade_a_menos():
    Group.objects.get(name="DAT").permissoes_funcionais.remove(
        PermissaoFuncional.objects.get(codename="manage_admin_registries")
    )

    with pytest.raises(CommandError, match="divergência"):
        _auditar()


def test_rbac_diff_auditar_exit1_perfil_fora_da_lista():
    Gerencia.objects.create(nome="GERENCIA FLUIR AUDIT", nome_setor="Fluir", perfil="ADMIN_OPERACIONAL")

    with pytest.raises(CommandError, match="divergência"):
        _auditar()


def test_rbac_diff_auditar_exit1_perfil_trocado_na_gerencia_permitida():
    Gerencia.objects.update_or_create(nome="GERENCIA DAT", defaults={"nome_setor": "DAT", "perfil": "DIRETORIA"})

    with pytest.raises(CommandError, match="divergência"):
        _auditar()


def test_rbac_diff_auditar_nao_grava_e_sem_dado_pessoal(capsys):
    u = UsuarioFactory(
        username="98765432100",
        cpf="98765432100",
        email="pessoa.secreta@example.com",
        first_name="Fulana",
        last_name="Sigilosa",
        groups=["Formador"],
    )
    Group.objects.get(name="Formador").permissoes_funcionais.add(
        PermissaoFuncional.objects.get(codename="approve_solicitation")
    )
    Gerencia.objects.create(nome="GERENCIA AUDIT PII", nome_setor="Audit", perfil="CONTROLE")
    out = StringIO()

    with CaptureQueriesContext(connection) as ctx, pytest.raises(CommandError) as erro:
        call_command("rbac_diff", "--auditar", stdout=out)

    escritas = [q["sql"] for q in ctx.captured_queries if re.match(r"\s*(INSERT|UPDATE|DELETE)\b", q["sql"], re.I)]
    assert escritas == []
    tudo = out.getvalue() + str(erro.value) + "\n".join(capsys.readouterr())
    assert "Formador" in tudo and "approve_solicitation" in tudo
    assert "GERENCIA AUDIT PII" in tudo
    for dado in ("98765432100", "pessoa.secreta", "Fulana", "Sigilosa", f"u{u.id}"):
        assert dado not in tudo, dado
