"""
Filtro para identificar tokens de indicadores (não-pessoas) nas planilhas.

CONTEXTO (PR20 Task 2):
A auditoria identificou 123 "pessoas pendentes" sem cadastro, porém muitas
dessas entradas são indicadores de ano/disciplina (ex: "3º ANO LING") e não
nomes de pessoas reais.

OBJETIVO:
Filtrar esses indicadores para evitar criar Participation com usuario_id NULL
e reduzir drasticamente as pendências reais de cadastro.

PADRÕES IDENTIFICADOS:
- Ano + Disciplina: "3º ANO LING", "5º ANO MAT", "1º ANO CIÊNCIAS"
- Grupos genéricos: "Coordenadores", "Formadores"
- Outros indicadores de turma/série
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false


from __future__ import annotations

import re
from typing import Optional


def is_indicator_token(name: Optional[str]) -> bool:
    """
    Verifica se um nome é um indicador (não-pessoa).

    Args:
        name: Nome a verificar (pode ser None)

    Returns:
        True se for indicador, False se for possível nome de pessoa

    Exemplos:
        >>> is_indicator_token("3º ANO LING")
        True
        >>> is_indicator_token("João Silva")
        False
        >>> is_indicator_token("Coordenadores")
        True
        >>> is_indicator_token(None)
        False
    """
    if not name:
        return False

    # Normalizar: strip, lowercase, remover acentos
    name_norm = name.strip().lower()
    # Remover acentos (é → e, ã → a, etc.)
    import unicodedata

    name_norm = unicodedata.normalize("NFKD", name_norm).encode("ascii", "ignore").decode("ascii")

    if not name_norm:
        return False

    # Padrão 1: "Xº ANO <disciplina>"
    # Exemplos: "3º ANO LING", "5º ANO MAT", "10º ANO CIÊNCIAS"
    # Regex: dígitos + opcional(º/ª/o) + espaço + ANO/SÉRIE + espaço + palavra
    # Nota: após normalização, símbolos especiais (°) são removidos
    pattern_ano = r"^\d{1,2}[oa]?\s+(ano|serie)\s+\w+"
    if re.match(pattern_ano, name_norm, re.IGNORECASE):
        return True

    # Padrão 2: Grupos genéricos (plural)
    # Exemplos: "Coordenadores", "Formadores", "Professores"
    generic_groups = [
        "coordenadores",
        "formadores",
        "professores",
        "gestores",
        "diretores",
        "alunos",
        "turma",
        "grupo",
    ]
    if name_norm in generic_groups:
        return True

    # Padrão 3: Apenas "Xº ANO" ou "Xª SÉRIE" sem disciplina
    # Exemplos: "3º ANO", "5º ANO", "1ª SÉRIE"
    pattern_ano_simple = r"^\d{1,2}[oa]?\s+(ano|serie)$"
    if re.match(pattern_ano_simple, name_norm, re.IGNORECASE):
        return True

    # Padrão 4: Código de turma (letras + números) ou "TURMA X"
    # Exemplos: "T301", "A5B", "TURMA A", "TURMA 5B"
    pattern_turma_code = r"^turma\s+[a-z0-9]+$"
    if re.match(pattern_turma_code, name_norm):
        return True
    # Código simples sem "TURMA": T301, A5B
    pattern_code_simple = r"^[a-z]?\d{1,3}[a-z]?$"
    if re.match(pattern_code_simple, name_norm):
        return True

    return False


def filter_indicators_from_list(names: list[str]) -> list[str]:
    """
    Filtra lista de nomes removendo indicadores.

    Args:
        names: Lista de nomes (podem conter indicadores)

    Returns:
        Lista apenas com nomes de pessoas (indicadores removidos)

    Exemplo:
        >>> filter_indicators_from_list(["João Silva", "3º ANO LING", "Maria Santos"])
        ["João Silva", "Maria Santos"]
    """
    return [name for name in names if name and not is_indicator_token(name)]


def should_create_participation(usuario_nome: Optional[str]) -> bool:
    """
    Decide se deve criar Participation para um nome.

    Args:
        usuario_nome: Nome do usuário candidato

    Returns:
        True se deve criar Participation, False se deve pular

    Uso no ETL:
        if should_create_participation(formador_nome):
            # Tentar resolver e criar Participation
        else:
            # Pular (é indicador ou None)
    """
    # Se nome vazio/None, NÃO criar Participation
    if not usuario_nome or not usuario_nome.strip():
        return False

    # Se for indicador, NÃO criar Participation
    if is_indicator_token(usuario_nome):
        return False

    # Nome válido e não é indicador: CRIAR Participation
    return True
