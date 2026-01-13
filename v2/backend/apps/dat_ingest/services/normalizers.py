"""
Normalizers - Funções utilitárias para limpar e normalizar dados de ETL
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false


from __future__ import annotations
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
    # Remove não-dígitos, padroniza para 11 dígitos (pad com zeros à esquerda, trunca se maior)
    return re.sub(r"\D", "", str(value)).zfill(11)[:11]


def normalize_telefone(value: Optional[str]) -> str:
    """
    Normaliza telefone: remove formatação, mantém apenas dígitos

    Examples:
        >>> normalize_telefone("(85) 98765-4321")
        "85987654321"
    """
    if not value:
        return ""
    # Remove não-dígitos e trunca para 11 dígitos (DDD + 9 dígitos)
    return re.sub(r"\D", "", str(value))[:11]


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
    return estados.get(v, "")


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
    # Tratamento especial para int(0) que é falsy mas deve retornar False
    if value == 0 or value == "0":
        return False

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
    Normalização completa: remove acentos, caracteres especiais, lowercase, colapsa espaços

    Examples:
        >>> normalize_text("  João  Silva  ")
        "joao silva"
        >>> normalize_text("Olá! Como vai?")
        "ola como vai"
    """
    import unicodedata

    if not value:
        return ""

    # Converter para string e normalizar espaços
    text = normalize_str(value)

    # Remove acentos (NFD = decomposição, filtra apenas caracteres base)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

    # Remove caracteres especiais (mantém apenas letras, números e espaços)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    # Lowercase e colapsa espaços múltiplos
    text = re.sub(r'\s+', ' ', text.lower().strip())

    return text


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


def make_sha256_hash(*args) -> str:
    """
    Gera hash SHA256 de uma ou mais strings concatenadas

    Args:
        *args: strings para concatenar e hashear

    Examples:
        >>> make_sha256_hash("test")
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        >>> make_sha256_hash("test", "data")
        "..."  # hash de "testdata"
    """
    import hashlib

    # Concatena todos os argumentos, convertendo None para string vazia
    data = "".join(str(arg) if arg is not None else "" for arg in args)

    if not data:
        return hashlib.sha256(b"").hexdigest()

    return hashlib.sha256(data.encode()).hexdigest()


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


def parse_datetime(date_val, time_val=None):
    """
    Parse date e time para datetime

    Args:
        date_val: string de data ou datetime
        time_val: string de hora ou time object (opcional)

    Returns:
        datetime object ou None

    Examples:
        >>> parse_datetime("2025-01-15", "14:30")
        datetime.datetime(2025, 1, 15, 14, 30)
        >>> parse_datetime("2025-01-15")
        datetime.datetime(2025, 1, 15, 0, 0)
    """
    from dateutil import parser
    from datetime import datetime, time as time_type

    if not date_val:
        return None

    # Se já é datetime, retorna
    if isinstance(date_val, datetime):
        return date_val

    try:
        # Parse data
        dt = parser.parse(str(date_val))

        # Se time_val fornecido, combina
        if time_val:
            if isinstance(time_val, time_type):
                dt = dt.replace(hour=time_val.hour, minute=time_val.minute, second=time_val.second)
            else:
                # Parse time_val como string
                time_obj = parse_time(time_val)
                if time_obj:
                    dt = dt.replace(hour=time_obj.hour, minute=time_obj.minute, second=time_obj.second)

        return dt
    except (ValueError, TypeError):
        return None


def parse_time(value: Optional[str]):
    """
    Parse string para time

    Args:
        value: string no formato "HH:MM", "HH:MM:SS", "HH" ou float Excel (0.5 = 12:00)

    Returns:
        time object ou None

    Examples:
        >>> parse_time("14:30")
        datetime.time(14, 30)
        >>> parse_time("14")
        datetime.time(14, 0)
        >>> parse_time(0.5)
        datetime.time(12, 0)
    """
    from datetime import time

    if not value and value != 0:
        return None

    if isinstance(value, time):
        return value

    # Excel time: float entre 0 e 1 (0.5 = 12:00)
    if isinstance(value, (float, int)) and 0 <= value <= 1:
        try:
            total_seconds = int(value * 24 * 3600)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return time(hours, minutes)
        except (ValueError, OverflowError):
            pass

    try:
        # Formato HH (apenas hora)
        v = str(value).strip()
        if ":" not in v and v.isdigit():
            return time(int(v), 0)

        # Formato HH:MM ou HH:MM:SS
        parts = v.split(":")
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
        value: string no formato "Fortaleza - CE", "Fortaleza-CE" ou "Fortaleza/CE"

    Returns:
        tuple (municipio, uf)

    Examples:
        >>> split_municipio_uf("Fortaleza - CE")
        ("Fortaleza", "CE")
        >>> split_municipio_uf("Caucaia-CE")
        ("Caucaia", "CE")
        >>> split_municipio_uf("Fortaleza/CE")
        ("Fortaleza", "CE")
    """
    if not value:
        return ("", "")

    # Tenta split por " - " primeiro, depois por "-", depois por "/"
    v = str(value).strip()

    if " - " in v:
        parts = v.split(" - ", 1)
    elif "/" in v:
        parts = v.split("/", 1)
    elif "-" in v:
        parts = v.split("-", 1)
    else:
        return (v, "")

    municipio = parts[0].strip() if len(parts) > 0 else ""
    uf = parts[1].strip() if len(parts) > 1 else ""

    return (municipio, uf)


def validate_row_data(row: dict, fields: list[str]) -> bool:
    """
    Valida dados de uma linha (dict) verificando campos obrigatórios

    Args:
        row: dicionário com dados da linha
        fields: lista de campos obrigatórios

    Returns:
        bool: True se todos campos obrigatórios estão presentes e não-vazios

    Examples:
        >>> validate_row_data({"nome": "João", "email": "joao@example.com"}, ["nome", "email"])
        True
        >>> validate_row_data({"nome": "", "email": ""}, ["nome", "email"])
        False
    """
    # Verifica se todos os campos obrigatórios estão presentes e não-vazios
    for field in fields:
        value = row.get(field)
        if not value:  # None, "", ou ausente
            return False

    return True
