"""
PR-A1 DAT-Imports (2026-04-29): matriz consolidada para os 6 endpoints
de importação em massa que passam a ser DAT-only via
``HasPerm("import_spreadsheet")``.

Endpoints cobertos:
- POST /api/controle/import-compras/
- POST /api/controle/import-acoes/
- POST /api/disponibilidade/import-bloqueios/
- POST /api/deslocamentos/import/
- POST /api/solicitacoes/import/
- POST /api/produtos/import/

Matriz canônica: cada perfil testado contra os 6 endpoints simultaneamente
para evitar drift quando alguém tocar em apenas um deles. Falhas mostram o
endpoint culpado no parametrize id.

Endpoints fora deste PR (mantêm comportamento próprio):
- /api/dat/import-cadastros/  (já era DAT-only)
- /api/imports/bloqueios/     (ASQ-005 async, regime separado)
- /api/imports/colecoes/      (manage_admin_registries → DAT)
- /api/imports/vinculos/      (manage_admin_registries → DAT)
- /api/imports/usuarios/      (DAT)
- /api/imports/municipios/    (DAT)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false, reportUnusedFunction=false

from __future__ import annotations

import io
import itertools

from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


PR_A1_ENDPOINTS: list[str] = [
    "/api/controle/import-compras/",
    "/api/controle/import-acoes/",
    "/api/disponibilidade/import-bloqueios/",
    "/api/deslocamentos/import/",
    "/api/solicitacoes/import/",
    "/api/produtos/import/",
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


# ============================================================================
# DAT → 200/400 (não 403)
# ============================================================================


@pytest.mark.parametrize("endpoint", PR_A1_ENDPOINTS)
def test_dat_user_can_access_import_endpoint(endpoint: str):
    """Grupo DAT → autenticado e capability `import_spreadsheet` via seed.
    Não deve receber 403; demais status (200/400/500) dependem do payload."""
    user = _user_in_groups("DAT", username="dat_imports_user")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(endpoint + "?dry_run=true", {"file": _file()}, format="multipart")

    assert response.status_code != 403, f"DAT recebeu 403 em {endpoint}; deveria ter `import_spreadsheet`."


# ============================================================================
# Outros perfis → 403
# ============================================================================


PERSONAS_FORBIDDEN: list[tuple[str, tuple[str, ...]]] = [
    ("controle_puro", ("Controle",)),
    ("superintendencia", ("Superintendência",)),
    ("gerente", ("Gerente",)),
    ("coordenador", ("Coordenador",)),
    ("apoio", ("Apoio de Coordenação",)),
    ("formador", ("Formador",)),
    ("diretoria", ("Diretoria",)),
    ("controle_mais_gerente", ("Controle", "Gerente")),
]


@pytest.mark.parametrize("endpoint", PR_A1_ENDPOINTS)
@pytest.mark.parametrize("persona", PERSONAS_FORBIDDEN, ids=[p[0] for p in PERSONAS_FORBIDDEN])
def test_non_dat_personas_get_403(endpoint: str, persona: tuple[str, tuple[str, ...]]):
    """PR-A1 (D-1): apenas DAT (e superuser) podem importar em massa.
    Todos os demais perfis recebem 403, mesmo combinações com Gerente."""
    label, group_names = persona
    user = _user_in_groups(*group_names, username=f"{label}_pr_a1")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(endpoint + "?dry_run=true", {"file": _file()}, format="multipart")

    assert response.status_code == 403, (
        f"{label} ({group_names}) deveria receber 403 em {endpoint}, " f"recebeu {response.status_code}."
    )


# ============================================================================
# Anonymous → 401 ou 403
# ============================================================================


@pytest.mark.parametrize("endpoint", PR_A1_ENDPOINTS)
def test_anonymous_request_is_rejected(endpoint: str):
    """Sem autenticação: backend retorna 401 (DRF default) ou 403 (config local)."""
    client = APIClient()
    response = client.post(endpoint + "?dry_run=true", {"file": _file()}, format="multipart")
    assert response.status_code in (
        401,
        403,
    ), f"Anonymous deveria ter sido rejeitado em {endpoint}, recebeu {response.status_code}."


# ============================================================================
# Superuser → bypass
# ============================================================================


@pytest.mark.parametrize("endpoint", PR_A1_ENDPOINTS)
def test_superuser_bypasses_dat_only_gate(endpoint: str):
    """Superuser tem bypass via HasPerm; passa em todos os endpoints PR-A1."""
    cpf = str(next(_CPF_COUNTER)).zfill(11)
    user = UsuarioFactory(
        superuser=True,
        username=f"su_pr_a1_{cpf}",
        email=f"su_{cpf}@x.com",
        password="x",
        cpf=cpf,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(endpoint + "?dry_run=true", {"file": _file()}, format="multipart")

    assert response.status_code != 403, f"Superuser recebeu 403 em {endpoint}; bypass HasPerm deveria autorizar."
