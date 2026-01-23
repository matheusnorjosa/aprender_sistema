"""
AS v2 — Usuario Serializers

Serializers para Usuario e Group.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers  # type: ignore[attr-defined]


class UserSlimSerializer(serializers.ModelSerializer):
    """
    Serializer slim para Usuario (usado em aninhamentos).
    Retorna apenas id, nome e email.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "first_name", "last_name", "email")


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
    ALLOWED_GROUPS: set[str] = getattr(settings, "ALLOWED_USER_GROUPS", set())

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
        # P1.1: is_staff and is_superuser are read-only
        # LGPD: CPF is write-only (use cpf_masked for display)
        read_only_fields = ["id", "date_joined", "last_login", "is_staff", "is_superuser"]
        extra_kwargs = {
            "password": {"write_only": True},
            "cpf": {"write_only": True},  # LGPD: don't expose full CPF in responses
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
