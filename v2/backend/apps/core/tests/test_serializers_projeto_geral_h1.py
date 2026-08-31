"""H.1 — read-serializers expõem `projeto_geral_nome` (família) além da variante `projeto`.

Compra/Ação/Plano/Solicitação expunham só a VARIANTE (`projeto`, ex.: 'NOVO LENDO 1'), nunca a
FAMÍLIA (`projeto_geral`, ex.: 'NOVO LENDO') → o front não reagrupa contagem por família. Nenhum
desses models tem FK direta `projeto_geral`; a família vem via `projeto.projeto_geral` (case-b),
como DATRegistro/DATCadastro já fazem. Este teste fixa o contrato: `projeto_geral_nome` presente,
read-only, com source `projeto.projeto_geral.nome`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from apps.core.serializers.dat_module.dat_acao import DATAcaoListSerializer, DATAcaoSerializer
from apps.core.serializers.dat_module.dat_compra import DATCompraListSerializer, DATCompraSerializer
from apps.core.serializers.plano_formacoes import PlanoFormacoesListSerializer, PlanoFormacoesSerializer
from apps.core.serializers.solicitacao import SolicitacaoSerializer

# 7 read-serializers que a hipótese H.1 apontou (full + List de cada domínio; Solicitação é única).
SERIALIZERS = [
    DATCompraSerializer,
    DATCompraListSerializer,
    DATAcaoSerializer,
    DATAcaoListSerializer,
    PlanoFormacoesSerializer,
    PlanoFormacoesListSerializer,
    SolicitacaoSerializer,
]


def test_projeto_geral_nome_exposto_com_source_de_familia() -> None:
    for cls in SERIALIZERS:
        nome = cls.__name__
        assert "projeto_geral_nome" in cls.Meta.fields, f"{nome}: 'projeto_geral_nome' ausente de Meta.fields"
        field = cls._declared_fields["projeto_geral_nome"]
        assert field.source == "projeto.projeto_geral.nome", f"{nome}: source errado ({field.source})"
        assert field.read_only is True, f"{nome}: deveria ser read-only"
