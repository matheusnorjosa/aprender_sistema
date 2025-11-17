"""
Helper para normalização de nomes de projetos.

Resolve variantes de nomes de projetos para seus nomes canônicos, garantindo
consistência em importações ETL e queries.

Issue: #150
"""

from typing import Dict, List


# Mapeamento de nomes canônicos e suas variantes conhecidas
CANONICAL_PROJECT_NAMES: Dict[str, List[str]] = {
    # Nome canônico: [lista de variantes]
    "LEIO, ESCREVO E CALCULO": [
        "LEIO ESCREVO E CALCULO",
        "LEIO,ESCREVO E CALCULO",
        "LEIO ESCREVO E CÁLCULO",
        "LEIO, ESCREVO E CÁLCULO",
    ],
    "GESTÃO ESCOLAR": [
        "GESTAO ESCOLAR",  # Sem acentos
        "Gestao Escolar",  # Mixed case sem acentos
        "IDEB10",  # Nome antigo
        # Nota: "Gestão Escolar" (mixed case COM acentos) não precisa estar aqui
        # pois .upper() já converte para "GESTÃO ESCOLAR" (canônico)
    ],
    "LER, OUVIR E CONTAR": [
        "LER OUVIR E CONTAR",
        "LER,OUVIR E CONTAR",
        "LER OUVIR CONTAR",
    ],
}


# Criar um dicionário reverso para lookup rápido: variante -> canônico
_VARIANT_TO_CANONICAL: Dict[str, str] = {}
for canonical, variants in CANONICAL_PROJECT_NAMES.items():
    for variant in variants:
        _VARIANT_TO_CANONICAL[variant.upper().strip()] = canonical


def normalize_project_name(name: str) -> str:
    """
    Normaliza nome de projeto para versão canônica.

    Args:
        name: Nome do projeto (pode ser variante)

    Returns:
        Nome canônico do projeto. Se não houver normalização conhecida,
        retorna o nome original (uppercased e stripped).

    Examples:
        >>> normalize_project_name("LEIO ESCREVO E CALCULO")
        'LEIO, ESCREVO E CALCULO'

        >>> normalize_project_name("  leio escrevo e calculo  ")
        'LEIO, ESCREVO E CALCULO'

        >>> normalize_project_name("Gestão Escolar")
        'GESTÃO ESCOLAR'

        >>> normalize_project_name("PROJETO DESCONHECIDO")
        'PROJETO DESCONHECIDO'
    """
    normalized_input = name.upper().strip()

    # Lookup no dicionário de variantes
    return _VARIANT_TO_CANONICAL.get(normalized_input, name.upper().strip())


def is_known_variant(name: str) -> bool:
    """
    Verifica se o nome é uma variante conhecida (não-canônica).

    Args:
        name: Nome do projeto

    Returns:
        True se é uma variante conhecida que precisa ser normalizada

    Examples:
        >>> is_known_variant("LEIO ESCREVO E CALCULO")
        True

        >>> is_known_variant("LEIO, ESCREVO E CALCULO")
        False  # É o canônico

        >>> is_known_variant("PROJETO DESCONHECIDO")
        False  # Não é conhecido
    """
    normalized = name.upper().strip()

    # É variante se está no dicionário e NÃO é um dos canônicos
    if normalized in _VARIANT_TO_CANONICAL:
        return _VARIANT_TO_CANONICAL[normalized] != normalized

    return False


def get_canonical_name(name: str) -> str | None:
    """
    Retorna o nome canônico se o nome for uma variante conhecida.

    Args:
        name: Nome do projeto (potencialmente variante)

    Returns:
        Nome canônico se for variante conhecida, None caso contrário

    Examples:
        >>> get_canonical_name("LEIO ESCREVO E CALCULO")
        'LEIO, ESCREVO E CALCULO'

        >>> get_canonical_name("LEIO, ESCREVO E CALCULO")
        None  # Já é canônico

        >>> get_canonical_name("PROJETO DESCONHECIDO")
        None  # Não é conhecido
    """
    if is_known_variant(name):
        return normalize_project_name(name)
    return None


def list_all_variants() -> Dict[str, List[str]]:
    """
    Lista todos os nomes canônicos e suas variantes conhecidas.

    Returns:
        Dicionário {canônico: [variantes]}

    Example:
        >>> variants = list_all_variants()
        >>> "LEIO, ESCREVO E CALCULO" in variants
        True
    """
    return CANONICAL_PROJECT_NAMES.copy()
