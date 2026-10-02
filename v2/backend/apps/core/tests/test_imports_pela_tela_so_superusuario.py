"""
Importação pela tela é só do superusuário (decisão do dono, 02/10/2026).

Nenhum perfil importa planilha pela tela na liberação: as cargas passam por script, com ensaio.
Os 12 endpoints de upload exigem ``SuperuserOnly``; nenhuma capability (``import_spreadsheet``,
``manage_admin_registries``, ``run_daily_operations``) dá acesso. O command de terminal
``import_export_contract`` não passa por estes endpoints e não muda.

Substitui a matriz do PR-A1 DAT-Imports (2026-04-29), que fixava "DAT importa" em 6 deles.

Endpoints cobertos:
- POST /api/controle/import-compras/ e o alias /api/import-compras/
- POST /api/controle/import-acoes/
- POST /api/dat/import-cadastros/
- POST /api/disponibilidade/import-bloqueios/
- POST /api/deslocamentos/import/
- POST /api/solicitacoes/import/
- POST /api/usuarios/import/
- POST /api/produtos/import/
- POST /api/municipios/import/
- POST /api/colecoes/import/
- POST /api/equipe-gerencia/import/
- POST /api/imports/bloqueios/ (assíncrono, ASQ-005)

Cada perfil é testado contra todos os endpoints; a falha mostra o endpoint no id do parametrize.
A sentinela no fim cobra que view de upload nova entre aqui.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import io
import itertools

from django.urls import get_resolver
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario
from apps.core.permissions import SuperuserOnly
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


ENDPOINTS_DE_IMPORT: list[str] = [
    "/api/controle/import-compras/",
    "/api/import-compras/",
    "/api/controle/import-acoes/",
    "/api/dat/import-cadastros/",
    "/api/disponibilidade/import-bloqueios/",
    "/api/deslocamentos/import/",
    "/api/solicitacoes/import/",
    "/api/usuarios/import/",
    "/api/produtos/import/",
    "/api/municipios/import/",
    "/api/colecoes/import/",
    "/api/equipe-gerencia/import/",
    "/api/imports/bloqueios/",
]


# Atomic counter (memória `feedback_deterministic_unique_in_pytest.md`):
# evita colisão de CPF entre tests parametrizados, sem depender de hash().
_CPF_COUNTER = itertools.count(80000000000)


def _file(content: bytes = b"x", name: str = "f.csv") -> io.BytesIO:
    f = io.BytesIO(content)
    f.name = name
    return f


def _user_in_groups(*group_names: str, username: str = "u") -> Usuario:
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = UsuarioFactory(
        username=f"{username}_{cpf}",
        email=f"{username}_{cpf}@x.com",
        password="x",
        cpf=cpf,
    )
    for name in group_names:
        group = GroupFactory(name=name)
        user.groups.add(group)
    return user


def _post(user: Usuario | None, endpoint: str):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client.post(endpoint + "?dry_run=true", {"file": _file()}, format="multipart")


# ============================================================================
# Todo perfil que não é superusuário → 403 (inclusive o DAT, que antes importava)
# ============================================================================


PERSONAS_FORBIDDEN: list[tuple[str, tuple[str, ...]]] = [
    ("dat", ("DAT",)),
    ("controle_puro", ("Controle",)),
    ("superintendencia", ("Superintendência",)),
    ("gerente", ("Gerente",)),
    ("coordenador", ("Coordenador",)),
    ("apoio", ("Apoio de Coordenação",)),
    ("formador", ("Formador",)),
    ("diretoria", ("Diretoria",)),
    ("controle_mais_gerente", ("Controle", "Gerente")),
    ("dat_mais_controle", ("DAT", "Controle")),
]


@pytest.mark.parametrize("endpoint", ENDPOINTS_DE_IMPORT)
@pytest.mark.parametrize("persona", PERSONAS_FORBIDDEN, ids=[p[0] for p in PERSONAS_FORBIDDEN])
def test_quem_nao_e_superusuario_recebe_403(endpoint: str, persona: tuple[str, tuple[str, ...]]):
    """Nenhuma capability dá acesso: o DAT tem `import_spreadsheet` e `manage_admin_registries` e recebe 403."""
    label, group_names = persona
    user = _user_in_groups(*group_names, username=f"{label}_import")

    response = _post(user, endpoint)

    assert (
        response.status_code == 403
    ), f"{label} ({group_names}) deveria receber 403 em {endpoint}, recebeu {response.status_code}."


def test_o_dat_do_403_tem_as_capacidades_que_antes_importavam():
    """Controle do teste acima: o 403 do DAT não é falta de seed (o grupo tem as capabilities)."""
    from apps.core.rbac.helpers import get_user_functional_permissions

    capacidades = get_user_functional_permissions(_user_in_groups("DAT", username="dat_caps"))

    assert {"import_spreadsheet", "manage_admin_registries"} <= set(capacidades)


# ============================================================================
# Anonymous → 401 ou 403
# ============================================================================


@pytest.mark.parametrize("endpoint", ENDPOINTS_DE_IMPORT)
def test_anonymous_request_is_rejected(endpoint: str):
    """Sem autenticação: backend retorna 401 (DRF default) ou 403 (config local)."""
    response = _post(None, endpoint)

    assert response.status_code in (
        401,
        403,
    ), f"Anonymous deveria ter sido rejeitado em {endpoint}, recebeu {response.status_code}."


# ============================================================================
# Superusuário → passa
# ============================================================================


@pytest.mark.parametrize("endpoint", ENDPOINTS_DE_IMPORT)
def test_superusuario_passa(endpoint: str):
    """O superusuário passa pelo gate; os demais status (200/202/400) dependem do arquivo."""
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = UsuarioFactory(
        superuser=True,
        username=f"su_import_{cpf}",
        email=f"su_{cpf}@x.com",
        password="x",
        cpf=cpf,
    )

    response = _post(user, endpoint)

    assert response.status_code not in (401, 403), f"Superusuário recebeu {response.status_code} em {endpoint}."


# ============================================================================
# Sentinela: view de upload nova entra aqui, com o mesmo gate
# ============================================================================


def _views_de_upload() -> dict[str, type]:
    """As views do `/api/` que recebem arquivo (multipart-only) por POST, pela rota."""
    achadas: dict[str, type] = {}

    def percorrer(padroes, prefixo: str) -> None:
        for padrao in padroes:
            rota = prefixo + str(padrao.pattern)
            if hasattr(padrao, "url_patterns"):
                percorrer(padrao.url_patterns, rota)
                continue
            view = getattr(padrao.callback, "view_class", None)
            if view is None or not hasattr(view, "post"):
                continue
            if list(getattr(view, "parser_classes", [])) == [MultiPartParser] or "import" in rota:
                achadas["/" + rota.replace("api/v1/", "api/", 1)] = view

    percorrer(get_resolver().url_patterns, "")
    return achadas


def test_sentinela_toda_view_de_upload_de_planilha_exige_superusuario():
    views = _views_de_upload()

    assert sorted(views) == sorted(ENDPOINTS_DE_IMPORT), (
        "Endpoint de importação pela tela novo (ou removido): atualize ENDPOINTS_DE_IMPORT. "
        "Importação pela tela é só do superusuário (decisão do dono, 02/10/2026)."
    )
    for rota, view in views.items():
        assert list(view.permission_classes) == [IsAuthenticated, SuperuserOnly], rota
