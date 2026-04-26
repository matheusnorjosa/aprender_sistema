"""
AS v2 — Me Serializers

Serializers minimais para endpoints `/api/me/*` (perfil e participações
do usuário autenticado).

Issue #1224 (Epic 2 RBAC Access Policy Realignment): página /meus-eventos
expõe lista de eventos onde o user é participante. Formador é o caso
primário (única página acessível por intent matrix), mas qualquer user
autenticado pode chamar.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers

from apps.core.models import Solicitacao


class MeEventSerializer(serializers.ModelSerializer):
    """
    Serializer minimal para evento na visão do participante.

    Campos derivados (`*_nome`, `formadores`) ficam fora do model — o frontend
    só precisa rótulos para exibição em lista (não edição).
    """

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True, default=None)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True, default=None)
    tipo_evento_nome = serializers.CharField(source="tipo_evento.nome", read_only=True, default=None)
    formadores = serializers.SerializerMethodField()

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "inicio",
            "fim",
            "municipio_nome",
            "projeto_nome",
            "tipo_evento_nome",
            "local",
            "formadores",
            "is_online",
            "meet_link",
            "status",
        ]
        read_only_fields = fields

    def get_formadores(self, obj: Solicitacao) -> list[str]:
        """Lista nomes dos participantes com role=FORMADOR (ordem estável)."""
        from apps.core.models.solicitacao import Participation

        formadores = (
            obj.participations.filter(role=Participation.Role.FORMADOR, usuario__isnull=False)
            .select_related("usuario")
            .order_by("usuario__first_name", "usuario__last_name")
        )
        return [f"{p.usuario.first_name} {p.usuario.last_name}".strip() for p in formadores]
