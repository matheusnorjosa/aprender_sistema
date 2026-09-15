"""
M15-02 (#1632) — invariantes de estoque/valor do DATCompra no BANCO (CheckConstraint).

O serializer (DATCompraSerializer.validate) já barra no write da API, mas um
import/`.update()`/shell grava por fora. Estas CHECKs tornam as regras invioláveis
no PostgreSQL:
- quantidade ≥ 0
- quantidade_utilizada ≥ 0
- quantidade_utilizada ≤ quantidade  (não dá pra usar mais do que se comprou)
- valor_unitario ≥ 0

⚑ A NK (UniqueConstraint) que a #1632 também pedia foi DESCARTADA: a medição do
dado (dev: 196 grupos com mesma município+projeto+produto+ano) mostrou que não
existe chave natural — várias compras do mesmo produto/ano são legítimas (compra
inicial vs adicional 1/2/3), e o histórico importado do sheets.banco não tinha id
de compra/nota. Ver memória `feedback-datcompra-no-natural-key-imported-history`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportMissingTypeStubs=false

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction

import pytest

from apps.core.models import DATCompra
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _compra(**kw):
    defaults = dict(
        municipio=MunicipioFactory(),
        projeto=ProjetoFactory(),
        descricao_produto="Produto CC",
        quantidade=5,
        quantidade_utilizada=0,
        valor_unitario=Decimal("10.00"),
        ano_uso=2025,
        created_by=UsuarioFactory(),
    )
    defaults.update(kw)
    return DATCompra.objects.create(**defaults)


class TestDATCompraCheckConstraints:
    def test_utilizada_maior_que_quantidade_rejeitado(self):
        """RED: sem CHECK, `.update()` grava utilizada > quantidade direto no banco."""
        c = _compra(quantidade=5, quantidade_utilizada=0)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DATCompra.objects.filter(pk=c.pk).update(quantidade_utilizada=10)

    def test_valor_unitario_negativo_rejeitado(self):
        c = _compra()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DATCompra.objects.filter(pk=c.pk).update(valor_unitario=Decimal("-1.00"))

    def test_quantidade_negativa_rejeitada(self):
        c = _compra()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DATCompra.objects.filter(pk=c.pk).update(quantidade=-1)

    def test_utilizada_negativa_rejeitada(self):
        c = _compra(quantidade=5)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DATCompra.objects.filter(pk=c.pk).update(quantidade_utilizada=-1)

    def test_valores_validos_persistem(self):
        """Não-regressão: valores dentro das regras gravam normalmente."""
        c = _compra(quantidade=10, quantidade_utilizada=3, valor_unitario=Decimal("5.50"))
        DATCompra.objects.filter(pk=c.pk).update(quantidade_utilizada=10)  # utilizada == quantidade OK
        c.refresh_from_db()
        assert c.quantidade_utilizada == 10
