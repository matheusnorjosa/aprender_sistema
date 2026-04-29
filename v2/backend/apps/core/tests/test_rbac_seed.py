"""
Testes para comando seed_rbac (PR 12/N).

Cobertura:
- Criação idempotente dos 5 grupos
- Atribuição correta de permissões model-level
- Endpoints críticos 200/403 conforme papel

Comando testado:
- python manage.py seed_rbac
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import Municipio, PermissaoFuncional, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def run_seed_rbac():
    """Executa seed_rbac antes de cada teste."""
    call_command("seed_rbac")


@pytest.fixture
def dados_basicos():
    """Criar dados básicos para os testes."""
    # Municípios
    mun_ce = Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400")

    # Projetos
    proj1 = Projeto.objects.create(nome="Alfabetização", codigo="P001")

    # Tipos de evento
    tipo1 = TipoEvento.objects.create(nome="Formação Inicial")

    return {
        "municipio": mun_ce,
        "projeto": proj1,
        "tipo": tipo1,
    }


# ============================================================================
# TESTES DE CRIAÇÃO IDEMPOTENTE DE GRUPOS
# ============================================================================


def test_seed_rbac_creates_all_groups(run_seed_rbac):
    """seed_rbac cria todos os grupos esperados."""
    expected_groups = [
        "DAT",
        "Controle",
        "Superintendência",
        "Coordenador",
        "Formador",
        "Apoio de Coordenação",
        "Diretoria",
    ]

    for group_name in expected_groups:
        assert Group.objects.filter(name=group_name).exists(), f"Grupo '{group_name}' não foi criado"


def test_seed_rbac_is_idempotent(run_seed_rbac):
    """seed_rbac pode ser executado múltiplas vezes sem duplicar grupos."""
    # Primeira execução já feita pelo fixture

    # Contagem inicial
    initial_count = Group.objects.count()

    # Segunda execução
    call_command("seed_rbac")

    # Contagem deve ser igual
    assert Group.objects.count() == initial_count, "seed_rbac não é idempotente (duplicou grupos)"


def test_seed_rbac_assigns_permissions_to_dat(run_seed_rbac):
    """Grupo DAT recebe permissões de admin completo."""
    dat = Group.objects.get(name="DAT")
    perms = dat.permissions.all()

    # DAT deve ter permissões em Usuario, Municipio, Projeto, Compra, AuditLog, Solicitacao
    perm_codenames = [p.codename for p in perms]

    # Usuario (CRUD)
    assert "add_usuario" in perm_codenames
    assert "change_usuario" in perm_codenames
    assert "delete_usuario" in perm_codenames
    assert "view_usuario" in perm_codenames

    # Municipio (CRUD)
    assert "add_municipio" in perm_codenames
    assert "change_municipio" in perm_codenames
    assert "delete_municipio" in perm_codenames
    assert "view_municipio" in perm_codenames

    # Solicitacao (view + add para Nova Solicitação)
    assert "view_solicitacao" in perm_codenames
    assert "add_solicitacao" in perm_codenames


def test_seed_rbac_assigns_permissions_to_controle(run_seed_rbac):
    """Grupo Controle recebe permissões de import e pré-agenda."""
    controle = Group.objects.get(name="Controle")
    perms = controle.permissions.all()

    perm_codenames = [p.codename for p in perms]

    # Read em admin models
    assert "view_municipio" in perm_codenames
    assert "view_projeto" in perm_codenames
    assert "view_compra" in perm_codenames

    # Import Compra
    assert "add_compra" in perm_codenames

    # AvailabilityBlock CRUD
    assert "add_availabilityblock" in perm_codenames
    assert "change_availabilityblock" in perm_codenames
    assert "delete_availabilityblock" in perm_codenames
    assert "view_availabilityblock" in perm_codenames


def test_seed_rbac_assigns_permissions_to_superintendencia(run_seed_rbac):
    """Grupo Superintendência recebe permissões de aprovar/reprovar."""
    super_group = Group.objects.get(name="Superintendência")
    perms = super_group.permissions.all()

    perm_codenames = [p.codename for p in perms]

    # Solicitacao (view + change para aprovar/reprovar)
    assert "view_solicitacao" in perm_codenames
    assert "change_solicitacao" in perm_codenames

    # Read em models de referência
    assert "view_usuario" in perm_codenames
    assert "view_municipio" in perm_codenames
    assert "view_projeto" in perm_codenames


def test_seed_rbac_assigns_permissions_to_coordenador(run_seed_rbac):
    """Grupo Coordenador recebe permissões de nova solicitação."""
    coord = Group.objects.get(name="Coordenador")
    perms = coord.permissions.all()

    perm_codenames = [p.codename for p in perms]

    # Solicitacao (add + view)
    assert "add_solicitacao" in perm_codenames
    assert "view_solicitacao" in perm_codenames

    # Read em models de referência
    assert "view_municipio" in perm_codenames
    assert "view_projeto" in perm_codenames

    # NÃO deve ter change (aprovar/reprovar)
    assert "change_solicitacao" not in perm_codenames


def test_seed_rbac_assigns_permissions_to_formador(run_seed_rbac):
    """Grupo Formador recebe permissões de bloqueio de agenda."""
    formador = Group.objects.get(name="Formador")
    perms = formador.permissions.all()

    perm_codenames = [p.codename for p in perms]

    # AvailabilityBlock CRUD
    assert "add_availabilityblock" in perm_codenames
    assert "change_availabilityblock" in perm_codenames
    assert "delete_availabilityblock" in perm_codenames
    assert "view_availabilityblock" in perm_codenames

    # Solicitacao (read onde é formador)
    assert "view_solicitacao" in perm_codenames


# ============================================================================
# TESTES DE ENDPOINTS CRÍTICOS (RBAC ENFORCEMENT)
# ============================================================================


def test_endpoint_municipios_dat_allowed(run_seed_rbac):
    """Issue #1222 (Epic 1): DAT acessa /api/municipios/ via `manage_admin_registries`
    (cadastro admin DAT puro). `seed_rbac` cria grupo DAT mas não atribui
    funcperms por default; explicitamente atribui aqui pra simular estado realista."""
    user = Usuario.objects.create_user(username="dat1", email="dat@x.com", password="x", cpf="11111111111")
    dat = Group.objects.get(name="DAT")
    PermissaoFuncional.objects.get(codename="manage_admin_registries").groups.add(dat)
    user.groups.add(dat)

    client = APIClient()
    client.force_authenticate(user=user)

    # GET (list)
    url = reverse("core:municipio-list")
    res = client.get(url)
    assert res.status_code == 200, f"DAT deve ter acesso GET /api/municipios/: {res.data}"


def test_endpoint_municipios_coordenador_forbidden(run_seed_rbac):
    """Coordenador NÃO tem acesso a /api/municipios/ (endpoint protegido por HasPerm("manage_purchases_and_materials"))."""
    user = Usuario.objects.create_user(username="coord1", email="coord@x.com", password="x", cpf="22222222222")
    coord = Group.objects.get(name="Coordenador")
    user.groups.add(coord)

    client = APIClient()
    client.force_authenticate(user=user)

    # GET (list) - MunicipioViewSet usa HasPerm("manage_purchases_and_materials") permission class
    url = reverse("core:municipio-list")
    res = client.get(url)
    # Coordenador NÃO deve ter acesso (403 esperado)
    assert res.status_code == 403, f"Coordenador não deve ter acesso a /api/municipios/: {res.data}"


def test_endpoint_solicitacoes_list_requires_authentication(run_seed_rbac):
    """Endpoints de solicitações exigem autenticação."""
    client = APIClient()

    # Tentar listar solicitações sem autenticação (403 esperado)
    url = reverse("core:solicitacao-list")
    res = client.get(url)

    assert res.status_code == 403, "Endpoints de solicitações devem requerer autenticação"


def test_endpoint_import_compras_dat_allowed(run_seed_rbac):
    """PR-A1 DAT-Imports (2026-04-29): DAT tem acesso ao endpoint de import compras.

    Nota: `seed_rbac` invoca `seed_functional_permissions(assign_default_groups=False)`,
    portanto os vínculos cap↔grupo precisam ser explicitamente reatribuídos no
    teste (mesmo padrão do test obsoleto `*_controle_allowed`).
    """
    user = Usuario.objects.create_user(username="dat1", email="dat@x.com", password="x", cpf="66666666666")
    dat = Group.objects.get(name="DAT")
    PermissaoFuncional.objects.get(codename="import_spreadsheet").groups.add(dat)
    user.groups.add(dat)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:import-compras")
    res = client.post(url, {})

    # 400 (dados inválidos) ou 200, mas NÃO 403
    assert res.status_code != 403, f"DAT deve ter acesso POST {url}: {res.status_code}"


def test_endpoint_import_compras_controle_forbidden(run_seed_rbac):
    """PR-A1 DAT-Imports (2026-04-29): Controle perde import em massa de compras.

    Mesmo que Controle receba via seed_rbac as caps `run_daily_operations` e
    `manage_purchases_and_materials`, o gate atual é `import_spreadsheet`
    (DAT-only) — Controle continua 403.
    """
    user = Usuario.objects.create_user(username="controle1", email="controle@x.com", password="x", cpf="55555555555")
    controle = Group.objects.get(name="Controle")
    # Reatribuir caps que Controle teria por seed em produção (já que
    # seed_rbac.py usa assign_default_groups=False).
    PermissaoFuncional.objects.get(codename="run_daily_operations").groups.add(controle)
    PermissaoFuncional.objects.get(codename="manage_purchases_and_materials").groups.add(controle)
    user.groups.add(controle)

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:import-compras")
    res = client.post(url, {})

    assert res.status_code == 403, f"Controle deve receber 403 em POST {url}: {res.status_code}"


def test_endpoint_import_compras_coordenador_forbidden(run_seed_rbac):
    """Coordenador NÃO tem acesso ao endpoint de import compras."""
    user = Usuario.objects.create_user(username="coord1", email="coord@x.com", password="x", cpf="77777777777")
    coord = Group.objects.get(name="Coordenador")
    user.groups.add(coord)

    client = APIClient()
    client.force_authenticate(user=user)

    # POST /api/import/compras/
    url = reverse("core:import-compras")
    res = client.post(url, {})

    # 403 esperado
    assert res.status_code == 403, "Coordenador não deve ter acesso a import compras"


def test_superuser_bypasses_all_permissions(run_seed_rbac):
    """Superuser sempre tem acesso, independente de grupos."""
    user = Usuario.objects.create_superuser(username="admin", email="admin@x.com", password="x", cpf="99999999999")

    client = APIClient()
    client.force_authenticate(user=user)

    # GET /api/municipios/
    url = reverse("core:municipio-list")
    res = client.get(url)
    assert res.status_code == 200, "Superuser deve ter acesso a todos endpoints"

    # GET /api/audit-logs/
    url = reverse("core:audit-log-list")
    res = client.get(url)
    assert res.status_code == 200, "Superuser deve ter acesso a audit logs"


# ============================================================================
# TESTES DE EDGE CASES
# ============================================================================


def test_seed_rbac_does_not_create_users(run_seed_rbac):
    """seed_rbac não deve criar usuários, apenas grupos."""
    # Contar usuários antes
    initial_user_count = Usuario.objects.count()

    # Executar seed novamente
    call_command("seed_rbac")

    # Contar usuários depois
    final_user_count = Usuario.objects.count()

    assert final_user_count == initial_user_count, "seed_rbac não deve criar usuários"


def test_seed_rbac_verbose_flag():
    """seed_rbac --verbose executa sem erros."""
    # Apenas garantir que não lança exceção
    call_command("seed_rbac", "--verbose")
