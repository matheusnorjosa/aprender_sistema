"""
Mixins de view compartilhados (DRF).

`LockOnWriteMixin`: serializa o read-modify-write de PATCH/PUT/DELETE com lock de
linha, prevenindo lost update em edições concorrentes (M15-08/#1665, M16-04/#1651).
Sem ele, dois PATCH concorrentes leem a mesma linha (`get_object` sem lock) e o
último a gravar sobrescreve o outro.
"""

# pyright: reportMissingTypeStubs=false, reportUntypedBaseClass=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Any

from django.db import transaction


class LockOnWriteMixin:
    """Trava a linha em métodos de escrita e roda a escrita numa transação.

    - `get_queryset`: em PUT/PATCH/DELETE aplica `select_for_update(of=("self",))`.
      `of=("self",)` trava só a tabela do próprio model — evita o erro do PostgreSQL
      "FOR UPDATE cannot be applied to the nullable side of an outer join" quando o
      queryset tem `select_related` de FK opcional (ex.: DATCompra.produto).
    - `update`/`destroy`: envolvem a operação em `transaction.atomic()` — pré-requisito
      do `select_for_update` (ATOMIC_REQUESTS=False neste projeto → a request não é
      atômica por si). `partial_update` do DRF delega a `update`, então PATCH é coberto.

    Ordem de herança: colocar ANTES do ViewSet (`class X(LockOnWriteMixin, ModelViewSet)`)
    para os overrides valerem.
    """

    _WRITE_METHODS = frozenset({"PUT", "PATCH", "DELETE"})

    def get_queryset(self) -> Any:
        qs = super().get_queryset()  # type: ignore[misc]
        method = getattr(getattr(self, "request", None), "method", None)
        if method in self._WRITE_METHODS:
            qs = qs.select_for_update(of=("self",))
        return qs

    def update(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        with transaction.atomic():
            return super().update(request, *args, **kwargs)  # type: ignore[misc]

    def destroy(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        with transaction.atomic():
            return super().destroy(request, *args, **kwargs)  # type: ignore[misc]
