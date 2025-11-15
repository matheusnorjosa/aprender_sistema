"""
DRF Serializers for Core models
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers  # type: ignore[attr-defined]

from .models import (
    AcaoControle,
    AcaoDAT,
    AuditLog,
    AvailabilityBlock,
    Compra,
    Municipio,
    Participation,
    Produto,
    Projeto,
    Solicitacao,
    TipoEvento,
)


class UserSlimSerializer(serializers.ModelSerializer):
    """
    Serializer slim para Usuario (usado em aninhamentos).
    Retorna apenas id, nome e email.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "first_name", "last_name", "email")


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

    participations = ParticipationNestedSerializer(
        many=True, read_only=True
    )
    fluxo = serializers.SerializerMethodField()

    # Campos legíveis para exibição (além dos IDs)
    usuario_username = serializers.SerializerMethodField()
    coordenador_username = serializers.SerializerMethodField()
    municipio_nome = serializers.CharField(source='municipio.nome', read_only=True)
    projeto_nome = serializers.CharField(source='projeto.nome', read_only=True)
    tipo_evento_nome = serializers.CharField(source='tipo_evento.nome', read_only=True)

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
            "inicio",
            "fim",
            "status",
            "observacoes",
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
            "gcal_payload_hash",
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
            "gcal_payload_hash",
            # PR19/RF06: Google Meet link (gerado automaticamente)
            "meet_link",
        ]

    def get_fluxo(self, obj: Solicitacao) -> str:
        """Retorna fluxo do projeto (SUPER ou NAO_SUPER), fallback para NAO_SUPER."""
        if obj.projeto:
            return obj.projeto.fluxo
        return 'NAO_SUPER'  # PR15: Fallback para solicitações sem projeto

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

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Permite PATCH parcial: se apenas um dos campos vier no payload,
        usa o valor atual da instância para validar o intervalo.
        """
        instance = getattr(self, "instance", None)
        inicio = attrs.get("inicio", getattr(instance, "inicio", None))
        fim = attrs.get("fim", getattr(instance, "fim", None))

        # só valida se os dois forem conhecidos
        if inicio is not None and fim is not None:
            if fim <= inicio:
                raise serializers.ValidationError(
                    {"fim": "O fim do evento deve ser posterior ao início."}
                )

        return super().validate(attrs)


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    """
    Serializer for AvailabilityBlock model.

    Status é auto-aprovado no ViewSet.perform_create().
    Usuario é preenchido automaticamente com request.user no ViewSet.
    """

    class Meta:
        model = AvailabilityBlock
        fields = [
            "id",
            "usuario",
            "inicio",
            "fim",
            "tipo",
            "motivo",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "usuario", "status", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Aceita updates parciais sem estourar KeyError.
        """
        instance = getattr(self, "instance", None)
        inicio = attrs.get("inicio", getattr(instance, "inicio", None))
        fim = attrs.get("fim", getattr(instance, "fim", None))

        if inicio is not None and fim is not None:
            if fim <= inicio:
                raise serializers.ValidationError(
                    {"fim": "O fim do bloqueio deve ser posterior ao início."}
                )

        return super().validate(attrs)


class ProdutoSerializer(serializers.ModelSerializer["Produto"]):
    """
    Serializer para modelo Produto.
    """

    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)

    class Meta:
        model = Produto
        fields = [
            "id",
            "codigo",
            "nome",
            "descricao",
            "projeto",
            "projeto_nome",
            "ativo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CompraSerializer(serializers.ModelSerializer):
    """
    Serializer for Compra model (basic CRUD).
    Includes nested fields from Produto FK.
    """

    produto_codigo = serializers.CharField(source="produto.codigo", read_only=True, allow_null=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, allow_null=True)

    class Meta:
        model = Compra
        fields = [
            "id",
            "codigo",  # DEPRECATED: Use produto FK
            "produto",
            "produto_codigo",
            "produto_nome",
            "projeto",
            "municipio",
            "quantidade",
            "data",
            "uso",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_quantidade(self, value: int) -> int:
        """Quantidade não pode ser negativa."""
        if value < 0:
            raise serializers.ValidationError("Quantidade não pode ser negativa.")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for AuditLog model (read-only).
    PA-05: Usado para rastrear aprovações/reprovações.
    """

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "usuario",
            "action",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "usuario", "action", "details", "created_at"]


class AcaoControleSerializer(serializers.ModelSerializer):
    """
    Serializer for AcaoControle model (read operations).
    Uses StringRelatedField for readable FK representation.
    """

    municipio = serializers.StringRelatedField()
    projeto = serializers.StringRelatedField()
    coordenador = serializers.StringRelatedField()

    class Meta:
        model = AcaoControle
        fields = [
            "id",
            "municipio",
            "projeto",
            "coordenador",
            "data_entrega",
            "data_carta",
            "contato_inicial",
            "data_reuniao",
            "observacao",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]


class AcaoDATSerializer(serializers.ModelSerializer):
    """
    Serializer for AcaoDAT model (read operations).
    Uses StringRelatedField for readable FK representation.
    """

    municipio = serializers.StringRelatedField()
    projeto = serializers.StringRelatedField()
    responsavel = serializers.StringRelatedField()

    class Meta:
        model = AcaoDAT
        fields = [
            "id",
            "municipio",
            "projeto",
            "tipo_acao",
            "responsavel",
            "observacao",
            "data_registro",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]


class AcaoDATCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for AcaoDAT model (write operations).
    Uses native ForeignKey IDs for creation.
    """

    class Meta:
        model = AcaoDAT
        fields = [
            "id",
            "municipio",
            "projeto",
            "tipo_acao",
            "responsavel",
            "observacao",
            "data_registro",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]


class MunicipioSerializer(serializers.ModelSerializer):
    """
    Full serializer for Municipio model (Admin CRUD).
    """

    class Meta:
        model = Municipio
        fields = ["id", "nome", "uf", "ibge_code", "ativo"]
        read_only_fields = ["id"]


class MunicipioOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Municipio (dropdowns/selects).
    """

    class Meta:
        model = Municipio
        fields = ["id", "nome", "uf"]


class ProjetoSerializer(serializers.ModelSerializer):
    """
    Full serializer for Projeto model (Admin CRUD).
    """

    class Meta:
        model = Projeto
        fields = ["id", "nome", "codigo", "fluxo", "ativo"]
        read_only_fields = ["id"]


class ProjetoOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Projeto (dropdowns/selects).
    """

    class Meta:
        model = Projeto
        fields = ["id", "nome", "codigo"]


class TipoEventoOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for TipoEvento (dropdowns/selects).
    """

    class Meta:
        model = TipoEvento
        fields = ["id", "nome"]


class UsuarioOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Usuario (dropdowns/selects).
    """

    class Meta:
        model = get_user_model()
        fields = ["id", "first_name", "last_name", "email"]


class UsuarioAdminSerializer(serializers.ModelSerializer):
    """
    Full serializer for Usuario (Admin CRUD).
    Includes groups and permissions for DAT admin operations.

    P1.1 Security Hardening:
    - is_staff and is_superuser are read-only
    - Groups whitelist: DAT, Controle, Superintendência, Coordenador, Formador, Gerência
    - Users cannot modify their own groups

    API Design:
    - groups (read-only): Retorna nomes dos grupos (ex: ["DAT", "Coordenador"])
    - group_ids (write-only): Aceita IDs dos grupos para escrita
    """

    # Read-only: retorna nomes dos grupos para a API/frontend
    groups = serializers.StringRelatedField(many=True, read_only=True)

    # Write-only: aceita IDs dos grupos para criar/atualizar (P1.1)
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        allow_empty=True,
        write_only=True,
        source='groups'  # Maps to the same field in the model
    )

    password = serializers.CharField(write_only=True, required=False)

    # Whitelist of allowed groups (P1.1) - incluindo Gerência
    ALLOWED_GROUPS = {"DAT", "Controle", "Superintendência", "Coordenador", "Formador", "Gerência"}

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "cpf",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",       # Read-only (nomes)
            "group_ids",    # Write-only (IDs)
            "date_joined",
            "last_login",
        ]
        # P1.1: is_staff and is_superuser are read-only
        read_only_fields = ["id", "date_joined", "last_login", "is_staff", "is_superuser"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate_group_ids(self, value: list[int]) -> list[int]:
        """
        P1.1: Validate group_ids against whitelist and self-modification.

        Rules:
        - Only groups in ALLOWED_GROUPS can be assigned
        - Users cannot modify their own groups
        """
        request = self.context.get("request")
        instance = self.instance  # None for create, User object for update

        # Check if user is trying to modify their own groups (P1.1)
        if instance and request and instance.id == request.user.id:
            raise serializers.ValidationError(
                "Você não pode modificar seus próprios grupos."
            )

        # Validate groups against whitelist (P1.1)
        for group in value:
            if group.name not in self.ALLOWED_GROUPS:
                allowed_list = ", ".join(sorted(self.ALLOWED_GROUPS))
                raise serializers.ValidationError(
                    f"Grupo '{group.name}' não permitido. Grupos válidos: {allowed_list}"
                )

        return value

    def create(self, validated_data: dict[str, Any]) -> Any:
        """Create user with hashed password and groups."""
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password", None)

        user = super().create(validated_data)

        if password:
            user.set_password(password)
            user.save()

        # Assign groups after user creation
        if groups:
            user.groups.set(groups)

        return user

    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        """Update user and hash password if provided."""
        groups = validated_data.pop("groups", None)
        password = validated_data.pop("password", None)

        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        # Update groups if provided (P1.1 validation already applied)
        if groups is not None:
            user.groups.set(groups)

        return user

    def validate_password(self, value: str) -> str:
        """
        Validate password using Django's password validators.
        Enforces minimum length of 8 characters and Django's AUTH_PASSWORD_VALIDATORS.
        """
        if value:
            # Minimum length check
            if len(value) < 8:
                raise serializers.ValidationError(
                    "A senha deve ter no mínimo 8 caracteres."
                )

            # Use Django's validate_password for consistent policy
            try:
                validate_password(value)
            except ValidationError as e:
                raise serializers.ValidationError(list(e.messages))

        return value


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Django Group model (Admin CRUD).

    Used by Admin DAT for managing user groups/sectors.
    GAP-002 (resolved): Created in Phase 1 Iteration 2.
    """

    permissions = serializers.SerializerMethodField(read_only=True)
    user_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "user_count"]
        read_only_fields = ["id", "permissions", "user_count"]

    def get_permissions(self, obj: Group) -> list[str]:
        """Return list of permission codenames."""
        return [f"{p.content_type.app_label}.{p.codename}" for p in obj.permissions.all()]

    def get_user_count(self, obj: Group) -> int:
        """Return count of users in this group."""
        return obj.user_set.count()


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
      gcal_last_error, meet_link, gcal_payload_hash, updated_at
    - participations: Lista de participantes (read-only)
    - timeline: Últimos 20 AuditLog relacionados (actions GCal), ordenado desc

    Permissions: IsControleOrSuper
    Endpoint: GET /api/gcal/dashboard/events/{id}/detail/
    """

    # Campos legíveis (nomes em vez de IDs)
    municipio_nome = serializers.CharField(source='municipio.nome', read_only=True)
    projeto_nome = serializers.CharField(source='projeto.nome', read_only=True)
    tipo_evento_nome = serializers.CharField(source='tipo_evento.nome', read_only=True)
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
            "gcal_payload_hash",
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
        return obj.projeto.fluxo if obj.projeto else 'NAO_SUPER'

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
            'PUBLISH_GCAL_REQUESTED',
            'PUBLISH_GCAL',
            'PUBLISH_GCAL_ERROR',
            'CANCEL_GCAL',
            'CANCEL_GCAL_REQUESTED',
            'RESYNC_GCAL_REQUESTED',
            'GOOGLE_CONNECT',
            'GOOGLE_DISCONNECT',
            'GOOGLE_REFRESH_TOKEN',
        ]

        # Buscar logs relacionados ao evento (via details.solicitacao_id ou model_name)
        logs = AuditLog.objects.filter(
            action__in=gcal_actions,
            details__solicitacao_id=obj.id
        ).select_related('usuario').order_by('-created_at')[:20]

        # Serializar
        return AuditLogTimelineSerializer(logs, many=True).data
