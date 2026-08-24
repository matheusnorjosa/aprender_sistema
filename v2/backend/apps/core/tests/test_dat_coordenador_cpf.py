"""Opção A — identidade do DATCoordenador por CPF (issue #1837).

Wave 1: o campo `cpf` (raw, nullable, RegexValidator). O CPF é a chave estável de
pessoa que substitui o email de cargo na resolução do coordenador. É PII: nunca
exposto em leitura (serializer/CRUD ficam para wave futura).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

from django.core.exceptions import ValidationError

import pytest

from apps.core.models import DATCoordenador
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF = "11144477735"


def _coord(**kw):
    actor = kw.pop("actor", None) or UsuarioFactory()
    defaults = dict(nome="Amanda Arruda", area="DAT", created_by=actor)
    defaults.update(kw)
    return DATCoordenador.objects.create(**defaults)


def test_cpf_aceita_none():
    """Legado (criado por CRUD) não tem CPF — o campo é nullable."""
    coord = _coord()
    coord.refresh_from_db()
    assert coord.cpf is None


def test_cpf_aceita_11_digitos():
    coord = _coord(cpf=_CPF)
    coord.refresh_from_db()
    assert coord.cpf == _CPF


def test_cpf_regexvalidator_rejeita_mascarado():
    """RegexValidator ^\\d{11}$ barra máscara no full_clean (fecha buraco de CRUD futuro).

    Instância NÃO salva: o full_clean roda o validator/max_length ANTES de qualquer INSERT.
    """
    coord = DATCoordenador(nome="X", area="DAT", created_by=UsuarioFactory(), cpf="111.444.777-35")
    with pytest.raises(ValidationError):
        coord.full_clean()


def test_cpf_regexvalidator_rejeita_tamanho_errado():
    coord = DATCoordenador(nome="X", area="DAT", created_by=UsuarioFactory(), cpf="123")
    with pytest.raises(ValidationError):
        coord.full_clean()
