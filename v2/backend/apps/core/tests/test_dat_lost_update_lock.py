"""
M15-08 (#1665) / M16-04 (#1651) — lost update em PATCH concorrente nos viewsets DAT.

Dois PATCH concorrentes liam a MESMA linha (`get_object` sem lock) e o último a
gravar sobrescrevia o outro (lost update). O `LockOnWriteMixin` serializa o
read-modify-write: `get_queryset` aplica `select_for_update(of=("self",))` nos
métodos de escrita (o `of=self` evita o erro de FOR UPDATE no lado nulo do OUTER
JOIN do `select_related` de FK opcional), e `update`/`destroy` rodam dentro de
`transaction.atomic()` (select_for_update exige transação; ATOMIC_REQUESTS=False).

Verificação: estrutural (lock aplicado em escrita, não em leitura) + guarda de
regressão (viewsets DAT usam o mixin) + integração (PATCH real → 200, prova que
o lock+atomic não quebram o queryset com select_related). Um teste de corrida real
exigiria threads+PG (flaky) — fora do escopo deste unit.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportMissingTypeStubs=false

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import Group
from rest_framework.test import APIClient, APIRequestFactory

import pytest

from apps.core.models import DATCompra
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory
from apps.core.views.dat import DATRegistroViewSet, ProjetoGeralViewSet
from apps.core.views.dat_module import DATCompraViewSet
from apps.core.views.mixins import LockOnWriteMixin

pytestmark = pytest.mark.django_db


class TestLockOnWriteMixinBehavior:
    def test_locks_queryset_on_patch(self):
        view = DATCompraViewSet()
        view.request = APIRequestFactory().patch("/")
        qs = view.get_queryset()
        assert qs.query.select_for_update is True, "escrita deve travar a linha (select_for_update)"

    def test_no_lock_on_get(self):
        view = DATCompraViewSet()
        view.request = APIRequestFactory().get("/")
        qs = view.get_queryset()
        assert qs.query.select_for_update is False, "leitura NÃO deve travar linha"


class TestDATWriteViewSetsUseMixin:
    @pytest.mark.parametrize("viewset", [DATCompraViewSet, DATRegistroViewSet, ProjetoGeralViewSet])
    def test_viewset_uses_lock_mixin(self, viewset):
        assert issubclass(viewset, LockOnWriteMixin), f"{viewset.__name__} deve usar LockOnWriteMixin"


class TestPatchStillWorks:
    def test_patch_datcompra_ok_com_lock(self):
        """Integração: PATCH real → 200 (lock+atomic não quebram o select_related com FK nula)."""
        user = UsuarioFactory(username="dat_lu", cpf="66600000901")
        user.groups.add(Group.objects.get_or_create(name="DAT")[0])
        compra = DATCompra.objects.create(
            municipio=MunicipioFactory(),
            projeto=ProjetoFactory(),
            descricao_produto="Produto LU",
            quantidade=10,
            valor_unitario=Decimal("5.00"),
            ano_uso=2025,
            created_by=user,
        )
        client = APIClient()
        client.force_authenticate(user)
        resp = client.patch(f"/api/dat/compras-materiais/{compra.id}/", {"quantidade": 20}, format="json")
        assert resp.status_code == 200, resp.data
        compra.refresh_from_db()
        assert compra.quantidade == 20
