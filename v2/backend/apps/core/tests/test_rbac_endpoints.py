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

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def grupo_superintendencia():
    """Grupo Superintendência."""
    grupo, _ = Group.objects.get_or_create(name="Superintendência")
    return grupo


@pytest.fixture
def grupo_dat():
    """Grupo DAT."""
    grupo, _ = Group.objects.get_or_create(name="DAT")
    return grupo


@pytest.fixture
def grupo_formador():
    """Grupo Formador."""
    grupo, _ = Group.objects.get_or_create(name="Formador")
    return grupo


@pytest.fixture
def user_superintendencia(grupo_superintendencia):
    """Usuário do grupo Superintendência."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"super_rbac_{uid}",
        email=f"super_rbac_{uid}@test.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )
    user.groups.add(grupo_superintendencia)
    return user


@pytest.fixture
def user_dat(grupo_dat):
    """Usuário do grupo DAT."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
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
    user = Usuario.objects.create_user(
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
    municipio, _ = Municipio.objects.get_or_create(nome="Fortaleza RBAC", defaults={"uf": "CE", "ativo": True})
    projeto, _ = Projeto.objects.get_or_create(
        nome="Projeto RBAC SUPER",
        defaults={"ativo": True, "fluxo": "SUPER"},
    )
    tipo_evento, _ = TipoEvento.objects.get_or_create(nome="Formação RBAC")

    now = timezone.now()
    return Solicitacao.objects.create(
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

    def test_dat_can_approve(self, solicitacao_pendente, user_dat):
        """DAT pode aprovar (PA-02 Adaptada).

        PA-02 foi adaptada para incluir DAT além de Superintendência.
        Ver HasPerm("approve_solicitation") permission class.
        """
        client = APIClient()
        client.force_authenticate(user=user_dat)

        response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ), f"DAT deve poder aprovar, recebido {response.status_code}"

        # Verificar que status mudou para aprovado
        solicitacao_pendente.refresh_from_db()
        assert solicitacao_pendente.status == "aprovado"

    def test_dat_can_reject(self, user_dat, user_formador):
        """DAT pode reprovar (PA-02 Adaptada)."""
        # Criar nova solicitação para este teste
        municipio, _ = Municipio.objects.get_or_create(nome="Fortaleza RBAC", defaults={"uf": "CE", "ativo": True})
        projeto, _ = Projeto.objects.get_or_create(
            nome="Projeto RBAC SUPER",
            defaults={"ativo": True, "fluxo": "SUPER"},
        )
        tipo_evento, _ = TipoEvento.objects.get_or_create(nome="Formação RBAC")

        now = timezone.now()
        solicitacao = Solicitacao.objects.create(
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
            {"justificativa": "Reprovado pelo DAT"},
        )

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ), f"DAT deve poder reprovar, recebido {response.status_code}"

        # Verificar que status mudou para reprovado
        solicitacao.refresh_from_db()
        assert solicitacao.status == "reprovado"

    def test_superintendencia_can_approve(self, solicitacao_pendente, user_superintendencia):
        """Superintendência pode aprovar (PA-02)."""
        client = APIClient()
        client.force_authenticate(user=user_superintendencia)

        response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ), f"Superintendência deve poder aprovar, recebido {response.status_code}"

    def test_superintendencia_can_reject(self, user_superintendencia, user_formador):
        """Superintendência pode reprovar (PA-02)."""
        # Criar nova solicitação para este teste
        municipio, _ = Municipio.objects.get_or_create(nome="Fortaleza RBAC", defaults={"uf": "CE", "ativo": True})
        projeto, _ = Projeto.objects.get_or_create(
            nome="Projeto RBAC SUPER",
            defaults={"ativo": True, "fluxo": "SUPER"},
        )
        tipo_evento, _ = TipoEvento.objects.get_or_create(nome="Formação RBAC")

        now = timezone.now()
        solicitacao = Solicitacao.objects.create(
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
