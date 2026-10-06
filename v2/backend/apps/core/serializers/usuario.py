"""
AS v2 — Usuario Serializers

Serializers para Usuario e Group.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.constants import FUNCAO_GROUPS, RESERVED_GROUPS, SETOR_GROUPS
from apps.core.models import AuditLog, EquipeGerencia, Gerencia, GroupClassificacao, PermissaoFuncional
from apps.core.rbac import can_admin_mutate_target
from apps.core.rbac.policies import solicitation_approval_basis
from apps.core.services.audit import (
    auditar_assign_groups,
    auditar_group_capabilities_set,
    auditar_privilege_flags,
    auditar_reset_senha,
    registrar_auditoria,
)
from apps.core.services.equipe_gerencia import (
    PAPEL_EQUIPE,
    encerrar_gerente_aprovador,
    encerrar_lotacao,
    papeis_de_grupos,
    setor_group_for,
    sync_user_lotacao,
    tem_equipe_administrativa,
)
from apps.core.services.rbac_service import get_assignable_group_names, nomes_grupos_funcao

# Sentinela: distingue "campo não enviado" de "enviado como null" no PATCH parcial.
_UNSET: Any = object()


# #2071: par do composite LEGADO de aprovação (espelha `APPROVER_COMPOSITES`; sai no B2). O par
# Controle + Assistente Administrativo é base legítima e fica fora da trava.
_PAR_LEGADO: tuple[str, str] = ("Superintendência", "Gerente")


def _vinculo_exibido(user: Any) -> Any:
    """O vínculo vigente que o form de Usuários mostra (e reenvia no save): o primeiro por id, preferindo
    gerência ativa (senão um vínculo antigo em gerência desativada viraria a lotação editada).

    Prefere vínculo com escopo (papel de função); o EQUIPE só aparece quando é o único vigente.
    """
    for vigentes in (EquipeGerencia.vigentes_com_escopo_em, EquipeGerencia.vigentes_em):
        vinculo = vigentes().filter(usuario=user).select_related("gerencia").order_by("-gerencia__ativo", "id").first()
        if vinculo is not None:
            return vinculo
    return None


class UserSlimSerializer(serializers.ModelSerializer):
    """
    Serializer slim para Usuario (usado em aninhamentos).
    Retorna apenas id, nome e email.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "first_name", "last_name", "email")


class GerenciaVinculoSerializer(serializers.Serializer):  # type: ignore[misc]
    """Gerência em que o usuário tem vínculo vigente (item de `/api/me/.gerencias`)."""

    id = serializers.IntegerField()
    rotulo = serializers.CharField()
    papeis = serializers.ListField(child=serializers.CharField())


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
    # PR A: vínculos EquipeGerencia vigentes em gerência ativa (escolha de gerência na Grade).
    gerencias = GerenciaVinculoSerializer(many=True)
    is_superuser = serializers.BooleanField()
    is_superintendencia = serializers.BooleanField()
    can_approve_super = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())
    # Senha em uso foi definida por outra pessoa: a tela só mostra a troca de senha.
    deve_trocar_senha = serializers.BooleanField()


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

    # Lotação (EquipeGerencia): gerencia_id (write) cria/atualiza o vínculo de gerência
    # a partir da Gerência + Função; gerencia_atual (read) hidrata o form no EDIT.
    gerencia_id = serializers.PrimaryKeyRelatedField(
        queryset=Gerencia.objects.all(), required=False, allow_null=True, write_only=True
    )
    gerencia_atual = serializers.SerializerMethodField()
    # Papel EQUIPE ("Equipe administrativa") na gerência do form: não vem de função (grupo), o form
    # marca à parte. Ausente = não mexer. A leitura sai em `to_representation`.
    equipe_administrativa = serializers.BooleanField(required=False, write_only=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["equipe_administrativa"] = tem_equipe_administrativa(instance)
        return data

    def validate_gerencia_id(self, value: Any) -> Any:
        """PR A: gerência inativa não vira lotação nova; reenviar a lotação exibida é permitido.

        O form reenvia a gerência atual em toda edição — desativar a gerência não pode
        travar a edição de quem está lotado nela. "Atual" = a mesma de `get_gerencia_atual`.
        """
        if value is None or value.ativo:
            return value
        atual = self.get_gerencia_atual(self.instance) if self.instance is not None else None
        if atual is not None and atual["gerencia_id"] == value.pk:
            return value
        raise serializers.ValidationError("Gerência inativa: escolha uma gerência ativa.")

    # CPF mascarado para list views (LGPD compliance)
    cpf_masked = serializers.SerializerMethodField()

    def get_group_ids_display(self, obj: Any) -> list[int]:
        """Return group IDs for frontend editing."""
        return [g.id for g in obj.groups.all()]

    def get_gerencia_atual(self, obj: Any) -> dict[str, Any] | None:
        """Gerência vigente do usuário (para hidratar o form no EDIT). None se não há vínculo."""
        v = _vinculo_exibido(obj)
        if v is None:
            return None
        return {
            "gerencia_id": v.gerencia_id,
            "rotulo": v.gerencia.rotulo,
            "nome_setor": v.gerencia.nome_setor,
            "setor_canonico": v.gerencia.setor_canonico,
            "papel": v.papel,
        }

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
            "gerencia_id",  # Write-only (cria/atualiza vínculo EquipeGerencia)
            "gerencia_atual",  # Read-only (hidrata a gerência atual no EDIT)
            "equipe_administrativa",  # Papel EQUIPE na gerência do form (lido em to_representation)
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

        # Marcar "Equipe administrativa" precisa de uma gerência (o vínculo é nela). Só vale para o
        # superuser: de outro ator o campo é ignorado, como a lotação toda.
        if (
            attrs_typed.get("equipe_administrativa")
            and attrs_typed.get("gerencia_id") is None
            and self._actor_is_superuser()
            and not (instance is not None and tem_equipe_administrativa(instance))
        ):
            raise serializers.ValidationError({"gerencia_id": "Escolha a gerência da equipe administrativa."})

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

    def _apply_lotacao(
        self, user: Any, groups: Any, gerencia: Any, actor: Any, before_group_ids: Any, equipe: bool | None = None
    ) -> None:
        """Aplica grupos + vínculo de gerência (chamado por create/update; superuser-only).

        #2071 — o salvar mexe só no que o form mudou (o form mostra as FUNÇÕES e UMA gerência):
        - `group_ids` substitui só os grupos de FUNÇÃO; os demais (setor, permissão funcional) ficam.
        - O grupo de setor derivado da gerência (`setor_group_for`, nome == `setor_canonico`) entra e
          sai só quando a gerência muda (ou na primeira lotação); a gerência aprovadora não deriva grupo.
          Só com função que tem papel (`papeis_de_grupos`); o papel EQUIPE nunca dá grupo.
        - A lotação `EquipeGerencia` só é re-sincronizada quando a gerência ou os PAPÉIS mudam. Aí o form
          é a fonte: encerra os outros vínculos; sem papel nenhum, encerra todos (revoga a aprovação).
        - `groups=None` = não mexer nas funções; `gerencia` ausente/`_UNSET`/None = não mexer na lotação.
        - O papel EQUIPE não vem de função: `equipe` (o campo `equipe_administrativa`) o põe ou tira;
          None = manter como está. Ele entra nos papéis de antes e de depois, então salvar sem mudar não
          o apaga e dar ou tirar uma função o mantém.
        - PR B1: audita a concessão/revogação do poder de aprovar solicitações (vínculo GERENTE
          na gerência aprovadora ou composite de grupos) — antes/depois de grupos + vínculo.
        """
        base_antes = solicitation_approval_basis(user)
        aprovava = base_antes is not None
        has_gerencia = gerencia is not None and gerencia is not _UNSET
        funcoes = nomes_grupos_funcao()
        antes = list(user.groups.all())
        exibido = _vinculo_exibido(user)
        anterior = exibido.gerencia if exibido is not None else None
        nova_lotacao = has_gerencia and (anterior is None or anterior.pk != gerencia.pk)

        final = [g for g in antes if groups is None or g.name not in funcoes]
        if groups is not None:
            final += [g for g in groups if g not in final]
        # O grupo de setor só vem de lotação com papel de FUNÇÃO (FORMADOR/COORDENADOR/APOIO/GERENTE): o papel
        # EQUIPE nunca concede grupo, e sem função com papel não há lotação que o explique.
        if nova_lotacao and papeis_de_grupos(final):
            setor_antigo = setor_group_for(anterior) if anterior is not None else None
            setor_novo = setor_group_for(gerencia)
            if (
                setor_antigo is not None
                and setor_antigo != setor_novo
                and (groups is None or setor_antigo not in groups)
            ):
                final = [g for g in final if g != setor_antigo]
            if setor_novo is not None and setor_novo not in final:
                final.append(setor_novo)
        if {g.pk for g in final} != {g.pk for g in antes}:
            user.groups.set(final)
        # #1672: atribuicao de grupos (privilegio) auditada (no-op sem delta).
        auditar_assign_groups(
            actor=actor,
            target_user=user,
            before_group_ids=before_group_ids,
            after_group_ids=[g.pk for g in final],
        )
        equipe_antes = tem_equipe_administrativa(user)
        equipe_depois = equipe_antes if equipe is None else equipe
        papeis = papeis_de_grupos(final) | ({PAPEL_EQUIPE} if equipe_depois else set())
        papeis_antes = papeis_de_grupos(antes) | ({PAPEL_EQUIPE} if equipe_antes else set())
        # O vínculo GERENTE na gerência aprovadora exige a função Gerente (tirada aqui ou na tela de Grupos).
        # Encerrá-lo conta como mudança de papel: a lotação exibida é refeita com os papéis que ficaram.
        encerrou_gerente = (
            groups is not None and "Gerente" not in {g.name for g in final} and encerrar_gerente_aprovador(user)
        )
        if papeis_antes and not papeis:
            # Tirou todas as funções com papel (com ou sem gerência): encerra a lotação e, com ela,
            # o poder de aprovar de quem era GERENTE na gerência aprovadora.
            encerrar_lotacao(user)
        elif has_gerencia and papeis and (nova_lotacao or papeis != papeis_antes or encerrou_gerente):
            sync_user_lotacao(user, gerencia, papeis)
        base = solicitation_approval_basis(user)
        setor, funcao = _PAR_LEGADO
        pedido = groups is not None and setor in {g.name for g in groups}
        par_novo = {setor, funcao} <= {g.name for g in final} and not {setor, funcao} <= {g.name for g in antes}
        if not pedido and (par_novo or (base == "grupo_superintendencia_gerente" and base != base_antes)):
            # O form não mostra o grupo de setor e o preserva; ele não pode virar poder de aprovar pelo
            # par legado sem ninguém pedir (a transação do update() desfaz tudo).
            raise serializers.ValidationError(
                {
                    "group_ids": (
                        f'Esta pessoa tem o grupo "{setor}", que o formulário não mostra. Com a função {funcao}, ela '
                        f"passaria a aprovar solicitações por esse grupo (regra antiga, que vai sair). Tire o grupo "
                        f'"{setor}" dela na tela de Grupos antes de salvar.'
                    )
                }
            )
        aprova = base is not None
        if aprova != aprovava:
            registrar_auditoria(
                actor=actor,
                action=AuditLog.Action.USER_PRIVILEGE_CHANGED,
                model_name="Usuario",
                details={
                    "target_user_id": user.pk,
                    "autoridade_aprovacao": "concedida" if aprova else "revogada",
                },
            )

    @staticmethod
    def _definir_senha_por_admin(user: Any, password: str, actor: Any, *, contexto: str) -> None:
        """Grava a senha definida por esta API (criar usuário / redefinir senha) e audita (#1672).

        Senha dada por OUTRA pessoa liga `deve_trocar_senha`: a dona da conta entra com ela e
        só usa o sistema depois de escolher a própria. Quem muda a PRÓPRIA senha por esta rota
        (ator == alvo) não é marcado. Sem ator identificável, marca (lado seguro). É o único
        lugar da API que liga a marca; o campo fica fora de `Meta.fields`, então não é gravável
        por PATCH/POST.
        """
        user.set_password(password)
        if actor is None or actor.pk != user.pk:
            user.deve_trocar_senha = True
        user.save()
        auditar_reset_senha(actor=actor, target_user=user, contexto=contexto)

    def create(self, validated_data: dict[str, Any]) -> Any:
        """Create user with hashed password, groups e vínculo de gerência."""
        groups = validated_data.pop("groups", None)
        gerencia = validated_data.pop("gerencia_id", None)
        equipe = validated_data.pop("equipe_administrativa", None)
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
            self._definir_senha_por_admin(user, password, actor, contexto="create")

        # P0-1 Tier-0 (D-1=2a): membership + lotação são superuser-only. group_ids /
        # gerencia_id de não-superuser são ignorados (o frontend já não envia — aqui é a
        # fronteira real). DAT cria a conta comum; grupo/vínculo ficam a cargo do superuser.
        if self._actor_is_superuser():
            self._apply_lotacao(user, groups, gerencia, actor, before_group_ids=[], equipe=equipe)

        return user

    @transaction.atomic
    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        """Update user, hash password e sincroniza lotação de gerência (atômico: #2071 pode recusar)."""
        groups = validated_data.pop("groups", None)
        # _UNSET distingue "não enviado" (não mexe no vínculo) de enviado (PATCH parcial).
        gerencia = validated_data.pop("gerencia_id", _UNSET)
        equipe = validated_data.pop("equipe_administrativa", None)
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
            self._definir_senha_por_admin(user, password, actor, contexto="update")

        # P0-1 Tier-0 (D-1=2a): membership + lotação são superuser-only (ver create()).
        # group_ids / gerencia_id de não-superuser são ignorados.
        if self._actor_is_superuser():
            self._apply_lotacao(user, groups, gerencia, actor, before_group_ids=before_group_ids, equipe=equipe)

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
    com os validadores do Django (``AUTH_PASSWORD_VALIDATORS``) COM o usuario — sem ele a
    regra de semelhanca com nome/CPF/e-mail nao roda. Recusa tambem a volta a senha recebida
    de outra pessoa (``Usuario.senha_recebida_hash``). NAO persiste — a view chama
    ``set_password`` + ``update_session_auth_hash``.
    """

    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        if len(value) < 8:
            raise serializers.ValidationError("A senha deve ter no minimo 8 caracteres.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request = self.context.get("request")
        user = request.user if request is not None else None
        if user is None or not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Senha atual incorreta."})
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "A nova senha deve ser diferente da senha atual."})
        # A senha recebida e a mesma para todos: voltar a ela deixaria a conta aberta e sem a marca.
        recebida = user.senha_recebida_hash
        if recebida and check_password(attrs["new_password"], recebida):
            raise serializers.ValidationError(
                {"new_password": "Esta é a senha que você recebeu no primeiro acesso. Escolha outra."}
            )
        try:
            validate_password(attrs["new_password"], user=user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
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
