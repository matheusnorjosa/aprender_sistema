"""
Regra da compra: quem cria evento onde (SSOT; plano de 14/10/2026, decisões do dono de 02/10 e 14/10).

Um par (município, projeto) está liberado quando, NO MESMO MUNICÍPIO, existe `DATCompra` ativa com
quantidade > 0 (qualquer ano de uso, qualquer tipo):
- do mesmo projeto; ou
- de qualquer projeto da mesma coleção (`projeto_geral`); ou
- de qualquer projeto da mesma gerência, se o projeto tem a marca `eh_nome_geral`; ou
- de qualquer projeto da coleção de um combo (`COMBOS`) que libera a coleção do projeto.

Projeto sem compra que o libere em município nenhum fica "em espera": some das listas de operação e
volta sozinho quando a compra entra.

Isentos: superusuário e quem tem a capacidade `create_solicitation_without_purchase` (sem grupo até o
pacote do DAT recebê-la).

Armadilha do NULL: `Q(projeto__projeto_geral_id=None)` vira `IS NULL` no Django e liberaria todo projeto
sem coleção pela compra de qualquer outro projeto sem coleção. Por isso a coleção e a gerência só
entram quando não são nulas. Do lado do `OuterRef`, NULL nunca casa no SQL, que é o certo.

Só leitura. Quem chama: `serializers/solicitacao.py` (criação e edição), `views_validate.py`,
`views_lookup.py` (municípios e projetos) e `views_options.py` (Plano Anual).
"""

from __future__ import annotations

from typing import Any

from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.core.models import DATCompra, Municipio, Projeto
from apps.core.rbac.helpers import user_has_any_perm

CAPACIDADE_ISENTA = "create_solicitation_without_purchase"

# Combo: kit vendido como um produto só que atravessa coleções (decisão do dono de 20/10/2026). Coleção do
# combo -> coleções que a compra dele libera, sempre no mesmo município. Por `ProjetoGeral.nome` (único).
COMBOS: dict[str, tuple[str, ...]] = {
    "NL E AMMA PORT E MAT": ("NOVO LENDO", "PROJETO AMMA"),
}


def isento_da_regra_da_compra(user: Any) -> bool:
    """Superusuário (bypass de `user_has_any_perm`) ou quem tem a capacidade de isenção."""
    return user_has_any_perm(user, CAPACIDADE_ISENTA)


def _compras_validas() -> QuerySet[DATCompra]:
    return DATCompra.objects.filter(ativo=True, quantidade__gt=0)


def _q_libera(projeto: Projeto) -> Q:
    """Compras (de qualquer município) que liberam `projeto`. Nunca compara com NULL."""
    q = Q(projeto_id=projeto.pk)
    projeto_geral_id = projeto.projeto_geral_id  # type: ignore[attr-defined]
    if projeto_geral_id is not None:
        q |= Q(projeto__projeto_geral_id=projeto_geral_id)
        colecao = projeto.projeto_geral.nome  # type: ignore[union-attr]
        combos = [combo for combo, colecoes in COMBOS.items() if colecao in colecoes]
        if combos:
            q |= Q(projeto__projeto_geral__nome__in=combos)
    gerencia_id = projeto.gerencia_id  # type: ignore[attr-defined]
    if projeto.eh_nome_geral and gerencia_id is not None:
        q |= Q(projeto__gerencia_id=gerencia_id)
    return q


def par_liberado(municipio_id: int, projeto: Projeto) -> bool:
    """O par (município, projeto) tem compra que o libere."""
    return _compras_validas().filter(_q_libera(projeto), municipio_id=municipio_id).exists()


def municipios_liberados(qs: QuerySet[Municipio], projeto: Projeto | None) -> QuerySet[Municipio]:
    """Municípios de `qs` liberados para `projeto`; com `projeto=None`, os que têm alguma compra válida."""
    compras = _compras_validas().filter(municipio_id=OuterRef("pk"))
    if projeto is not None:
        compras = compras.filter(_q_libera(projeto))
    return qs.filter(Exists(compras))


def projetos_liberados(qs: QuerySet[Projeto], municipio_id: int | None = None) -> QuerySet[Projeto]:
    """Projetos de `qs` liberados no município; sem município, os que não estão "em espera"."""
    compras = _compras_validas()
    if municipio_id is not None:
        compras = compras.filter(municipio_id=municipio_id)
    mesmo_projeto = Exists(compras.filter(projeto_id=OuterRef("pk")))
    mesma_colecao = Exists(compras.filter(projeto__projeto_geral_id=OuterRef("projeto_geral_id")))
    mesma_gerencia = Exists(compras.filter(projeto__gerencia_id=OuterRef("gerencia_id")))
    libera = mesmo_projeto | mesma_colecao | (Q(eh_nome_geral=True) & mesma_gerencia)
    for combo, colecoes in COMBOS.items():
        libera |= Q(projeto_geral__nome__in=colecoes) & Exists(compras.filter(projeto__projeto_geral__nome=combo))
    return qs.filter(libera)
