"""
Testes para modelo Participation - PR #1

Valida:
- UniqueConstraint (solicitacao, usuario, role)
- Integridade referencial
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from apps.core.models import Participation, Solicitacao, Municipio, TipoEvento, Projeto

pytestmark = pytest.mark.django_db


@pytest.fixture
def factory_solicitacao():
    """
    Factory para criar Solicitacao com dependências mínimas.
    """

    def _factory(**kwargs):
        User = get_user_model()
        user = User.objects.create_user(
            username="solicita_user",
            email="solicita@example.com",
            password="testpass123",
            cpf="12345678901",
        )

        municipio = Municipio.objects.create(
            nome="Fortaleza", uf="CE", ativo=True
        )

        tipo_evento = TipoEvento.objects.create(
            nome="Formação", descricao="Formação continuada"
        )

        projeto = Projeto.objects.create(
            nome="Teste Projeto", ativo=True
        )

        defaults = {
            "usuario": user,
            "municipio": municipio,
            "tipo_evento": tipo_evento,
            "projeto": projeto,
            "inicio": timezone.now(),
            "fim": timezone.now() + timezone.timedelta(hours=2),
            "status": "pendente",
        }
        defaults.update(kwargs)

        return Solicitacao.objects.create(**defaults)

    return _factory


def test_participation_unique_constraint(factory_solicitacao):
    """
    Testa que UniqueConstraint impede duplicação de papel por (solicitacao, usuario, role).
    """
    solicitacao = factory_solicitacao()
    User = get_user_model()
    user = User.objects.create_user(
        username="formador1",
        email="formador1@example.com",
        password="testpass123",
        cpf="98765432100",
    )

    # Criar primeira participation
    Participation.objects.create(
        solicitacao=solicitacao,
        usuario=user,
        role=Participation.Role.COORDENADOR,
    )

    # Tentar criar duplicata deve falhar
    with pytest.raises(IntegrityError):
        Participation.objects.create(
            solicitacao=solicitacao,
            usuario=user,
            role=Participation.Role.COORDENADOR,
        )


def test_participation_allows_different_roles_same_user(factory_solicitacao):
    """
    Testa que o mesmo usuário pode ter múltiplos papéis DIFERENTES na mesma solicitação.
    """
    solicitacao = factory_solicitacao()
    User = get_user_model()
    user = User.objects.create_user(
        username="multi_role",
        email="multi@example.com",
        password="testpass123",
        cpf="11122233344",
    )

    # Criar COORDENADOR
    p1 = Participation.objects.create(
        solicitacao=solicitacao,
        usuario=user,
        role=Participation.Role.COORDENADOR,
    )

    # Criar FORMADOR (mesmo user, role diferente) deve funcionar
    p2 = Participation.objects.create(
        solicitacao=solicitacao,
        usuario=user,
        role=Participation.Role.FORMADOR,
    )

    assert p1.id != p2.id
    assert Participation.objects.filter(solicitacao=solicitacao, usuario=user).count() == 2


def test_participation_cascade_delete_on_solicitacao(factory_solicitacao):
    """
    Testa que deletar Solicitacao deleta Participations em cascata.
    """
    solicitacao = factory_solicitacao()
    User = get_user_model()
    user = User.objects.create_user(
        username="cascade_test",
        email="cascade@example.com",
        password="testpass123",
        cpf="55566677788",
    )

    Participation.objects.create(
        solicitacao=solicitacao,
        usuario=user,
        role=Participation.Role.FORMADOR,
    )

    assert Participation.objects.filter(solicitacao=solicitacao).count() == 1

    # Deletar solicitacao deve deletar participations
    solicitacao.delete()

    assert Participation.objects.filter(solicitacao_id=solicitacao.id).count() == 0


def test_participation_protect_on_usuario_delete(factory_solicitacao):
    """
    Testa que deletar Usuario com Participations deve ser PROTEGIDO (PROTECT).
    """
    solicitacao = factory_solicitacao()
    User = get_user_model()
    user = User.objects.create_user(
        username="protect_test",
        email="protect@example.com",
        password="testpass123",
        cpf="99988877766",
    )

    Participation.objects.create(
        solicitacao=solicitacao,
        usuario=user,
        role=Participation.Role.CONVIDADO,
    )

    # Tentar deletar usuario deve falhar (PROTECT)
    with pytest.raises(Exception):  # Django ProtectedError
        user.delete()
