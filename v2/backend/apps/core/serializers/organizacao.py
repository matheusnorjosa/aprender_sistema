"""
AS v2 — Organizacao Serializers

Serializers para Municipio, ProjetoGeral, Projeto, Gerencia, TipoEvento, Produto.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportReturnType=false

from __future__ import annotations

from typing import Any

from rest_framework import serializers  # type: ignore[attr-defined]

from apps.core.models import Gerencia, Municipio, Produto, Projeto, ProjetoGeral, TipoEvento
from apps.core.rbac.helpers import (
    GERENCIA_APROVADORA_NOME,
    MSG_FLUXO_SUPER_SO_NA_SUPERINTENDENCIA,
    fluxo_super_fora_da_superintendencia,
)


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


class ProjetoGeralSerializer(serializers.ModelSerializer["ProjetoGeral"]):
    """
    Full serializer for ProjetoGeral model (Admin CRUD).

    Ref: SPEC_DAT_REGISTROS.md seção 2.1
    """

    projetos_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = ProjetoGeral
        fields = [
            "id",
            "nome",
            "usa_avaliar",
            "tipo_calculo_codigos",
            "divisor_aluno",
            "multiplicador_professor",
            "ativo",
            "descricao",
            "projetos_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ProjetoGeralOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for ProjetoGeral (dropdowns/selects).
    """

    class Meta:
        model = ProjetoGeral
        fields = ["id", "nome", "usa_avaliar", "tipo_calculo_codigos"]


class ProjetoSerializer(serializers.ModelSerializer):
    """
    Full serializer for Projeto model (Admin CRUD).

    PR 7 hardening RBAC (2026-04-30): `fluxo` é obrigatório explicitamente
    no payload da API. Antes o field model tinha `default="NAO_SUPER"`,
    o que silenciosamente assumia esse valor quando ausente — o serializer
    agora exige escolha explícita (`SUPER` ou `NAO_SUPER`) na criação. O
    default do model permanece para uso interno (fixtures de teste, ORM
    direto), mas a API/Admin não dependem mais dele.
    """

    gerencia_nome = serializers.CharField(source="gerencia.rotulo", read_only=True, allow_null=True)
    # `setor` NÃO é declarado aqui: o ModelSerializer o gera do campo model `Projeto.setor`
    # (CharField gravável, read devolve o valor ARMAZENADO). A derivação vai para `setor_efetivo`
    # (read-only) — assim o modal de edição liga no raw sem contaminá-lo (guarda anti-M17).
    setor_efetivo = serializers.SerializerMethodField()
    projeto_geral_nome = serializers.CharField(source="projeto_geral.nome", read_only=True, allow_null=True)

    # PR 7 (2026-04-30): explícito + required=True (não consome default do
    # model). DRF respeita choices e devolve 400 com mensagem padrão.
    fluxo = serializers.ChoiceField(choices=Projeto.FLUXO_CHOICES, required=True)

    def get_setor_efetivo(self, obj: Projeto) -> str:
        """Setor EFETIVO para EXIBIÇÃO: campo canônico do model (`Projeto.setor`, do de-para v15)
        quando preenchido; senão deriva de `gerencia.nome_setor` (fallback sem regressão #1893).
        Read-only: a grade exibe este; o form de conferência grava no raw `setor`."""
        return obj.setor or (obj.gerencia.nome_setor if obj.gerencia else "")

    class Meta:
        model = Projeto
        fields = [
            "id",
            "nome",
            "codigo",
            "fluxo",
            "ativo",
            "gerencia",
            "gerencia_nome",
            "projeto_geral",
            "projeto_geral_nome",
            "setor",
            "setor_efetivo",
            "sem_operacao",
            "eh_serie",
            "is_test",
        ]
        # sem_operacao: autoritativo do import (#1897), sem entrada-direta → read-only.
        read_only_fields = ["id", "sem_operacao"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Regra do dono (30/09): fluxo SUPER só em projeto da gerência Superintendência (g1).

        Vale quando o payload grava `fluxo` ou `gerencia` (estado final = payload + instância); um
        PATCH só de outros campos não é barrado por dado antigo. Erro sem campo → vira o `detail`
        da resposta, que a ProjetosPage mostra.
        """
        if "fluxo" in attrs or "gerencia" in attrs:
            instance = getattr(self, "instance", None)
            fluxo = attrs.get("fluxo", getattr(instance, "fluxo", None))
            gerencia = attrs.get("gerencia", getattr(instance, "gerencia", None))
            if fluxo_super_fora_da_superintendencia(fluxo, gerencia):
                raise serializers.ValidationError(MSG_FLUXO_SUPER_SO_NA_SUPERINTENDENCIA)
        return attrs


class ProjetoOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Projeto (dropdowns/selects).
    """

    class Meta:
        model = Projeto
        fields = ["id", "nome", "codigo"]


class GerenciaSerializer(serializers.ModelSerializer["Gerencia"]):
    """
    Serializer para modelo Gerencia.

    Fields:
        - id, nome, nome_setor, nome_exibicao, gerente (nested), ativo
        - rotulo (read-only): nome que a tela mostra (`nome_exibicao or nome_setor`)
        - projetos_count (annotated, read-only)
    """

    gerente_nome = serializers.CharField(source="gerente.get_full_name", read_only=True, allow_null=True)
    projetos_count = serializers.IntegerField(read_only=True, required=False)
    rotulo = serializers.CharField(read_only=True)

    class Meta:  # type: ignore[misc]
        model = Gerencia
        fields = [
            "id",
            "nome",
            "nome_setor",
            "nome_exibicao",
            "rotulo",
            "setor_canonico",
            "setor_canonico_confianca",
            "gerente",
            "gerente_nome",
            "ativo",
            "descricao",
            # Decisão do dono (05/10/2026): False = a Nova Solicitação não pergunta se a pessoa
            # pretende avaliar o formador (vale a gerência do PROJETO do evento).
            "pergunta_avaliar_formador",
            "projetos_count",
            "created_at",
            "updated_at",
        ]
        # setor_canonico_confianca: sinal importado do de-para (RELAY 50, item 8), SEM entrada-direta →
        # read-only. Fora da tela desde o C2b; o campo segue na API.
        read_only_fields = ["created_at", "updated_at", "setor_canonico_confianca"]

    def validate_nome(self, value: str) -> str:
        """PR B1 (anti-escalada): `nome` da gerência aprovadora é chave de autorização.

        GERENTE vigente em `GERENCIA_APROVADORA_NOME` aprova solicitações. Renomear g1
        desligaria as aprovações; dar esse nome a outra gerência ligaria o poder de aprovar
        para os GERENTEs dela. Rótulo de tela é `nome_exibicao` (editável; `rotulo`).
        """
        instance: Any = self.instance
        atual = getattr(instance, "nome", None)
        if atual == GERENCIA_APROVADORA_NOME and value != atual:
            raise serializers.ValidationError(
                "O nome desta gerência não pode ser alterado: ele define quem aprova solicitações."
            )
        if value == GERENCIA_APROVADORA_NOME and atual != GERENCIA_APROVADORA_NOME:
            raise serializers.ValidationError(
                f"O nome '{GERENCIA_APROVADORA_NOME}' é reservado à gerência que aprova solicitações."
            )
        return value


class TipoEventoOptionSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for TipoEvento (dropdowns/selects).
    """

    class Meta:
        model = TipoEvento
        fields = ["id", "nome"]


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


class ProdutoOptionSerializer(serializers.ModelSerializer["Produto"]):
    """
    Serializer minimalista para dropdowns de Produto.
    """

    class Meta:
        model = Produto
        fields = ["id", "nome", "codigo"]
