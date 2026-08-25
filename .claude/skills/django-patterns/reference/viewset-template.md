# ViewSet template — thin controller + service layer

Rules:
- **Thin controllers**: views validate + delegate; business logic lives in
  `apps/core/services/`. A view method with 50 lines of logic is a smell.
- **Read vs write serializer** picked in `get_serializer_class()`.
- **Owner / sector scope** filtered in `get_queryset()` (see SKILL.md RBAC section),
  not by re-checking identity inside the body.
- **N+1**: `select_related` (FK/OneToOne) + `prefetch_related` (M2M/reverse FK).

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.rbac import HasPerm
from apps.core.serializers import (
    SolicitacaoReadSerializer,
    SolicitacaoWriteSerializer,
)


class SolicitacaoViewSet(viewsets.ModelViewSet):
    """CRUD + custom actions for Solicitacao."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Solicitacao.objects.select_related(
            "solicitante", "municipio", "projeto",
        ).prefetch_related("participantes")
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(solicitante=user)  # owner-scope
        return qs

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return SolicitacaoReadSerializer
        return SolicitacaoWriteSerializer

    def perform_create(self, serializer):
        # keep thin; set owner from request
        serializer.save(solicitante=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[HasPerm("approve_solicitation")])
    def approve(self, request, pk=None):
        """POST /api/solicitacoes/{id}/approve/ — delegate to service."""
        solicitacao = self.get_object()
        if solicitacao.status != "pendente":
            return Response(
                {"error": "Solicitação já foi processada"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.core.services.solicitacao_approval import approve_solicitacao
        try:
            result = approve_solicitacao(
                solicitacao=solicitacao,
                aprovador=request.user,
                justificativa=request.data.get("justificativa", ""),
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

## get_permissions() override hides @action permissions

If a ViewSet overrides `get_permissions()`, that override **wins** over
`@action(permission_classes=...)` — the decorator's classes are silently ignored.
Check `get_permissions()` before assuming an action's declared permissions apply.
(Real example: `apps/core/views_solicitacao.py` `SolicitacaoViewSet.get_permissions()`
maps `approve`/`batch_approve` to a Policy class, `CanAccessSolicitationApprovals`.)

## DRF permission composition needs instances in get_permissions()

In `permission_classes = [...]` you pass classes. In `get_permissions()` you must return
**instances**:

```python
def get_permissions(self):
    if self.action == "approve":
        return [HasPerm("approve_solicitation")()]   # note the trailing ()
    return [IsAuthenticated()]
```

Real reference: `apps/core/views_solicitacao.py` (canonical impl; `views/solicitacao.py`
is a compat re-export wrapper).
