"""
AS v2 — Workflow Serializers

Serializers para AcaoDAT, Deslocamento.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import AcaoDAT, Deslocamento, EquipeGerencia, Usuario
from apps.core.rbac.policies import gerencias_que_delegam_deslocamento, user_delega_deslocamento_de_qualquer_um


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


class DeslocamentoSerializer(serializers.ModelSerializer):
    """
    Serializer for Deslocamento model (Issue #188).

    Provides CRUD operations for travel records between municipalities.

    Fields:
        - id, usuario, origem, destino, start_date, end_date, observacao
        - usuario_nome (read-only): Nome do usuário, ou "Usuario #id" (nunca o login, que é o CPF)
        - pode_editar (read-only): se quem pede pode editar e excluir a linha (a tela só mostra os
          botões aí). Mesma regra de `DeslocamentoViewSet._ensure_owner_or_delegate`.
        - external_hash (read-only): ETL idempotence hash
        - created_at, updated_at (read-only)

    Validation:
        - start_date <= end_date: ida e volta no mesmo dia vale (error: "Data fim não pode ser anterior à data início.")
        - origem != destino (error: "Origem e destino devem ser diferentes")

    Escrita owner-forced (#1454): `usuario` opcional; omitido → self-service.
    Registrar em nome de outro exige delegação (validada na view).
    """

    usuario_nome = serializers.SerializerMethodField()
    pode_editar = serializers.SerializerMethodField()

    class Meta:
        model = Deslocamento
        fields = [
            "id",
            "usuario",
            "usuario_nome",
            "pode_editar",
            "origem",
            "destino",
            "start_date",
            "end_date",
            "observacao",
            "external_hash",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_hash", "created_at", "updated_at"]
        extra_kwargs = {
            # #1454: `usuario` é opcional na entrada. Omitido → self-service
            # (a view força request.user). Preenchido ≠ self → exige capability
            # de delegação (validada em DeslocamentoViewSet.perform_create).
            "usuario": {"required": False},
        }

    def get_usuario_nome(self, obj: Deslocamento) -> str:
        """Nome do usuário, ou "Usuario #id": nunca o login (CPF)."""
        usuario = cast("Usuario | None", obj.usuario)
        if usuario:
            return str(usuario)
        return ""

    def get_pode_editar(self, obj: Deslocamento) -> bool:
        """Dono, ou quem delega para o dono da linha (`user_can_delegate_deslocamento`)."""
        request: Any = cast("dict[str, Any]", self.context).get("request")
        user: Any = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if obj.usuario_id == user.pk:
            return True
        alvos = self._alvos_que_delega(user)
        return alvos is None or obj.usuario_id in alvos

    def _alvos_que_delega(self, user: Any) -> set[int] | None:
        """Ids dos formadores que `user` delega (None = qualquer um), calculado uma vez por requisição.

        Na lista, o `child` do ListSerializer é uma instância só: o cache no `self` vale para a página toda.
        """
        if not hasattr(self, "_cache_alvos_que_delega"):
            if user_delega_deslocamento_de_qualquer_um(user):
                alvos: set[int] | None = None
            else:
                gerencias = gerencias_que_delegam_deslocamento(user)
                alvos = (
                    set(
                        EquipeGerencia.vigentes_em()
                        .filter(papel="FORMADOR", gerencia_id__in=gerencias, gerencia__ativo=True)
                        .values_list("usuario_id", flat=True)
                    )
                    if gerencias
                    else set()
                )
            self._cache_alvos_que_delega = alvos
        return self._cache_alvos_que_delega

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Valida regras de negócio:
        - start_date <= end_date (mesmo dia vale: ida e volta)
        - origem != destino

        Suporta PATCH parcial: se apenas um campo vier no payload,
        usa valor atual da instância.
        """
        instance = getattr(self, "instance", None)

        # Obter valores (novos ou existentes)
        start_date = attrs.get("start_date", getattr(instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(instance, "end_date", None))
        origem = attrs.get("origem", getattr(instance, "origem", None))
        destino = attrs.get("destino", getattr(instance, "destino", None))

        # Validação 1: start_date <= end_date (decisão do dono, 05/11: ida e volta no mesmo dia vale)
        if start_date is not None and end_date is not None:
            if end_date < start_date:
                raise serializers.ValidationError({"end_date": "Data fim não pode ser anterior à data início."})

        # Validação 2: origem != destino
        if origem is not None and destino is not None:
            if origem.strip().lower() == destino.strip().lower():
                raise serializers.ValidationError({"destino": "Origem e destino devem ser diferentes"})

        return super().validate(attrs)
