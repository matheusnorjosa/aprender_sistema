"""
Escrita em `/api/gerencias/` só com `manage_admin_registries` (decisão do dono, 19/10/2026).

Antes a escrita pedia `manage_purchases_and_materials`, que o pacote CONTROLE também tem: o Controle
criava, editava e excluía gerência pela API, embora a tela /dat/admin/gerencias seja só do DAT. Agora
a API pede a mesma capacidade da tela (pacote ADMIN_OPERACIONAL). A leitura não muda.
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import itertools

from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Usuario
from apps.core.rbac import user_has_any_perm
from apps.core.tests.factories import UsuarioFactory, com_pacote_do_controle, com_pacote_do_dat, com_papel

pytestmark = pytest.mark.django_db

_SEQ = itertools.count(1)


def _gerencia() -> Gerencia:
    n = next(_SEQ)
    return Gerencia.objects.create(nome=f"GERENCIA ESCRITA {n}", nome_setor=f"Setor Escrita {n}")


def _cliente(usuario: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


def _controle() -> Usuario:
    user = UsuarioFactory()
    com_pacote_do_controle(user)
    # Sem isto o teste passaria por falta de poder, não pela regra nova.
    assert user_has_any_perm(user, "manage_purchases_and_materials")
    assert not user_has_any_perm(user, "manage_admin_registries")
    return user


def _dat() -> Usuario:
    user = UsuarioFactory()
    com_pacote_do_dat(user)
    assert user_has_any_perm(user, "manage_admin_registries")
    return user


def _escrever(client: APIClient, metodo: str, gerencia: Gerencia):
    n = next(_SEQ)
    if metodo == "POST":
        return client.post("/api/gerencias/", {"nome": f"GERENCIA NOVA {n}", "nome_setor": f"Nova {n}"}, format="json")
    url = f"/api/gerencias/{gerencia.id}/"
    if metodo == "PUT":
        return client.put(
            url, {"nome": gerencia.nome, "nome_setor": gerencia.nome_setor, "descricao": "x"}, format="json"
        )
    if metodo == "PATCH":
        return client.patch(url, {"descricao": "x"}, format="json")
    return client.delete(url)


@pytest.mark.parametrize("metodo", ["POST", "PUT", "PATCH", "DELETE"])
def test_controle_nao_escreve_gerencia(metodo: str) -> None:
    g = _gerencia()
    client = _cliente(_controle())  # cria a gerência CONTROLE antes da contagem
    total = Gerencia.objects.count()

    resp = _escrever(client, metodo, g)

    assert resp.status_code == 403, resp.content
    assert Gerencia.objects.count() == total
    g.refresh_from_db()
    assert g.descricao != "x"


@pytest.mark.parametrize("persona", ["dat", "superusuario"])
@pytest.mark.parametrize(("metodo", "esperado"), [("POST", 201), ("PUT", 200), ("PATCH", 200), ("DELETE", 204)])
def test_dat_e_superusuario_escrevem_gerencia(persona: str, metodo: str, esperado: int) -> None:
    user = _dat() if persona == "dat" else UsuarioFactory(superuser=True)

    resp = _escrever(_cliente(user), metodo, _gerencia())

    assert resp.status_code == esperado, resp.content


def _leitor(persona: str) -> Usuario:
    if persona == "controle":
        return _controle()
    if persona == "dat":
        return _dat()
    if persona == "superusuario":
        return UsuarioFactory(superuser=True)
    user = UsuarioFactory()
    com_papel(user, persona.upper(), _gerencia())
    return user


@pytest.mark.parametrize("persona", ["controle", "dat", "superusuario", "coordenador", "formador"])
def test_leitura_nao_muda(persona: str) -> None:
    g = _gerencia()
    client = _cliente(_leitor(persona))

    assert client.get("/api/gerencias/").status_code == 200
    assert client.get(f"/api/gerencias/{g.id}/").status_code == 200
