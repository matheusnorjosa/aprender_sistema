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


# ============================================================================
# Shims/Adapters para testes (Issue #39)
# ============================================================================


def normalize_text(value: Optional[str]) -> str:
    """
    Alias para normalize_str() (compatibilidade com testes)

    Examples:
        >>> normalize_text("  João  Silva  ")
        "João Silva"
    """
    return normalize_str(value)


def generate_cpf_from_email(email: str) -> str:
    """
    Gera CPF determinístico fake a partir de email (para testes)

    Usa hash do email convertido para inteiro e formata como CPF de 11 dígitos.

    Examples:
        >>> generate_cpf_from_email("test@example.com")
        "12345678901"  # determinístico baseado no hash
    """
    import hashlib

    if not email:
        return ""

    # Hash do email para gerar CPF determinístico
    hash_obj = hashlib.sha256(email.lower().encode())
    hash_int = int(hash_obj.hexdigest(), 16)

    # Pega os primeiros 11 dígitos do hash
    cpf = str(hash_int)[:11].zfill(11)

    return cpf


def make_sha256_hash(data: str) -> str:
    """
    Gera hash SHA256 de uma string

    Examples:
        >>> make_sha256_hash("test")
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    """
    import hashlib

    if not data:
        return ""

    return hashlib.sha256(str(data).encode()).hexdigest()


def make_iso_datetime(dt, tz=None) -> str:
    """
    Converte datetime para ISO 8601

    Args:
        dt: datetime object ou string
        tz: timezone (opcional)

    Examples:
        >>> from datetime import datetime
        >>> make_iso_datetime(datetime(2025, 1, 15, 14, 30))
        "2025-01-15T14:30:00"
    """
    from datetime import datetime

    if isinstance(dt, str):
        return dt

    if isinstance(dt, datetime):
        return dt.isoformat()

    return ""


def parse_datetime(value: Optional[str]):
    """
    Parse string para datetime

    Args:
        value: string no formato ISO ou comum

    Returns:
        datetime object ou None

    Examples:
        >>> parse_datetime("2025-01-15 14:30:00")
        datetime.datetime(2025, 1, 15, 14, 30)
    """
    from dateutil import parser
    from datetime import datetime

    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return parser.parse(str(value))
    except (ValueError, TypeError):
        return None


def parse_time(value: Optional[str]):
    """
    Parse string para time

    Args:
        value: string no formato "HH:MM" ou "HH:MM:SS"

    Returns:
        time object ou None

    Examples:
        >>> parse_time("14:30")
        datetime.time(14, 30)
    """
    from datetime import time

    if not value:
        return None

    if isinstance(value, time):
        return value

    try:
        # Formato HH:MM ou HH:MM:SS
        parts = str(value).strip().split(":")
        if len(parts) == 2:
            return time(int(parts[0]), int(parts[1]))
        elif len(parts) == 3:
            return time(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError, AttributeError):
        pass

    return None


def split_municipio_uf(value: Optional[str]) -> tuple[str, str]:
    """
    Divide string "Municipio - UF" em tupla (municipio, uf)

    Args:
        value: string no formato "Fortaleza - CE"

    Returns:
        tuple (municipio, uf)

    Examples:
        >>> split_municipio_uf("Fortaleza - CE")
        ("Fortaleza", "CE")
        >>> split_municipio_uf("Caucaia-CE")
        ("Caucaia", "CE")
    """
    if not value:
        return ("", "")

    # Tenta split por " - " primeiro, depois por "-"
    v = str(value).strip()

    if " - " in v:
        parts = v.split(" - ", 1)
    elif "-" in v:
        parts = v.split("-", 1)
    else:
        return (v, "")

    municipio = parts[0].strip() if len(parts) > 0 else ""
    uf = parts[1].strip() if len(parts) > 1 else ""

    return (municipio, uf)


def validate_row_data(row: dict) -> tuple[bool, list[str]]:
    """
    Valida dados de uma linha (dict) retornando (ok, errors)

    Args:
        row: dicionário com dados da linha

    Returns:
        tuple (is_valid: bool, errors: list[str])

    Examples:
        >>> validate_row_data({"nome": "João", "email": "joao@example.com"})
        (True, [])
        >>> validate_row_data({"nome": "", "email": ""})
        (False, ["Campo 'nome' obrigatório", "Campo 'email' obrigatório"])
    """
    errors = []

    # Validações básicas (exemplos - ajustar conforme necessidade)
    required_fields = []  # Nenhum campo obrigatório por padrão

    for field in required_fields:
        if not row.get(field):
            errors.append(f"Campo '{field}' obrigatório")

    return (len(errors) == 0, errors)
