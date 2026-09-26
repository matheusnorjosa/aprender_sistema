"""
Feature (épico #2035 / onboarding): o cadastro de usuário (`/api/usuarios-admin/`)
passa a criar o vínculo `EquipeGerencia` a partir de uma Gerência selecionada +
a Função (papel), e auto-atribui o grupo de setor por nome quando existir.

Motivo: o escopo da Wave 1 (#1656) usa `EquipeGerencia -> Gerencia.setor_canonico`,
NÃO o grupo RBAC de setor. Antes, o form só setava grupos -> quem era criado ficava
sem vínculo e invisível para o coordenador do setor (bug de onboarding real, 2026-09-25).

Regras:
- `gerencia_id` + Função -> vínculo `EquipeGerencia(gerencia, papel)` (papel derivado da
  função: Formador->FORMADOR, Coordenador->COORDENADOR, Gerente->GERENTE,
  Apoio de Coordenação->APOIO; Assistente Administrativo NÃO vira papel).
- Auto-atribui o grupo de setor cujo nome == `Gerencia.setor_canonico`, quando existir.
- Superuser-only (mesma trava de `group_ids`, Tier-0).
- O form é SSOT da lotação: trocar a gerência encerra o vínculo antigo e abre o novo.
- PATCH sem `gerencia_id` (ex.: só senha/telefone) NÃO mexe no vínculo.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def root(db):
    return UsuarioFactory(username="root_ger", cpf="92000000009", superuser=True)


@pytest.fixture
def dat(db):
    user = UsuarioFactory(username="dat_ger", cpf="92000000001")
    user.groups.add(GroupFactory(name="DAT"))
    return user


@pytest.fixture
def gerencia_fluir(db):
    """Gerência cujo setor_canonico coincide com um grupo RBAC ('Fluir')."""
    GroupFactory(name="Fluir")  # grupo de setor com mesmo nome do setor_canonico
    return Gerencia.objects.create(nome="GERENCIA FLUIR TESTE", setor_canonico="Fluir", nome_setor="Fluir", ativo=True)


@pytest.fixture
def gerencia_vidas(db):
    return Gerencia.objects.create(
        nome="GERENCIA VIDAS TESTE", setor_canonico="Vidas", nome_setor="Vidas M", ativo=True
    )


@pytest.mark.django_db
class TestCreateUserWithGerencia:
    def test_superuser_create_formador_creates_vinculo_and_setor_group(self, api_client, root, gerencia_fluir):
        formador = GroupFactory(name="Formador")
        api_client.force_authenticate(root)
        resp = api_client.post(
            "/api/usuarios-admin/",
            {
                "username": "novo_formador",
                "email": "novo_formador@example.com",
                "cpf": "92000000010",
                "password": "SecurePass123!",
                "group_ids": [formador.id],
                "gerencia_id": gerencia_fluir.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        u = Usuario.objects.get(username="novo_formador")
        vinc = EquipeGerencia.objects.filter(usuario=u, gerencia=gerencia_fluir, papel="FORMADOR", ativo=True)
        assert vinc.exists(), "vínculo FORMADOR ativo deveria ter sido criado"
        # grupo de setor auto-atribuído por nome (== setor_canonico 'Fluir')
        assert set(u.groups.values_list("name", flat=True)) >= {"Formador", "Fluir"}

    def test_papel_derived_coordenador(self, api_client, root, gerencia_fluir):
        coord = GroupFactory(name="Coordenador")
        api_client.force_authenticate(root)
        resp = api_client.post(
            "/api/usuarios-admin/",
            {
                "username": "novo_coord",
                "email": "novo_coord@example.com",
                "cpf": "92000000011",
                "password": "SecurePass123!",
                "group_ids": [coord.id],
                "gerencia_id": gerencia_fluir.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        u = Usuario.objects.get(username="novo_coord")
        assert EquipeGerencia.objects.filter(
            usuario=u, gerencia=gerencia_fluir, papel="COORDENADOR", ativo=True
        ).exists()

    def test_assistente_administrativo_no_papel_no_crash(self, api_client, root, gerencia_fluir):
        asss = GroupFactory(name="Assistente Administrativo")
        api_client.force_authenticate(root)
        resp = api_client.post(
            "/api/usuarios-admin/",
            {
                "username": "novo_asa",
                "email": "novo_asa@example.com",
                "cpf": "92000000012",
                "password": "SecurePass123!",
                "group_ids": [asss.id],
                "gerencia_id": gerencia_fluir.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        u = Usuario.objects.get(username="novo_asa")
        # Assistente Administrativo não é papel -> nenhum vínculo criado
        assert not EquipeGerencia.objects.filter(usuario=u, gerencia=gerencia_fluir).exists()

    def test_dat_non_superuser_gerencia_ignored(self, api_client, dat, gerencia_fluir):
        formador = GroupFactory(name="Formador")
        api_client.force_authenticate(dat)
        resp = api_client.post(
            "/api/usuarios-admin/",
            {
                "username": "novo_por_dat",
                "email": "novo_por_dat@example.com",
                "cpf": "92000000013",
                "password": "SecurePass123!",
                "group_ids": [formador.id],
                "gerencia_id": gerencia_fluir.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        u = Usuario.objects.get(username="novo_por_dat")
        # Tier-0: não-superuser não muta membership nem lotação
        assert not EquipeGerencia.objects.filter(usuario=u).exists()
        assert u.groups.count() == 0


@pytest.mark.django_db
class TestUpdateUserGerencia:
    def test_change_gerencia_closes_old_opens_new(self, api_client, root, gerencia_fluir, gerencia_vidas):
        formador = GroupFactory(name="Formador")
        target = UsuarioFactory(username="alvo_troca", cpf="92000000020")
        EquipeGerencia.objects.create(gerencia=gerencia_fluir, usuario=target, papel="FORMADOR", ativo=True)
        api_client.force_authenticate(root)
        resp = api_client.patch(
            f"/api/usuarios-admin/{target.id}/",
            {"group_ids": [formador.id], "gerencia_id": gerencia_vidas.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        # nova gerência ativa
        assert EquipeGerencia.objects.filter(
            usuario=target, gerencia=gerencia_vidas, papel="FORMADOR", ativo=True
        ).exists()
        # antiga encerrada
        antiga = EquipeGerencia.objects.get(usuario=target, gerencia=gerencia_fluir, papel="FORMADOR")
        assert antiga.ativo is False

    def test_patch_without_gerencia_leaves_vinculo(self, api_client, root, gerencia_fluir):
        target = UsuarioFactory(username="alvo_sem_ger", cpf="92000000021")
        EquipeGerencia.objects.create(gerencia=gerencia_fluir, usuario=target, papel="FORMADOR", ativo=True)
        api_client.force_authenticate(root)
        resp = api_client.patch(f"/api/usuarios-admin/{target.id}/", {"telefone": "85911112222"}, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert EquipeGerencia.objects.filter(
            usuario=target, gerencia=gerencia_fluir, papel="FORMADOR", ativo=True
        ).exists()
