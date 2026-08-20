"""
DATCompra Serializers - §10 Epic #459

Purchase/inventory tracking serializers.
Extracted from serializers/dat_module.py.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import DATCompra


class DATCompraSerializer(serializers.ModelSerializer["DATCompra"]):
    """Full serializer for DATCompra (CRUD)."""

    # FK names
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    municipio_uf = serializers.CharField(source="municipio.uf", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, allow_null=True)
    # #1637: codigo e' do Produto (SSOT), nao por-compra. Espelho read-only.
    codigo_produto = serializers.CharField(source="produto.codigo", read_only=True, allow_null=True)

    # Computed
    disponivel = serializers.IntegerField(read_only=True)
    valor_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    # Audit
    created_by_nome = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = DATCompra
        fields = [
            "id",
            # FKs
            "municipio",
            "municipio_nome",
            "municipio_uf",
            "projeto",
            "projeto_nome",
            "produto",
            "produto_nome",
            "codigo_produto",
            "descricao_produto",
            "tipo_compra",
            "tipo",
            "conta_para_codigos",
            # Quantidades
            "quantidade",
            "quantidade_utilizada",
            "disponivel",
            # Valores
            "valor_unitario",
            "valor_total",
            # Período
            "ano_uso",
            "data_compra",
            # Status
            "status_uso",
            "ativo",
            "observacoes",
            # Audit
            "created_by",
            "created_by_nome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "status_uso", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """M15-02 (#1632): invariantes de estoque/valor/coerência (SSOT de entrada).

        Em PATCH, monta os valores EFETIVOS a partir da instância antes de comparar
        (o payload pode conter só um subconjunto dos campos).
        """
        # Padrão que passa pyright strict (espelha serializers/solicitacao.py): getattr(self,
        # "instance", None) devolve Any (conhecido); getattr(instance, field, None) com default.
        instance = getattr(self, "instance", None)

        def eff(field: str) -> Any:
            return attrs.get(field, getattr(instance, field, None))

        quantidade = eff("quantidade")
        quantidade_utilizada = eff("quantidade_utilizada")
        valor_unitario = eff("valor_unitario")
        produto = eff("produto")
        descricao_produto = eff("descricao_produto")
        projeto = eff("projeto")

        errors: dict[str, str] = {}

        if quantidade is not None and quantidade_utilizada is not None and quantidade_utilizada > quantidade:
            errors["quantidade_utilizada"] = (
                f"Quantidade utilizada ({quantidade_utilizada}) não pode exceder a adquirida ({quantidade})."
            )
        if valor_unitario is not None and valor_unitario < 0:
            errors["valor_unitario"] = "Valor unitário não pode ser negativo."
        if produto is None and not (descricao_produto or "").strip():
            errors["descricao_produto"] = "Informe um produto cadastrado ou uma descrição do produto."
        if produto is not None and projeto is not None and produto.projeto_id != projeto.id:
            errors["produto"] = (
                f"O produto '{produto}' pertence ao projeto '{produto.projeto}', "
                f"diferente do projeto da compra ('{projeto}')."
            )

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class DATCompraListSerializer(serializers.ModelSerializer["DATCompra"]):
    """List serializer for DATCompra (table view)."""

    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    municipio_uf = serializers.CharField(source="municipio.uf", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, allow_null=True)
    codigo_produto = serializers.CharField(source="produto.codigo", read_only=True, allow_null=True)
    disponivel = serializers.IntegerField(read_only=True)
    valor_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DATCompra
        fields = [
            "id",
            "municipio_nome",
            "municipio_uf",
            "projeto_nome",
            "produto_nome",
            "codigo_produto",
            "descricao_produto",
            "tipo_compra",
            "tipo",
            "conta_para_codigos",
            "quantidade",
            "quantidade_utilizada",
            "disponivel",
            "valor_unitario",
            "valor_total",
            "ano_uso",
            "data_compra",
            "status_uso",
            "ativo",
        ]
