"""Troca obrigatória de senha no primeiro acesso (decisão do dono, 02/10/2026).

Enquanto `Usuario.deve_trocar_senha` está ligado, a API só aceita ler o próprio `/api/me/`,
buscar o CSRF, trocar a senha, sair e entrar de novo. O ponto ÚNICO de imposição é o
`TrocaDeSenhaObrigatoriaMiddleware`, que NEGA POR PADRÃO: rota nova nasce bloqueada.

ATENÇÃO: estes testes usam `force_login` (sessão de verdade). O `force_authenticate` do DRF
não passa pelo `AuthenticationMiddleware` — o `request.user` do Django fica anônimo e o
middleware não veria a marca (o teste passaria ou falharia pelo motivo errado).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportPrivateUsage=false

from __future__ import annotations

from typing import Any

from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import NoReverseMatch, ResolverMatch, URLPattern, URLResolver, get_resolver, reverse
from rest_framework.test import APIClient

import pytest

from apps.core.middleware import ROTAS_LIBERADAS_NA_TROCA_DE_SENHA, TrocaDeSenhaObrigatoriaMiddleware
from apps.core.models import AuditLog
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

CODIGO = "PASSWORD_CHANGE_REQUIRED"
SENHA_RECEBIDA = "Provisoria#2026"
METODOS = ("get", "post", "put", "patch", "delete", "head", "options")


def _logado(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def _marcado(**kwargs: Any):
    return UsuarioFactory(deve_trocar_senha=True, password=SENHA_RECEBIDA, **kwargs)


def _codigo(resp) -> str | None:
    if not resp["Content-Type"].startswith("application/json") or not resp.content:
        return None
    data = resp.json()
    return data.get("code") if isinstance(data, dict) else None


def _bloqueada(resp, *, sem_corpo: bool = False) -> bool:
    if sem_corpo:
        # HEAD: o Django descarta o corpo; sobra o status e o tipo da resposta do middleware.
        return resp.status_code == 403 and resp["Content-Type"] == "application/json" and not resp.content
    return resp.status_code == 403 and _codigo(resp) == CODIGO


# Um caso por grupo de rota do sistema: (rótulo, método, caminho).
ROTAS_DE_NEGOCIO = [
    ("lista de solicitações", "get", "/api/solicitacoes/"),
    ("lista de municípios", "get", "/api/municipios/"),
    ("criar solicitação", "post", "/api/solicitacoes/"),
    ("aprovar solicitação", "post", "/api/solicitacoes/1/approve/"),
    ("aprovar em lote", "post", "/api/solicitacoes/batch-approve/"),
    ("administração de usuários", "get", "/api/usuarios-admin/"),
    ("administração de grupos", "get", "/api/grupos/"),
    ("importação de usuários", "post", "/api/usuarios/import/"),
    ("importações em andamento", "get", "/api/imports/"),
    ("painel inicial", "get", "/api/stats/home/"),
    ("painel geral", "get", "/api/dashboard/overview/"),
    ("painel da agenda Google", "get", "/api/gcal/dashboard/metrics/"),
    ("permissões da pessoa", "get", "/api/me/policies/"),
    ("exportar os próprios dados", "get", "/api/me/export/"),
    ("corrigir o próprio contato", "patch", "/api/me/"),
    ("renovar a sessão", "post", "/api/auth/ping/"),
    ("apelido antigo /api/v1/ de lista", "get", "/api/v1/solicitacoes/"),
    ("apelido antigo /api/v1/ do /me", "get", "/api/v1/me/"),
    ("apelido antigo /api/v1/ da troca", "post", "/api/v1/me/change-password/"),
    ("Django Admin", "get", "/admin/"),
    ("entrada do Django Admin", "post", "/admin/login/"),
]


@pytest.mark.parametrize(("rotulo", "metodo", "caminho"), ROTAS_DE_NEGOCIO, ids=[r[0] for r in ROTAS_DE_NEGOCIO])
def test_marca_ligada_bloqueia_cada_grupo_de_rota(rotulo, metodo, caminho):
    # Superusuário: nenhuma regra de permissão explicaria o 403 — só a marca.
    client = _logado(_marcado(superuser=True))

    resp = getattr(client, metodo)(caminho, {}, format="json")

    assert resp.status_code == 403, rotulo
    assert resp.json() == {"detail": "Defina uma senha própria para continuar.", "code": CODIGO}


def test_marca_ligada_libera_o_minimo():
    user = _marcado()
    client = _logado(user)

    me = client.get("/api/me/")
    assert me.status_code == 200
    assert me.json()["deve_trocar_senha"] is True
    assert client.get("/api/csrf/").status_code == 200
    assert client.post("/api/auth/logout/").status_code == 200


def test_marca_ligada_libera_a_troca_de_senha():
    client = _logado(_marcado())

    resp = client.post(
        "/api/me/change-password/",
        {"old_password": SENHA_RECEBIDA, "new_password": "Girassol#Azul77"},
        format="json",
    )

    assert resp.status_code == 200


def test_marca_desligada_nao_bloqueia_nada():
    client = _logado(UsuarioFactory(superuser=True))

    for _rotulo, metodo, caminho in ROTAS_DE_NEGOCIO:
        resp = getattr(client, metodo)(caminho, {}, format="json")
        assert not _bloqueada(resp), caminho
    assert client.get("/api/solicitacoes/").status_code == 200


def test_anonimo_nao_e_afetado():
    client = APIClient()

    resp = client.get("/api/solicitacoes/")

    assert resp.status_code in (401, 403)
    assert resp.json()["code"] == "NOT_AUTHENTICATED"
    assert client.get("/api/readyz/").status_code == 200


def _rotas_registradas(resolver: URLResolver, namespaces: tuple[str, ...] = ()) -> list[tuple[str, URLPattern]]:
    """Todas as rotas do projeto, com o nome completo (`namespace:nome`) que o Django resolve."""
    rotas: list[tuple[str, URLPattern]] = []
    for item in resolver.url_patterns:
        if isinstance(item, URLResolver):
            ns = (*namespaces, item.namespace) if item.namespace else namespaces
            rotas.extend(_rotas_registradas(item, ns))
        else:
            nome = item.name or item.lookup_str
            rotas.append((":".join((*namespaces, nome)), item))
    return rotas


def _caminho_de(view_name: str, pattern: URLPattern) -> str | None:
    kwargs = {k: ("json" if k == "format" else "1") for k in pattern.pattern.regex.groupindex}
    try:
        return reverse(view_name, kwargs=kwargs)
    except NoReverseMatch:
        return None


def test_nega_por_padrao_em_todas_as_rotas_registradas():
    """Percorre TODAS as rotas: com a marca ligada, só a lista fechada passa.

    Rota com endereço montável é exercitada por HTTP (cadeia inteira de middlewares). A que
    não dá para montar (padrão sem nome ou com grupo sem nome) é entregue direto ao middleware
    com o `resolver_match` que o Django daria — nenhuma rota fica de fora da prova.
    """
    user = _marcado(superuser=True)
    client = _logado(user)
    rotas = _rotas_registradas(get_resolver())
    assert len(rotas) > 200, "o resolver deveria listar as rotas da API e do Admin"

    middleware = TrocaDeSenhaObrigatoriaMiddleware(lambda request: HttpResponse())
    passaram: set[tuple[str, str]] = set()
    por_http = 0

    for view_name, pattern in rotas:
        caminho = _caminho_de(view_name, pattern)
        for metodo in METODOS:
            chave = (view_name, metodo.upper())
            if caminho is None:
                request = getattr(RequestFactory(), metodo)("/rota-sem-endereco-montavel/")
                request.user = user
                request.resolver_match = ResolverMatch(
                    pattern.callback, (), {}, url_name=pattern.name, namespaces=view_name.split(":")[:-1]
                )
                if request.resolver_match.view_name != view_name:
                    # Padrão sem nome: o Django usa o caminho pontilhado da função.
                    request.resolver_match.view_name = view_name
                barrada = middleware.process_view(request, pattern.callback, (), {})
                if barrada is None:
                    passaram.add(chave)
                continue
            if chave in ROTAS_LIBERADAS_NA_TROCA_DE_SENHA:
                # Sair encerra a sessão: cada rota liberada usa uma sessão nova.
                resp = getattr(_logado(user), metodo)(caminho, {}, format="json")
            else:
                resp = getattr(client, metodo)(caminho, {}, format="json")
            por_http += 1
            if not _bloqueada(resp, sem_corpo=metodo == "head"):
                passaram.add(chave)

    assert por_http > 1000, "a maior parte das rotas tem de ser provada por HTTP"
    assert passaram == set(ROTAS_LIBERADAS_NA_TROCA_DE_SENHA)


def test_lista_liberada_e_exatamente_me_csrf_troca_sair_e_entrar():
    assert ROTAS_LIBERADAS_NA_TROCA_DE_SENHA == frozenset(
        {
            ("core:current-user", "GET"),
            ("core:csrf-token", "GET"),
            ("core:me-change-password", "POST"),
            ("core:auth-logout", "POST"),
            ("core:auth-login", "POST"),
        }
    )


# ---------------------------------------------------------------------------
# Entrar de novo com o cookie de uma conta marcada (navegador que ficou com a sessão antiga)
# ---------------------------------------------------------------------------

LOGIN = "/api/auth/login/"


def test_cookie_de_conta_marcada_nao_barra_a_entrada_com_outra_conta():
    client = _logado(_marcado())
    outra = UsuarioFactory(username="outra.conta", password=SENHA_NOVA)

    resp = client.post(LOGIN, {"username": "outra.conta", "password": SENHA_NOVA}, format="json")

    assert resp.status_code == 200
    me = client.get("/api/me/")
    assert me.status_code == 200
    assert me.json()["id"] == outra.pk
    assert me.json()["deve_trocar_senha"] is False
    assert client.get("/api/me/policies/").status_code == 200


def test_entrar_de_novo_com_a_propria_conta_marcada_nao_libera_nada():
    user = _marcado(username="conta.marcada")
    client = _logado(user)

    resp = client.post(LOGIN, {"username": "conta.marcada", "password": SENHA_RECEBIDA}, format="json")

    assert resp.status_code == 200
    assert client.get("/api/me/").json()["deve_trocar_senha"] is True
    for _rotulo, metodo, caminho in ROTAS_DE_NEGOCIO:
        assert _bloqueada(getattr(client, metodo)(caminho, {}, format="json")), caminho


# ---------------------------------------------------------------------------
# A troca: desliga a marca, mantém a sessão e fica na trilha
# ---------------------------------------------------------------------------

TROCA = "/api/me/change-password/"
SENHA_NOVA = "Girassol#Azul77"


def test_troca_desliga_a_marca_mantem_a_sessao_e_audita(settings):
    user = _marcado(username="52998224725", cpf="52998224725")
    client = APIClient()
    entrada = client.post("/api/auth/login/", {"username": "52998224725", "password": SENHA_RECEBIDA}, format="json")
    assert entrada.status_code == 200
    sessao_antes = client.cookies[settings.SESSION_COOKIE_NAME].value
    assert _bloqueada(client.get("/api/solicitacoes/"))

    resp = client.post(TROCA, {"old_password": SENHA_RECEBIDA, "new_password": SENHA_NOVA}, format="json")

    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.deve_trocar_senha is False
    assert user.check_password(SENHA_NOVA)
    # A chave da sessão é renovada e a pessoa continua dentro, sem novo login.
    assert client.cookies[settings.SESSION_COOKIE_NAME].value != sessao_antes
    depois = client.get("/api/me/")
    assert depois.status_code == 200
    assert depois.json()["deve_trocar_senha"] is False
    assert client.get("/api/me/policies/").status_code == 200

    audit = AuditLog.objects.filter(usuario=user, action=AuditLog.Action.CHANGE_PASSWORD).get()
    assert audit.details["primeiro_acesso"] is True
    assert SENHA_NOVA not in str(audit.details)
    assert SENHA_RECEBIDA not in str(audit.details)


def test_nova_igual_a_recebida_e_recusada_e_a_marca_continua():
    user = _marcado()
    client = _logado(user)

    resp = client.post(TROCA, {"old_password": SENHA_RECEBIDA, "new_password": SENHA_RECEBIDA}, format="json")

    assert resp.status_code == 400
    assert "new_password" in resp.json()["errors"]
    user.refresh_from_db()
    assert user.deve_trocar_senha is True
    assert _bloqueada(client.get("/api/solicitacoes/"))


def test_nao_da_para_voltar_a_senha_recebida_depois_da_troca():
    """Senha padrão é a mesma para todos: voltar a ela deixaria a conta aberta e sem a marca."""
    user = _marcado()
    client = _logado(user)
    assert (
        client.post(TROCA, {"old_password": SENHA_RECEBIDA, "new_password": SENHA_NOVA}, format="json").status_code
        == 200
    )

    volta = client.post(TROCA, {"old_password": SENHA_NOVA, "new_password": SENHA_RECEBIDA}, format="json")

    assert volta.status_code == 400
    assert "new_password" in volta.json()["errors"]
    user.refresh_from_db()
    assert user.check_password(SENHA_NOVA)
    assert user.deve_trocar_senha is False

    # Nem dando a volta por uma terceira senha: a recebida fica lembrada (só o hash).
    outra = "Mandacaru#Verde88"
    assert client.post(TROCA, {"old_password": SENHA_NOVA, "new_password": outra}, format="json").status_code == 200
    de_novo = client.post(TROCA, {"old_password": outra, "new_password": SENHA_RECEBIDA}, format="json")
    assert de_novo.status_code == 400
    user.refresh_from_db()
    assert user.check_password(outra)
    assert SENHA_RECEBIDA not in user.senha_recebida_hash


def test_troca_comum_sem_a_marca_nao_guarda_senha_recebida():
    user = UsuarioFactory(password=SENHA_RECEBIDA)
    client = _logado(user)

    assert (
        client.post(TROCA, {"old_password": SENHA_RECEBIDA, "new_password": SENHA_NOVA}, format="json").status_code
        == 200
    )
    volta = client.post(TROCA, {"old_password": SENHA_NOVA, "new_password": SENHA_RECEBIDA}, format="json")

    assert volta.status_code == 200
    user.refresh_from_db()
    assert user.senha_recebida_hash == ""


def test_senha_fraca_nao_desliga_a_marca():
    user = _marcado()
    client = _logado(user)

    resp = client.post(TROCA, {"old_password": SENHA_RECEBIDA, "new_password": "12345678"}, format="json")

    assert resp.status_code == 400
    assert "new_password" in resp.json()["errors"]
    user.refresh_from_db()
    assert user.deve_trocar_senha is True
    assert user.check_password(SENHA_RECEBIDA)


@pytest.mark.parametrize(
    ("parecida_com", "senha_nova"),
    [
        ("nome", "marcolina77"),
        ("sobrenome", "Albuquerque#1"),
        ("e-mail", "marcolina.teste9"),
        ("CPF", "52998224725ab"),
    ],
)
def test_senha_parecida_com_os_dados_da_pessoa_e_recusada(parecida_com, senha_nova):
    """A tela promete a regra de semelhança com nome, CPF e e-mail: o servidor cumpre."""
    user = _marcado(
        username="conta.ficticia",  # diferente do CPF: prova que o CPF entra por conta própria
        cpf="52998224725",
        first_name="Marcolina",
        last_name="Albuquerque",
        email="marcolina.teste@example.invalid",
    )
    client = _logado(user)

    resp = client.post(TROCA, {"old_password": SENHA_RECEBIDA, "new_password": senha_nova}, format="json")

    assert resp.status_code == 400, parecida_com
    assert "new_password" in resp.json()["errors"]
    user.refresh_from_db()
    assert user.deve_trocar_senha is True
    assert user.check_password(SENHA_RECEBIDA)


def test_marca_nao_sai_por_escrita_direta_no_me():
    user = _marcado()
    client = _logado(user)

    resp = client.patch("/api/me/", {"deve_trocar_senha": False, "telefone": "85900000000"}, format="json")

    assert _bloqueada(resp)
    user.refresh_from_db()
    assert user.deve_trocar_senha is True


def test_pessoa_sem_a_marca_nao_consegue_ligar_pelo_me():
    user = UsuarioFactory()
    client = _logado(user)

    resp = client.patch("/api/me/", {"deve_trocar_senha": True, "telefone": "85900000000"}, format="json")

    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.deve_trocar_senha is False
