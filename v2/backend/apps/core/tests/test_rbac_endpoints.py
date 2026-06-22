"""
Testes RBAC para endpoints de aprovação/reprovação.

Issue #250: Garantir cobertura de testes para permissões nos endpoints:
- POST/PATCH /api/solicitacoes/{id}/approve/
- POST/PATCH /api/solicitacoes/{id}/reject/

Complementa test_approval_policy_PA.py com cenários adicionais:
- DAT pode aprovar (PA-02 Adaptada)
- Usuário não autenticado recebe 401
- Formador (sem permissão) recebe 403
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def grupo_superintendencia():
    """Grupo Superintendência."""
    grupo = GroupFactory(name="Superintendência")
    return grupo


@pytest.fixture
def grupo_dat():
    """Grupo DAT."""
    grupo = GroupFactory(name="DAT")
    return grupo


@pytest.fixture
def grupo_formador():
    """Grupo Formador."""
    grupo = GroupFactory(name="Formador")
    return grupo


@pytest.fixture
def grupo_gerente():
    """Função Gerente (PR 3, 2026-04-29 — composite Gerente+Sup aprova)."""
    grupo = GroupFactory(name="Gerente")
    return grupo


@pytest.fixture
def user_superintendencia(grupo_superintendencia, grupo_gerente):
    """PR 3 hardening RBAC: composite Gerente da Superintendência (Setor
    Superintendência + Função Gerente). Sup puro sem Função não aprova mais."""
    uid = uuid4().hex[:8]
    user = UsuarioFactory(
        username=f"super_rbac_{uid}",
        email=f"super_rbac_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )
    user.groups.add(grupo_superintendencia, grupo_gerente)
    return user


@pytest.fixture
def user_dat(grupo_dat):
    """PR 3 hardening RBAC: DAT NÃO aprova mais (regra anterior PA-02 Adaptada
    foi descontinuada). Mantém o nome `user_dat` para os testes invertidos."""
    uid = uuid4().hex[:8]
    user = UsuarioFactory(
        username=f"dat_rbac_{uid}",
        email=f"dat_rbac_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )
    user.groups.add(grupo_dat)
    return user


@pytest.fixture
def user_formador(grupo_formador):
    """Usuário do grupo Formador (sem permissão de aprovação)."""
    uid = uuid4().hex[:8]
    user = UsuarioFactory(
        username=f"formador_rbac_{uid}",
        email=f"formador_rbac_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )
    user.groups.add(grupo_formador)
    return user


@pytest.fixture
def solicitacao_pendente(user_formador):
    """Solicitação pendente para testes RBAC."""
    municipio = MunicipioFactory(nome="Fortaleza RBAC", uf="CE", ativo=True)
    projeto = ProjetoFactory(nome="Projeto RBAC SUPER", ativo=True, fluxo="SUPER")
    tipo_evento = TipoEventoFactory(nome="Formação RBAC")

    now = timezone.now()
    return SolicitacaoFactory(
        usuario=user_formador,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="pendente",
    )


class TestRBACApprovalEndpoints:
    """Testes RBAC para endpoints /approve/ e /reject/."""

    def test_unauthenticated_cannot_approve(self, solicitacao_pendente):
        """Usuário não autenticado recebe 401 ou 403 ao tentar aprovar.

        Nota: DRF pode retornar 401 ou 403 dependendo da configuração de autenticação.
        Ambos são válidos para indicar acesso negado a usuários não autenticados.
        """
        client = APIClient()
        # Não autenticar - cliente sem credenciais

        response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ), f"Esperado 401 ou 403, recebido {response.status_code}"

    def test_unauthenticated_cannot_reject(self, solicitacao_pendente):
        """Usuário não autenticado recebe 401 ou 403 ao tentar reprovar.

        Nota: DRF pode retornar 401 ou 403 dependendo da configuração de autenticação.
        """
        client = APIClient()

        response = client.patch(
            f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
            {"justificativa": "Teste"},
        )

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ), f"Esperado 401 ou 403, recebido {response.status_code}"

    def test_formador_cannot_approve(self, solicitacao_pendente, user_formador):
        """Formador recebe 403 ao tentar aprovar."""
        client = APIClient()
        client.force_authenticate(user=user_formador)

        response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")

        assert response.status_code == status.HTTP_403_FORBIDDEN, f"Esperado 403, recebido {response.status_code}"

    def test_formador_cannot_reject(self, solicitacao_pendente, user_formador):
        """Formador recebe 403 ao tentar reprovar."""
        client = APIClient()
        client.force_authenticate(user=user_formador)

        response = client.patch(
            f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
            {"justificativa": "Teste"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, f"Esperado 403, recebido {response.status_code}"

    def test_dat_cannot_approve(self, solicitacao_pendente, user_dat):
        """PR 3 hardening RBAC (2026-04-29): DAT NÃO aprova mais.

        Regra antiga (PA-02 Adaptada) incluía DAT; após PR 3, apenas
        Gerente da Superintendência ou Assistente Administrativo do
        Controle podem aprovar.
        """
        client = APIClient()
        client.force_authenticate(user=user_dat)

        response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")

        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"DAT deve receber 403 em approve, recebido {response.status_code}"

    def test_dat_cannot_reject(self, user_dat, user_formador):
        """PR 3 hardening RBAC (2026-04-29): DAT NÃO reprova mais."""
        municipio = MunicipioFactory(nome="Fortaleza RBAC", uf="CE", ativo=True)
        projeto = ProjetoFactory(nome="Projeto RBAC SUPER", ativo=True, fluxo="SUPER")
        tipo_evento = TipoEventoFactory(nome="Formação RBAC")

        now = timezone.now()
        solicitacao = SolicitacaoFactory(
            usuario=user_formador,
            municipio=municipio,
            projeto=projeto,
            tipo_evento=tipo_evento,
            inicio=now + timedelta(days=2),
            fim=now + timedelta(days=2, hours=2),
            status="pendente",
        )

        client = APIClient()
        client.force_authenticate(user=user_dat)

        response = client.patch(
            f"/api/solicitacoes/{solicitacao.id}/reject/",
            {"justificativa": "tentativa"},
        )

        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"DAT deve receber 403 em reject, recebido {response.status_code}"

    def test_gerente_superintendencia_can_approve(self, solicitacao_pendente, user_superintendencia):
        """PR 3 hardening RBAC: Gerente da Superintendência aprova."""
        client = APIClient()
        client.force_authenticate(user=user_superintendencia)

        response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ), f"Gerente Superintendência deve poder aprovar, recebido {response.status_code}"

    def test_gerente_superintendencia_can_reject(self, user_superintendencia, user_formador):
        """PR 3 hardening RBAC: Gerente da Superintendência reprova."""
        # Criar nova solicitação para este teste
        municipio = MunicipioFactory(nome="Fortaleza RBAC", uf="CE", ativo=True)
        projeto = ProjetoFactory(nome="Projeto RBAC SUPER", ativo=True, fluxo="SUPER")
        tipo_evento = TipoEventoFactory(nome="Formação RBAC")

        now = timezone.now()
        solicitacao = SolicitacaoFactory(
            usuario=user_formador,
            municipio=municipio,
            projeto=projeto,
            tipo_evento=tipo_evento,
            inicio=now + timedelta(days=3),
            fim=now + timedelta(days=3, hours=2),
            status="pendente",
        )

        client = APIClient()
        client.force_authenticate(user=user_superintendencia)

        response = client.patch(
            f"/api/solicitacoes/{solicitacao.id}/reject/",
            {"justificativa": "Reprovado pela Superintendência"},
        )

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ), f"Superintendência deve poder reprovar, recebido {response.status_code}"
