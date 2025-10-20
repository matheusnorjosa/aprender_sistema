"""
Normalizers - Funções utilitárias para limpar e normalizar dados de ETL
"""

import re
from typing import Optional


def normalize_str(value: Optional[str], default: str = "") -> str:
    """
    Normaliza string: strip, remove espaços múltiplos

    Examples:
        >>> normalize_str("  João  Silva  ")
        "João Silva"
        >>> normalize_str(None)
        ""
    """
    if not value:
        return default
    # Strip e remove espaços múltiplos
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_email(value: Optional[str]) -> str:
    """
    Normaliza email: lowercase, strip

    Examples:
        >>> normalize_email(" JOAO@Example.COM ")
        "joao@example.com"
    """
    if not value:
        return ""
    return str(value).strip().lower()


def normalize_cpf(value: Optional[str]) -> str:
    """
    Normaliza CPF: remove formatação, mantém apenas dígitos

    Examples:
        >>> normalize_cpf("123.456.789-00")
        "12345678900"
        >>> normalize_cpf("123 456 789 00")
        "12345678900"
    """
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


def normalize_telefone(value: Optional[str]) -> str:
    """
    Normaliza telefone: remove formatação, mantém apenas dígitos

    Examples:
        >>> normalize_telefone("(85) 98765-4321")
        "85987654321"
    """
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


def titlecase(value: Optional[str]) -> str:
    """
    Aplica title case em nomes (exceto conectores)

    Examples:
        >>> titlecase("joão da silva")
        "João da Silva"
        >>> titlecase("MARIA DE SOUZA")
        "Maria de Souza"
    """
    if not value:
        return ""

    # Palavras que não devem ser capitalizadas (conectores)
    excecoes = {"de", "da", "do", "das", "dos", "e"}

    palavras = normalize_str(value).lower().split()
    resultado = []

    for i, palavra in enumerate(palavras):
        # Primeira palavra sempre capitalizada
        # Conectores apenas se não forem a primeira palavra
        if i == 0 or palavra not in excecoes:
            resultado.append(palavra.capitalize())
        else:
            resultado.append(palavra)

    return " ".join(resultado)


def normalize_uf(value: Optional[str]) -> str:
    """
    Normaliza UF: uppercase, 2 caracteres

    Examples:
        >>> normalize_uf("ce")
        "CE"
        >>> normalize_uf("Ceará")
        "CE"
    """
    if not value:
        return ""

    # Mapa de estados por extenso → sigla
    estados = {
        "acre": "AC",
        "alagoas": "AL",
        "amapá": "AP",
        "amapa": "AP",
        "amazonas": "AM",
        "bahia": "BA",
        "ceará": "CE",
        "ceara": "CE",
        "distrito federal": "DF",
        "espírito santo": "ES",
        "espirito santo": "ES",
        "goiás": "GO",
        "goias": "GO",
        "maranhão": "MA",
        "maranhao": "MA",
        "mato grosso": "MT",
        "mato grosso do sul": "MS",
        "minas gerais": "MG",
        "pará": "PA",
        "para": "PA",
        "paraíba": "PB",
        "paraiba": "PB",
        "paraná": "PR",
        "parana": "PR",
        "pernambuco": "PE",
        "piauí": "PI",
        "piaui": "PI",
        "rio de janeiro": "RJ",
        "rio grande do norte": "RN",
        "rio grande do sul": "RS",
        "rondônia": "RO",
        "rondonia": "RO",
        "roraima": "RR",
        "santa catarina": "SC",
        "são paulo": "SP",
        "sao paulo": "SP",
        "sergipe": "SE",
        "tocantins": "TO",
    }

    v = str(value).strip().lower()

    # Se já é uma sigla válida
    if len(v) == 2 and v.upper() in estados.values():
        return v.upper()

    # Se é o nome por extenso
    return estados.get(v, v.upper()[:2])


def parse_bool(value: Optional[str], default: bool = True) -> bool:
    """
    Parse valores booleanos de planilhas

    Examples:
        >>> parse_bool("Sim")
        True
        >>> parse_bool("Não")
        False
        >>> parse_bool("1")
        True
        >>> parse_bool("")
        True
    """
    if not value:
        return default

    v = str(value).strip().lower()

    # Valores falsos
    if v in {"não", "nao", "n", "false", "0", "inativo"}:
        return False

    # Valores verdadeiros
    if v in {"sim", "s", "true", "1", "ativo"}:
        return True

    return default
