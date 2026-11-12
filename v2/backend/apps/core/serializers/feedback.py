"""
Serializer do feedback de uso (botão "Dar feedback", 11/11/2026).

Quem enviou vem da sessão (a view grava `usuario=request.user`), nunca do corpo. Na leitura, a
pessoa aparece pelo nome (`str(usuario)`, que nunca é o CPF nem o login).
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportIncompatibleVariableOverride=false, reportMissingTypeArgument=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from rest_framework import serializers

from apps.core.models import Feedback

COMENTARIO_MAX = 2000
PAGINA_MAX = 200  # o max_length de Feedback.pagina


class FeedbackSerializer(serializers.ModelSerializer):
    nota = serializers.IntegerField(min_value=1, max_value=5)
    comentario = serializers.CharField(required=False, allow_blank=True, max_length=COMENTARIO_MAX)
    # Sem limite de tamanho na entrada: a rota é cortada em `PAGINA_MAX` (validate_pagina).
    pagina = serializers.CharField()
    pessoa = serializers.SerializerMethodField()

    class Meta:  # type: ignore[misc]
        model = Feedback
        fields = ["id", "pessoa", "nota", "tipo", "comentario", "pagina", "created_at"]
        read_only_fields = ["id", "pessoa", "created_at"]

    def get_pessoa(self, obj: Feedback) -> str:
        return str(obj.usuario) if obj.usuario is not None else "Usuário removido"

    def validate_pagina(self, value: str) -> str:
        """A rota da tela (`location.pathname`): começa por "/", sem query string nem âncora."""
        caminho = value.split("?", 1)[0].split("#", 1)[0].strip()
        if not caminho.startswith("/") or caminho.startswith("//"):
            raise serializers.ValidationError("Informe a rota da tela, começando por /.")
        return caminho[:PAGINA_MAX]
