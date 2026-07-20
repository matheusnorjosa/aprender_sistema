"""
Validação de CPF (mod-11) — SSOT reutilizável do backend.

Criado para a #1578: o importer export-contract (e futuros callers) precisam
REJEITAR CPF estruturalmente inválido, não apenas checar ``len == 11``. O model
``Usuario.cpf`` só tem ``RegexValidator(r"^\\d{11}$")`` (comprimento), então a
validação de dígitos verificadores vive aqui, na camada de aplicação, sem tocar
o model (que exigiria migration e afetaria dado real em produção).

Funções puras: sem I/O, sem ORM, sem mutação. Entrada tolerante (``None`` / com
máscara / dígitos) — conta apenas os dígitos via ``normalize_cpf_digits`` (SSOT
de normalização de import).
"""

from __future__ import annotations

from typing import Final

from apps.core.imports.normalization import normalize_cpf_digits

__all__ = [
    "CPF_ABSENT",
    "CPF_INVALID",
    "CPF_VALID",
    "classify_cpf",
    "is_cpf_placeholder",
    "is_valid_cpf",
    "normalize_cpf",
]

# Estados retornados por ``classify_cpf``.
CPF_VALID: Final[str] = "valid"
CPF_INVALID: Final[str] = "invalid"
CPF_ABSENT: Final[str] = "absent"

_CPF_LEN: Final[int] = 11


def normalize_cpf(raw: object) -> str:
    """Retorna só os dígitos de ``raw`` (tolera ``None``/máscara). Não valida."""
    return normalize_cpf_digits(raw)


def is_cpf_placeholder(raw: object) -> bool:
    """
    ``True`` para sequências de dígito repetido (``00000000000`` até
    ``99999999999``).

    Esses valores passam na aritmética do dígito verificador, mas são inválidos
    por definição — usados como placeholder / "sem CPF". A #1578 os trata como
    AUSENTES (não como "CPF inválido").
    """
    digits = normalize_cpf(raw)
    return len(digits) == _CPF_LEN and digits == digits[0] * _CPF_LEN


def _check_digit(digits: str, first_weight: int) -> str:
    """Dígito verificador mod-11 de ``digits`` com pesos ``first_weight``..2."""
    total = sum(int(d) * w for d, w in zip(digits, range(first_weight, 1, -1)))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def is_valid_cpf(raw: object) -> bool:
    """
    ``True`` se ``raw`` é um CPF estruturalmente válido: exatamente 11 dígitos,
    não é placeholder de dígito repetido, e os dois dígitos verificadores mod-11
    conferem.
    """
    digits = normalize_cpf(raw)
    if len(digits) != _CPF_LEN or is_cpf_placeholder(digits):
        return False
    return digits[9] == _check_digit(digits[:9], 10) and digits[10] == _check_digit(digits[:10], 11)


def classify_cpf(raw: object) -> str:
    """
    Classifica ``raw`` em três estados, para o relatório de import distinguir os
    motivos de skip (#1578):

    - ``CPF_ABSENT``  : vazio OU placeholder de dígito repetido → tratar como
      ausente (não é NK, não é "inválido").
    - ``CPF_VALID``   : dígitos verificadores mod-11 conferem.
    - ``CPF_INVALID`` : tem dígitos, não é placeholder, mas é estruturalmente
      inválido (comprimento ≠ 11 ou DV errado).
    """
    digits = normalize_cpf(raw)
    if not digits or is_cpf_placeholder(digits):
        return CPF_ABSENT
    return CPF_VALID if is_valid_cpf(digits) else CPF_INVALID
