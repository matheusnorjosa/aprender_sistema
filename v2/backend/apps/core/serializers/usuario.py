"""
AS v2 — Usuario Serializers

Serializers para Usuario e Group.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.constants import RESERVED_GROUPS
from apps.core.models import PermissaoFuncional


class UserSlimSerializer(serializers.ModelSerializer):
    """
    Serializer slim para Usuario (usado em aninhamentos).
    Retorna apenas id, nome e email.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "first_name", "last_name", "email")


class CurrentUserSerializer(serializers.Serializer):  # type: ignore[misc]
    """
    Response serializer for authenticated user payload (/api/me/).
    """

    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, required=False)
    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    name = serializers.CharField()
    groups = serializers.ListField(child=serializers.CharField())
    setores = serializers.ListField(child=serializers.CharField())
    funcoes = serializers.ListField(child=serializers.CharField())
    is_superuser = serializers.BooleanField()
    is_superintendencia = serializers.BooleanField()
    can_approve_super = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())


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
    - is_staff remains read-only
    - Groups whitelist: DAT, Controle, Superintendência, Coordenador, Formador, Gerência
    - Users cannot modify their own groups

    RBAC funcional (Issue #829):
    - is_superuser é editável apenas por superuser
    - auto-demotion de superuser é bloqueada
    - último superuser ativo é protegido

    API Design:
    - groups (read-only): Retorna nomes dos grupos (ex: ["DAT", "Coordenador"])
    - group_ids (write-only): Aceita IDs dos grupos para escrita
    """

    # Read-only: retorna nomes dos grupos para a API/frontend
    groups = serializers.StringRelatedField(many=True, read_only=True)

    # Read-only: retorna IDs dos grupos para edição no frontend
    group_ids_display = serializers.SerializerMethodField()

    # Write-only: aceita IDs dos grupos para criar/atualizar (P1.1)
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        allow_empty=True,
        write_only=True,
        source="groups",  # Maps to the same field in the model
    )

    password = serializers.CharField(write_only=True, required=False)

    # CPF mascarado para list views (LGPD compliance)
    cpf_masked = serializers.SerializerMethodField()

    def get_group_ids_display(self, obj: Any) -> list[int]:
        """Return group IDs for frontend editing."""
        return [g.id for g in obj.groups.all()]

    def get_cpf_masked(self, obj: Any) -> str | None:
        """
        Return masked CPF for LGPD compliance.

        Format: ***.***XXX-XX (shows only last 6 digits)
        """
        cpf = getattr(obj, "cpf", None)
        if not cpf or len(cpf) < 6:
            return cpf
        # Keep only last 6 characters visible
        return f"***.***.{cpf[-6:]}"

    # Whitelist of allowed groups (P1.1) - configurável via settings (Issue #254)
    # Fallback para set vazio se não configurado (todos os grupos bloqueados)
    ALLOWED_GROUPS: set[str] = set(getattr(settings, "ALLOWED_USER_GROUPS", set()))

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "cpf",  # Full CPF (write-only for create/update)
            "cpf_masked",  # Masked CPF for display (LGPD)
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",  # Read-only (nomes)
            "group_ids",  # Write-only (IDs para criar/editar)
            "group_ids_display",  # Read-only (IDs para popular form de edição)
            "date_joined",
            "last_login",
        ]
        # P1.1: is_staff permanece read-only
        # LGPD: CPF is write-only (use cpf_masked for display)
        read_only_fields = ["id", "date_joined", "last_login", "is_staff"]
        extra_kwargs = {
            "password": {"write_only": True},
            "cpf": {"write_only": True},  # LGPD: don't expose full CPF in responses
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Regras de segurança para operações sensíveis de admin.
        """
        attrs = super().validate(attrs)
        attrs_typed = cast(dict[str, object], attrs)

        request: Any = self.context.get("request")
        request_user: Any = getattr(request, "user", None)
        instance: Any = self.instance

        current_is_superuser = bool(getattr(instance, "is_superuser", False)) if instance is not None else False
        current_is_active = bool(getattr(instance, "is_active", True)) if instance is not None else True
        target_is_superuser = (
            bool(attrs_typed["is_superuser"]) if "is_superuser" in attrs_typed else current_is_superuser
        )
        target_is_active = bool(attrs_typed["is_active"]) if "is_active" in attrs_typed else current_is_active
        incoming_is_superuser = "is_superuser" in attrs_typed

        # Apenas superuser pode alterar is_superuser.
        if incoming_is_superuser and (not request_user or not getattr(request_user, "is_superuser", False)):
            raise serializers.ValidationError(
                {"is_superuser": "Apenas superusuários podem alterar o campo is_superuser."}
            )

        if instance and getattr(instance, "is_superuser", False):
            # Bloqueia auto-demotion de superuser.
            if (
                request_user
                and getattr(request_user, "id", None) == getattr(instance, "id", None)
                and incoming_is_superuser
                and not target_is_superuser
            ):
                raise serializers.ValidationError(
                    {"is_superuser": "Você não pode remover seu próprio privilégio de superusuário."}
                )

            # Protege o último superuser ativo.
            removing_superuser = getattr(instance, "is_superuser", False) and not target_is_superuser
            deactivating_superuser = getattr(instance, "is_superuser", False) and not target_is_active
            if removing_superuser or deactivating_superuser:
                UserModel = get_user_model()
                has_other_active_superuser = (
                    UserModel.objects.filter(is_superuser=True, is_active=True).exclude(pk=instance.pk).exists()
                )
                if not has_other_active_superuser:
                    message = "Não é possível remover ou desativar o último superusuário ativo."
                    if removing_superuser:
                        raise serializers.ValidationError({"is_superuser": message})
                    raise serializers.ValidationError({"is_active": message})

        return attrs

    def validate_group_ids(self, value: list[Group]) -> list[Group]:
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
            raise serializers.ValidationError("Você não pode modificar seus próprios grupos.")

        # Validate groups against whitelist (P1.1)
        for group in value:
            if group.name not in self.ALLOWED_GROUPS:
                allowed_list = ", ".join(sorted(self.ALLOWED_GROUPS))
                raise serializers.ValidationError(f"Grupo '{group.name}' não permitido. Grupos válidos: {allowed_list}")

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
                raise serializers.ValidationError("A senha deve ter no mínimo 8 caracteres.")

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
    permissoes_funcionais = serializers.SerializerMethodField(read_only=True)
    permissao_funcional_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=PermissaoFuncional.objects.all(),
        required=False,
        allow_empty=True,
        write_only=True,
        source="permissoes_funcionais",
    )

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "permissions",
            "user_count",
            "permissoes_funcionais",
            "permissao_funcional_ids",
        ]
        read_only_fields = ["id", "permissions", "user_count"]

    def get_permissions(self, obj: Group) -> list[str]:
        """Return list of permission codenames."""
        return [f"{p.content_type.app_label}.{p.codename}" for p in obj.permissions.all()]

    def get_user_count(self, obj: Group) -> int:
        """Return count of users in this group."""
        return obj.user_set.count()

    def get_permissoes_funcionais(self, obj: Group) -> list[dict[str, Any]]:
        return [
            {
                "id": permissao.id,
                "codename": permissao.codename,
                "label": permissao.label,
                "category": permissao.category,
            }
            for permissao in obj.permissoes_funcionais.all().order_by("category", "label")
        ]

    def validate_name(self, value: str) -> str:
        instance = self.instance
        if instance and instance.name in RESERVED_GROUPS and value != instance.name:
            request: Any = self.context.get("request")
            confirmed = False
            if request is not None:
                confirmed = str(request.query_params.get("confirm_reserved", "")).lower() == "true"
            if not confirmed:
                raise serializers.ValidationError(
                    "Grupo reservado. Para renomear, use ?confirm_reserved=true na requisição."
                )
        return value

    def create(self, validated_data: dict[str, Any]) -> Group:
        permissoes_funcionais = validated_data.pop("permissoes_funcionais", [])
        instance = super().create(validated_data)
        if permissoes_funcionais:
            instance.permissoes_funcionais.set(permissoes_funcionais)
        return instance

    def update(self, instance: Group, validated_data: dict[str, Any]) -> Group:
        permissoes_funcionais = validated_data.pop("permissoes_funcionais", None)
        instance = super().update(instance, validated_data)
        if permissoes_funcionais is not None:
            instance.permissoes_funcionais.set(permissoes_funcionais)
        return instance


class PermissaoFuncionalSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PermissaoFuncional
        fields = [
            "id",
            "codename",
            "label",
            "description",
            "category",
            "is_system",
            "groups",
        ]
        read_only_fields = fields

    def get_groups(self, obj: PermissaoFuncional) -> list[dict[str, Any]]:
        return [{"id": group.id, "name": group.name} for group in obj.groups.all().order_by("name")]
