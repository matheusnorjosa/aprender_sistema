"""
AS v2 — Teste de identidade da facade de Availability (#1463 / audit 2026-06-19).

Garante que `apps.core.views` (facade) reexporta as views ATIVAS e protegidas
de `apps.core.views_availability` — não as cópias fracas órfãs que existiam em
`apps.core.views.availability` (agora um shim).

Regressão coberta: a facade reexportava `AvailabilityCheckView` com
`permission_classes = [IsAuthenticated]` (cópia órfã, nunca roteada), enquanto o
urls.py roteia a versão de `views_availability` protegida por
`HasPerm("view_all_availability") | ...`. Se a facade voltar a apontar para a
órfã, a identidade quebra.

GOTCHA: NÃO asserir "existe um HasPerm" via isinstance/is — a composição
`HasPerm("a") | HasPerm("b") | HasPerm("c")` colapsa em UMA instância
`rest_framework.permissions.OR`, logo `permission_classes == [<OR>]`. A prova é
a IDENTIDADE de objeto entre facade e módulo ativo; e a AUSÊNCIA de
`IsAuthenticated` discrimina a órfã fraca da versão protegida.
"""

# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated

from apps.core import views, views_availability


def test_facade_availability_check_view_is_active_view() -> None:
    """A facade reexporta a AvailabilityCheckView ativa (não a órfã)."""
    assert views.AvailabilityCheckView is views_availability.AvailabilityCheckView


def test_facade_availability_check_many_view_is_active_view() -> None:
    """A facade reexporta a AvailabilityCheckManyView ativa (não a órfã)."""
    assert views.AvailabilityCheckManyView is views_availability.AvailabilityCheckManyView


def test_facade_availability_block_viewset_is_active_view() -> None:
    """A facade reexporta o AvailabilityBlockViewSet ativo (não a órfã)."""
    assert views.AvailabilityBlockViewSet is views_availability.AvailabilityBlockViewSet


def test_facade_check_view_is_not_the_weak_orphan() -> None:
    """
    A AvailabilityCheckView exposta pela facade NÃO é a órfã fraca.

    A órfã tinha `permission_classes = [IsAuthenticated]`; a ativa usa
    `HasPerm(...) | HasPerm(...) | HasPerm(...)` (composta numa instância OR).
    A ausência de `IsAuthenticated` na lista discrimina uma da outra.
    """
    perms = views.AvailabilityCheckView.permission_classes
    assert not any(p is IsAuthenticated for p in perms)
