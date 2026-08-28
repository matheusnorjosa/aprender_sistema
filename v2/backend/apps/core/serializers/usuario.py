"""
AS v2 — Usuario Serializers

Serializers para Usuario e Group.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.constants import FUNCAO_GROUPS, RESERVED_GROUPS, SETOR_GROUPS
from apps.core.models import AuditLog, GroupClassificacao, PermissaoFuncional
from apps.core.rbac import can_admin_mutate_target
from apps.core.services.audit import (
    auditar_assign_groups,
    auditar_group_capabilities_set,
    auditar_privilege_flags,
    auditar_reset_senha,
    registrar_auditoria,
)
from apps.core.services.rbac_service import get_assignable_group_names


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
    # LGPD art. 18-II (acesso): o titular confirma os proprios dados de cadastro.
    cpf = serializers.CharField()
    telefone = serializers.CharField(allow_blank=True, required=False)
    cargo = serializers.CharField(allow_blank=True, required=False)
    groups = serializers.ListField(child=serializers.CharField())
    setores = serializers.ListField(child=serializers.CharField())
    funcoes = serializers.ListField(child=serializers.CharField())
    is_superuser = serializers.BooleanField()
    is_superintendencia = serializers.BooleanField()
    can_approve_super = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())


class MeContactUpdateSerializer(serializers.Serializer):  # type: ignore[misc]
    """PATCH /api/me/ — autocorreção de contato pelo titular (LGPD art. 18-III).

    Apenas `telefone` é autocorrigível. Identidade (cpf), organização (cargo, groups)
    e privilégio (is_superuser/is_staff) ficam de fora: são dados que o titular não
    define sozinho. Campos não declarados aqui são simplesmente ignorados no PATCH.
    """

    telefone = serializers.CharField(max_length=20, allow_blank=True, trim_whitespace=True)


class UsuarioOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Usuario (dropdowns/selects).
    SEC-ENUM-01: email removed to prevent user enumeration.
    """

    class Meta:
        model = get_user_model()
        fields = ["id", "first_name", "last_name"]


class UsuarioAdminSerializer(serializers.ModelSerializer):
    """
    Full serializer for Usuario (Admin CRUD).
    Includes groups and permissions for DAT admin operations.

    P1.1 Security Hardening:
    - is_staff remains read-only
    - Groups whitelist: dynamic (SETOR_GROUPS + FUNCAO_GROUPS + functional permissions)
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

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "telefone",
            "cargo",
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

        # P0-0 (Tier-0, auditoria 2026-07-17): um não-superuser nunca altera uma
        # conta que já é superuser. Defense-in-depth — a queryset de
        # `UsuarioAdminViewSet` já retorna 404 antes daqui; esta checagem
        # protege qualquer reuso futuro do serializer fora daquela view.
        if (
            instance is not None
            and getattr(instance, "is_superuser", False)
            and not (request_user and getattr(request_user, "is_superuser", False))
        ):
            raise serializers.ValidationError(
                {"detail": "Você não tem permissão para alterar uma conta de superusuário."}
            )

        # M07-01/M07-02 (#1616/#1617): defense-in-depth ator×alvo — um não-superuser
        # não muta conta APROVADORA (tomar a conta viabiliza auto-aprovação de
        # solicitações, violando CP-02). A view (`UsuarioAdminViewSet.get_object`)
        # já barra com 403 antes daqui; esta checagem protege reuso do serializer
        # fora daquela view. SSOT: `can_admin_mutate_target`.
        if instance is not None and request_user is not None and not can_admin_mutate_target(request_user, instance):
            raise serializers.ValidationError({"detail": "Você não tem permissão para alterar esta conta."})

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

        allowed_groups = get_assignable_group_names()

        # Validate groups against dynamic whitelist (P1.1/#832)
        for group in value:
            if group.name not in allowed_groups:
                allowed_list = ", ".join(sorted(allowed_groups))
                raise serializers.ValidationError(f"Grupo '{group.name}' não permitido. Grupos válidos: {allowed_list}")

        return value

    def _actor_is_superuser(self) -> bool:
        request: Any = self.context.get("request")
        actor: Any = getattr(request, "user", None)
        return bool(actor and getattr(actor, "is_superuser", False))

    def _actor(self) -> Any:
        return getattr(self.context.get("request"), "user", None)

    def create(self, validated_data: dict[str, Any]) -> Any:
        """Create user with hashed password and groups."""
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password", None)

        user = super().create(validated_data)
        actor = self._actor()

        # M07-03 (#1618): a criacao e a concessao inicial de flags auditam igual ao
        # Django Admin (antes o path REST so auditava senha e grupos).
        registrar_auditoria(
            actor=actor,
            action=AuditLog.Action.CREATE,
            model_name="Usuario",
            details={"target_user_id": user.pk, "target_username": user.username},
        )
        auditar_privilege_flags(actor=actor, target_user=user, before=None, via="rest_api")

        if password:
            user.set_password(password)
            user.save()
            # #1672: senha definida por um admin para outro usuario -> trilha.
            auditar_reset_senha(actor=actor, target_user=user, contexto="create")

        # P0-1 Tier-0 (D-1=2a): membership é superuser-only. group_ids de
        # não-superuser é ignorado (o frontend já não envia — aqui é a
        # fronteira real). DAT cria a conta comum; o vínculo a grupo fica a
        # cargo do superuser.
        if groups and self._actor_is_superuser():
            user.groups.set(groups)
            # #1672: atribuicao de grupos (privilegio) auditada.
            auditar_assign_groups(
                actor=actor,
                target_user=user,
                before_group_ids=[],
                after_group_ids=list(user.groups.values_list("pk", flat=True)),
            )

        return user

    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        """Update user and hash password if provided."""
        groups = validated_data.pop("groups", None)
        password = validated_data.pop("password", None)
        actor = self._actor()
        before_group_ids = set(instance.groups.values_list("pk", flat=True))
        # M07-03 (#1618): snapshot dos flags ANTES do super().update (DRF muta a instance
        # in-place — ler depois daria before==after e nada auditaria).
        before_flags = {f: bool(getattr(instance, f)) for f in ("is_superuser", "is_staff", "is_active")}
        cadastral_keys = sorted(k for k in validated_data if k not in ("is_superuser", "is_staff", "is_active"))

        user = super().update(instance, validated_data)

        # #1894: desativação decidida NO SISTEMA (admin) é LOCAL -> marca `desativado_localmente`
        # para o import never-reactivate (o import nunca liga False->True com a flag). Reativar
        # (ação humana) limpa a flag. Reage só à TRANSIÇÃO real de is_active.
        was_active = before_flags["is_active"]
        if was_active and not user.is_active and not user.desativado_localmente:
            user.desativado_localmente = True
            user.save(update_fields=["desativado_localmente"])
        elif not was_active and user.is_active and user.desativado_localmente:
            user.desativado_localmente = False
            user.save(update_fields=["desativado_localmente"])

        # M07-03: flip de privilegio via REST (activate/deactivate/promote) audita igual ao Admin.
        auditar_privilege_flags(actor=actor, target_user=user, before=before_flags, via="rest_api")
        # M07-03: alteracao cadastral — so os NOMES dos campos escritos (nunca valores/PII).
        if cadastral_keys:
            registrar_auditoria(
                actor=actor,
                action=AuditLog.Action.UPDATE,
                model_name="Usuario",
                details={"target_user_id": user.pk, "target_username": user.username, "campos": cadastral_keys},
            )

        if password:
            user.set_password(password)
            user.save()
            # #1672: senha redefinida por um admin para outro usuario -> trilha.
            auditar_reset_senha(actor=actor, target_user=user, contexto="update")

        # P0-1 Tier-0 (D-1=2a): membership é superuser-only (ver create()).
        # group_ids de não-superuser é ignorado.
        if groups is not None and self._actor_is_superuser():
            user.groups.set(groups)
            # #1672: mudanca de membership (privilegio) auditada.
            auditar_assign_groups(
                actor=actor,
                target_user=user,
                before_group_ids=before_group_ids,
                after_group_ids=set(user.groups.values_list("pk", flat=True)),
            )

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


class ChangePasswordSerializer(serializers.Serializer):
    """Troca de senha self-service (POST /api/me/change-password/).

    Valida a senha atual (``check_password`` do usuario no contexto) e a nova senha
    com os validadores do Django (``AUTH_PASSWORD_VALIDATORS``), reusando o mesmo
    padrao de ``UsuarioAdminSerializer.validate_password``. NAO persiste — a view chama
    ``set_password`` + ``update_session_auth_hash``.
    """

    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        if len(value) < 8:
            raise serializers.ValidationError("A senha deve ter no minimo 8 caracteres.")
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request = self.context.get("request")
        user = request.user if request is not None else None
        if user is None or not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Senha atual incorreta."})
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "A nova senha deve ser diferente da senha atual."})
        return attrs


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Django Group model (Admin CRUD).

    Used by Admin DAT for managing user groups/sectors.
    GAP-002 (resolved): Created in Phase 1 Iteration 2.
    """

    permissions = serializers.SerializerMethodField(read_only=True)
    user_count = serializers.SerializerMethodField(read_only=True)
    permissoes_funcionais = serializers.SerializerMethodField(read_only=True)
    group_type = serializers.SerializerMethodField(read_only=True)
    group_type_input = serializers.ChoiceField(
        choices=GroupClassificacao.Tipo.choices,
        required=False,
        allow_null=True,
        write_only=True,
    )
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
            "group_type",
            "group_type_input",
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

    def get_group_type(self, obj: Group) -> str | None:
        classificacao = getattr(obj, "rbac_classificacao", None)
        if classificacao is not None:
            return cast(str, classificacao.tipo)
        if obj.name in SETOR_GROUPS:
            return GroupClassificacao.Tipo.SETOR
        if obj.name in FUNCAO_GROUPS:
            return GroupClassificacao.Tipo.FUNCAO
        return None

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

    def _actor(self) -> Any:
        return getattr(self.context.get("request"), "user", None)

    def create(self, validated_data: dict[str, Any]) -> Group:
        group_type = validated_data.pop("group_type_input", None)
        permissoes_funcionais = validated_data.pop("permissoes_funcionais", [])
        instance = super().create(validated_data)
        if group_type:
            GroupClassificacao.objects.update_or_create(group=instance, defaults={"tipo": group_type})
        if permissoes_funcionais:
            instance.permissoes_funcionais.set(permissoes_funcionais)
            # #1672: mudanca Group x Capability via REST tambem e auditada — este
            # e o path que antes perdia o registro por nao passar pelo Admin.
            auditar_group_capabilities_set(
                actor=self._actor(),
                group=instance,
                before_cap_ids=[],
                after_cap_ids=[c.pk for c in permissoes_funcionais],
            )
        return instance

    def update(self, instance: Group, validated_data: dict[str, Any]) -> Group:
        group_type = validated_data.pop("group_type_input", None)
        permissoes_funcionais = validated_data.pop("permissoes_funcionais", None)
        before_cap_ids = set(instance.permissoes_funcionais.values_list("pk", flat=True))
        instance = super().update(instance, validated_data)
        if group_type:
            GroupClassificacao.objects.update_or_create(group=instance, defaults={"tipo": group_type})
        if permissoes_funcionais is not None:
            instance.permissoes_funcionais.set(permissoes_funcionais)
            # #1672: idem — REST auditado (antes so o Admin persistia a trilha).
            auditar_group_capabilities_set(
                actor=self._actor(),
                group=instance,
                before_cap_ids=before_cap_ids,
                after_cap_ids=set(instance.permissoes_funcionais.values_list("pk", flat=True)),
            )
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
