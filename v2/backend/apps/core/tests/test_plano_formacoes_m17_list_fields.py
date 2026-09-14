"""
PlanoFormacoes — assinatura M17: a List serializer precisa expor os campos que o
modal de edição edita (`ch_estudo`, `observacoes`).

O modal de edição do PlanoFormacoes é semeado a partir da LINHA da lista
(`handleEdit` → `setFieldsValue(record)`), não busca o detalhe. Se a
`PlanoFormacoesListSerializer` OMITE um campo editável, o modal abre **em branco
sobre dado real** (eixos 2/3 da corretude de dados). Mesma classe já corrigida
para Ações/Cadastros/Compras/Coordenadores (M17-02/#1917) — aqui aplicada ao
PlanoFormacoes: expor os campos na List (o detail já os tem).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from apps.core.serializers.plano_formacoes import PlanoFormacoesListSerializer


class TestPlanoFormacoesListM17:
    """A List serializer deve carregar os campos que o modal de edição semeia da linha."""

    def test_list_declara_ch_estudo(self):
        campos = set(PlanoFormacoesListSerializer().fields.keys())
        assert "ch_estudo" in campos, (
            "ch_estudo faltando na List → modal de edição abre em branco sobre " "carga horária de estudo real (M17)."
        )

    def test_list_declara_observacoes(self):
        campos = set(PlanoFormacoesListSerializer().fields.keys())
        assert "observacoes" in campos, (
            "observacoes faltando na List → modal de edição abre em branco sobre " "a observação real do plano (M17)."
        )
