"""
Testes para CPFOrUsernameBackend (Issue #134 - P1).

Valida:
- Autenticação via CPF (com e sem máscara)
- Autenticação via username
- CPF com leading zeros
- Senha incorreta rejeitada
- Usuário inativo bloqueado
- Credenciais vazias rejeitadas
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false

from __future__ import annotations
import pytest
from uuid import uuid4
from django.test import RequestFactory

from apps.core.models import Usuario
from apps.core.auth_backends import CPFOrUsernameBackend


pytestmark = pytest.mark.django_db


@pytest.fixture
def backend():
    """Instance of CPFOrUsernameBackend."""
    return CPFOrUsernameBackend()


@pytest.fixture
def request_factory():
    """Django RequestFactory for creating mock requests."""
    return RequestFactory()


@pytest.fixture
def usuario_com_cpf():
    """Usuário com CPF para testes de autenticação."""
    uid = uuid4().hex
    cpf = "12345678901"  # CPF fixo para testes
    return Usuario.objects.create_user(
        username=f"user_{uid}",
        email=f"user_{uid}@example.com",
        password="testpass123",
        cpf=cpf,
        is_active=True,
    )


@pytest.fixture
def usuario_cpf_com_zeros():
    """Usuário com CPF contendo leading zeros."""
    uid = uuid4().hex
    cpf = "00123456789"  # CPF com leading zeros
    return Usuario.objects.create_user(
        username=f"user_zeros_{uid}",
        email=f"user_zeros_{uid}@example.com",
        password="testpass123",
        cpf=cpf,
        is_active=True,
    )


@pytest.fixture
def usuario_inativo():
    """Usuário inativo para testes de bloqueio."""
    uid = uuid4().hex
    cpf = str(uuid4().int % 10**11).zfill(11)
    return Usuario.objects.create_user(
        username=f"inactive_{uid}",
        email=f"inactive_{uid}@example.com",
        password="testpass123",
        cpf=cpf,
        is_active=False,
    )


# ===================================================================
# AUTENTICAÇÃO VIA CPF
# ===================================================================


def test_authenticate_via_cpf_plain(backend, request_factory, usuario_com_cpf):
    """
    Autenticação via CPF sem máscara deve funcionar.

    Valida:
    - CPF "12345678901" → autentica usuário correto
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="12345678901",
        password="testpass123"
    )

    assert user is not None
    assert user == usuario_com_cpf
    assert user.cpf == "12345678901"


def test_authenticate_via_cpf_with_mask(backend, request_factory, usuario_com_cpf):
    """
    Autenticação via CPF com máscara deve funcionar.

    Valida:
    - CPF "123.456.789-01" → remove pontuação → autentica
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="123.456.789-01",
        password="testpass123"
    )

    assert user is not None
    assert user == usuario_com_cpf
    assert user.cpf == "12345678901"


def test_authenticate_via_cpf_with_spaces(backend, request_factory, usuario_com_cpf):
    """
    CPF com espaços deve ser normalizado e autenticar.

    Valida:
    - CPF "123 456 789 01" → remove espaços → autentica
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="123 456 789 01",
        password="testpass123"
    )

    assert user is not None
    assert user == usuario_com_cpf


def test_authenticate_via_cpf_with_leading_zeros(backend, request_factory, usuario_cpf_com_zeros):
    """
    CPF com leading zeros deve autenticar corretamente.

    Valida:
    - CPF "00123456789" mantém zeros → autentica
    - CPF "001.234.567-89" com máscara → autentica
    """
    request = request_factory.get("/")

    # Sem máscara
    user = backend.authenticate(
        request=request,
        username="00123456789",
        password="testpass123"
    )
    assert user is not None
    assert user == usuario_cpf_com_zeros

    # Com máscara
    user = backend.authenticate(
        request=request,
        username="001.234.567-89",
        password="testpass123"
    )
    assert user is not None
    assert user == usuario_cpf_com_zeros


def test_authenticate_via_cpf_wrong_password(backend, request_factory, usuario_com_cpf):
    """
    CPF correto com senha errada deve retornar None.

    Valida:
    - CPF "12345678901" + senha errada → None
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="12345678901",
        password="wrongpass"
    )

    assert user is None


def test_authenticate_via_cpf_not_found(backend, request_factory):
    """
    CPF inexistente deve retornar None.

    Valida:
    - CPF "99999999999" (não existe) → None
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="99999999999",
        password="testpass123"
    )

    assert user is None


# ===================================================================
# AUTENTICAÇÃO VIA USERNAME
# ===================================================================


def test_authenticate_via_username(backend, request_factory, usuario_com_cpf):
    """
    Autenticação via username deve funcionar.

    Valida:
    - username (não é 11 dígitos) → tenta username lookup
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username=usuario_com_cpf.username,
        password="testpass123"
    )

    assert user is not None
    assert user == usuario_com_cpf


def test_authenticate_via_username_wrong_password(backend, request_factory, usuario_com_cpf):
    """
    Username correto com senha errada deve retornar None.

    Valida:
    - username + senha errada → None
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username=usuario_com_cpf.username,
        password="wrongpass"
    )

    assert user is None


def test_authenticate_via_username_not_found(backend, request_factory):
    """
    Username inexistente deve retornar None.

    Valida:
    - username "nonexistent" → None
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="nonexistent",
        password="testpass123"
    )

    assert user is None


# ===================================================================
# VALIDAÇÕES DE SEGURANÇA
# ===================================================================


def test_authenticate_empty_username(backend, request_factory):
    """
    Username vazio deve retornar None.

    Valida:
    - username=None → None
    - username="" é diferente (processa string vazia, retorna None por não encontrar)
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username=None,
        password="testpass123"
    )

    assert user is None


def test_authenticate_empty_password(backend, request_factory, usuario_com_cpf):
    """
    Password vazio deve retornar None.

    Valida:
    - password=None → None
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username=usuario_com_cpf.username,
        password=None
    )

    assert user is None


def test_authenticate_inactive_user(backend, request_factory, usuario_inativo):
    """
    Usuário inativo deve ser bloqueado (user_can_authenticate=False).

    Valida:
    - is_active=False → None (mesmo com senha correta)
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username=usuario_inativo.username,
        password="testpass123"
    )

    assert user is None


# ===================================================================
# EDGE CASES
# ===================================================================


def test_authenticate_cpf_10_digits(backend, request_factory):
    """
    CPF com 10 dígitos (não 11) deve tentar username lookup.

    Valida:
    - "1234567890" (10 dígitos) → não é CPF → tenta username
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="1234567890",
        password="testpass123"
    )

    # Como não existe username "1234567890", retorna None
    assert user is None


def test_authenticate_cpf_12_digits(backend, request_factory):
    """
    CPF com 12 dígitos (não 11) deve tentar username lookup.

    Valida:
    - "123456789012" (12 dígitos) → não é CPF → tenta username
    """
    request = request_factory.get("/")
    user = backend.authenticate(
        request=request,
        username="123456789012",
        password="testpass123"
    )

    # Como não existe username "123456789012", retorna None
    assert user is None


def test_authenticate_alphanumeric_tries_username(backend, request_factory, usuario_com_cpf):
    """
    Input alfanumérico deve tentar username lookup (não CPF).

    Valida:
    - "user123" (contém letras) → tenta username
    """
    request = request_factory.get("/")

    # Criar usuário com username alfanumérico
    uid = uuid4().hex
    user_alpha = Usuario.objects.create_user(
        username="user123",
        email=f"user123_{uid}@example.com",
        password="testpass123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        is_active=True,
    )

    user = backend.authenticate(
        request=request,
        username="user123",
        password="testpass123"
    )

    assert user is not None
    assert user == user_alpha
