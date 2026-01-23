"""
AS v2 — Solicitacao Serializers

Serializers para Solicitacao, Participation e EventDetail.
Clausulas Petreas: PA-01 a PA-07.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import AuditLog, Participation, Solicitacao
from apps.core.serializers.usuario import UserSlimSerializer


class ParticipationNestedSerializer(serializers.ModelSerializer):
    """
    Serializer aninhado para Participation (read-only).
    Usado em SolicitacaoSerializer para expor participations.
    """

    usuario = UserSlimSerializer(read_only=True)
    email = serializers.SerializerMethodField()

    class Meta:
        model = Participation
        fields = ("usuario", "guest_email", "email", "role", "ch_horas", "observacao")

    def get_email(self, obj: Participation) -> str | None:
        user_email = getattr(getattr(obj, "usuario", None), "email", None)
        return user_email or getattr(obj, "guest_email", None)


class SolicitacaoSerializer(serializers.ModelSerializer):
    """
    Serializer for Solicitacao model.
    PA-01: Status sempre começa pendente.

    Inclui campo participations (read-only, aninhado) para expor
    múltiplos participantes com seus papéis.
    """

    participations = ParticipationNestedSerializer(many=True, read_only=True)
    fluxo = serializers.SerializerMethodField()

    # Campos legíveis para exibição (além dos IDs)
    usuario_username = serializers.SerializerMethodField()
    coordenador_username = serializers.SerializerMethodField()
    coordenador_nome = serializers.SerializerMethodField()
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    tipo_evento_nome = serializers.CharField(source="tipo_evento.nome", read_only=True)

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "usuario",
            "usuario_username",
            "municipio",
            "municipio_nome",
            "projeto",
            "projeto_nome",
            "tipo_evento",
            "tipo_evento_nome",
            "tipo",
            "encontro",
            "segmento",
            "coordenador_acompanha",
            "coordenador",
            "coordenador_username",
            "coordenador_nome",
            "inicio",
            "fim",
            "status",
            "observacoes",
            "local",
            # PR19: Modalidade online/presencial (gera Meet apenas quando online)
            "is_online",
            "external_event_id",
            "created_at",
            "updated_at",
            "participations",
            "fluxo",
            # PR14: Campos GCal para rastreamento de sincronização
            "gcal_status",
            "gcal_last_sync_at",
            "gcal_last_error",
            # gcal_payload_hash removed: internal implementation detail
            # PR19/RF06: Google Meet link
            "meet_link",
            # Modalidade online/presencial
            "is_online",
        ]
        read_only_fields = [
            "id",
            "usuario",
            "status",
            "external_event_id",
            "created_at",
            "updated_at",
            # PR14: Campos GCal são gerenciados pelo sistema
            "gcal_status",
            "gcal_last_sync_at",
            "gcal_last_error",
            # gcal_payload_hash removed: internal implementation detail
            # PR19/RF06: Google Meet link (gerado automaticamente)
            "meet_link",
        ]

    def get_fluxo(self, obj: Solicitacao) -> str:
        """Retorna fluxo do projeto (SUPER ou NAO_SUPER), fallback para NAO_SUPER."""
        if obj.projeto:
            return obj.projeto.fluxo
        return "NAO_SUPER"  # PR15: Fallback para solicitações sem projeto

    def get_usuario_username(self, obj: Solicitacao) -> str | None:
        """Retorna username do usuário que criou a solicitação."""
        if obj.usuario:
            return obj.usuario.username
        return None

    def get_coordenador_username(self, obj: Solicitacao) -> str | None:
        """
        Retorna username do coordenador.
        Prioriza: coordenador field -> usuario (fallback para ETL imports).
        """
        if obj.coordenador:
            return obj.coordenador.username
        # Fallback: Se coordenador não foi preenchido, usa usuario
        # (para eventos importados via ETL onde usuario = coordenador resolvido)
        if obj.usuario:
            return obj.usuario.username
        return None

    def get_coordenador_nome(self, obj: Solicitacao) -> str | None:
        """
        Retorna nome completo do coordenador (first_name + last_name).
        Prioriza: coordenador field -> usuario (fallback para ETL imports).
        """
        user = obj.coordenador or obj.usuario
        if user:
            nome = f"{user.first_name} {user.last_name}".strip()
            return nome if nome else user.username
        return None

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Validações para criação e edição de solicitações.

        Regras:
        1. Permite PATCH parcial: se apenas um dos campos vier no payload,
           usa o valor atual da instância para validar o intervalo.
        2. Bloqueia edição de solicitações já publicadas no Google Calendar
           (gcal_status == 'PUBLISHED') para evitar drift.
        3. Bloqueia edição de solicitações reprovadas.
        """
        instance = getattr(self, "instance", None)

        # Regra 2: Bloquear edição após publicação no GCal
        if instance is not None:
            if getattr(instance, "gcal_status", None) == "PUBLISHED":
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Não é possível editar uma solicitação já publicada no Google Calendar. "
                            "Cancele o evento primeiro se precisar fazer alterações."
                        ]
                    }
                )

            # Regra 3: Bloquear edição de solicitações reprovadas
            if getattr(instance, "status", None) == "reprovado":
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Não é possível editar uma solicitação reprovada. "
                            "Crie uma nova solicitação se necessário."
                        ]
                    }
                )

        # Regra 1: Validação de intervalo (fim > inicio)
        inicio = attrs.get("inicio", getattr(instance, "inicio", None))
        fim = attrs.get("fim", getattr(instance, "fim", None))

        # só valida se os dois forem conhecidos
        if inicio is not None and fim is not None:
            if fim <= inicio:
                raise serializers.ValidationError({"fim": "O fim do evento deve ser posterior ao início."})

        return super().validate(attrs)


# ================================================================
# Issue #98 - Event Detail with AuditLog Timeline
# ================================================================


class AuditLogTimelineSerializer(serializers.ModelSerializer):
    """
    Serializer para AuditLog na timeline de eventos.

    Expõe apenas campos relevantes para exibição no Drawer:
    - id, action, details, created_at
    - usuario (nome completo ou "Sistema")

    Usado em EventDetailSerializer para timeline.
    """

    usuario_nome = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "usuario_nome",
            "details",
            "created_at",
        ]
        read_only_fields = fields

    def get_usuario_nome(self, obj: AuditLog) -> str:
        """Retorna nome do usuário ou 'Sistema' se null."""
        if obj.usuario:
            full_name = obj.usuario.get_full_name()
            return full_name if full_name.strip() else obj.usuario.username
        return "Sistema"


class EventDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalhes completos de um evento GCal (Issue #98).

    Campos expostos:
    - Dados do evento: id, municipio_nome, projeto_nome, tipo_evento_nome,
      inicio, fim, usuario_username, coordenador_username, fluxo
    - Dados GCal: gcal_status, external_event_id, gcal_last_sync_at,
      gcal_last_error, meet_link, updated_at
    - participations: Lista de participantes (read-only)
    - timeline: Últimos 20 AuditLog relacionados (actions GCal), ordenado desc

    Note: gcal_payload_hash removed (internal implementation detail)

    Permissions: IsControleOrSuper
    Endpoint: GET /api/gcal/dashboard/events/{id}/detail/
    """

    # Campos legíveis (nomes em vez de IDs)
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    tipo_evento_nome = serializers.CharField(source="tipo_evento.nome", read_only=True)
    usuario_username = serializers.SerializerMethodField()
    coordenador_username = serializers.SerializerMethodField()
    fluxo = serializers.SerializerMethodField()

    # Participations (aninhado)
    participations = ParticipationNestedSerializer(many=True, read_only=True)

    # Timeline de AuditLog (últimos 20, ordenado desc)
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = Solicitacao
        fields = [
            "id",
            "municipio_nome",
            "projeto_nome",
            "tipo_evento_nome",
            "inicio",
            "fim",
            "usuario_username",
            "coordenador_username",
            "fluxo",
            "gcal_status",
            "external_event_id",
            "gcal_last_sync_at",
            "gcal_last_error",
            "meet_link",
            # gcal_payload_hash removed: internal implementation detail
            "updated_at",
            "participations",
            "timeline",
        ]
        read_only_fields = fields

    def get_usuario_username(self, obj: Solicitacao) -> str | None:
        """Retorna username do usuário que criou a solicitação."""
        return obj.usuario.username if obj.usuario else None

    def get_coordenador_username(self, obj: Solicitacao) -> str | None:
        """Retorna username do coordenador (ou usuario se coordenador null)."""
        if obj.coordenador:
            return obj.coordenador.username
        if obj.usuario:
            return obj.usuario.username
        return None

    def get_fluxo(self, obj: Solicitacao) -> str:
        """Retorna fluxo do projeto (SUPER ou NAO_SUPER)."""
        return obj.projeto.fluxo if obj.projeto else "NAO_SUPER"

    def get_timeline(self, obj: Solicitacao) -> list[dict[str, Any]]:
        """
        Retorna últimos 20 AuditLog relacionados ao evento.

        Filtro por actions GCal relevantes:
        - PUBLISH_GCAL_REQUESTED
        - PUBLISH_GCAL
        - PUBLISH_GCAL_ERROR
        - CANCEL_GCAL
        - CANCEL_GCAL_REQUESTED
        - RESYNC_GCAL_REQUESTED
        - GOOGLE_CONNECT
        - GOOGLE_DISCONNECT
        - GOOGLE_REFRESH_TOKEN

        Ordenado por created_at desc (mais recentes primeiro).
        Limite: 20 registros.
        """
        # Ações GCal relevantes para timeline
        gcal_actions = [
            "PUBLISH_GCAL_REQUESTED",
            "PUBLISH_GCAL",
            "PUBLISH_GCAL_ERROR",
            "CANCEL_GCAL",
            "CANCEL_GCAL_REQUESTED",
            "RESYNC_GCAL_REQUESTED",
            "GOOGLE_CONNECT",
            "GOOGLE_DISCONNECT",
            "GOOGLE_REFRESH_TOKEN",
        ]

        # Buscar logs relacionados ao evento (via details.solicitacao_id ou model_name)
        logs = (
            AuditLog.objects.filter(action__in=gcal_actions, details__solicitacao_id=obj.id)
            .select_related("usuario")
            .order_by("-created_at")[:20]
        )

        # Serializar
        return AuditLogTimelineSerializer(logs, many=True).data
