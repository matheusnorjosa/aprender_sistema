"""Redacao central de PII (LGPD art. 46) para caminhos de PERSISTENCIA.

O `PIIRedactionFilter` (logging_filters.py) protege o pipeline de LOGS. Este modulo
cobre o que o filtro de log nao alcanca: valores que vao para o banco (ex.: o JSONField
`AuditLog.details`). Um helper por tipo de dado sensivel, reusavel na escrita e na leitura.
"""

from __future__ import annotations

import re
from typing import Any, cast

from django.db.models import Q

# CPF nas DUAS formas: 11 digitos crus OU formatado 000.000.000-00. As ancoras `\b`
# garantem que so o TOKEN inteiro casa — um username como `user_<hex>` (digitos cercados
# de word-chars) NAO tem fronteira de palavra no meio e por isso nunca e alterado.
_CPF_RE = re.compile(r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})\b")

# Convencao alinhada ao PIIRedactionFilter dos logs (logging_filters.py).
_CPF_PLACEHOLDER = "<cpf>"

# Conta importada sem e-mail recebe `<cpf>@placeholder.local` (services/usuarios_import.py):
# não é caixa de verdade e leva o CPF.
EMAIL_DE_RESERVA_SUFIXO = "@placeholder.local"


def redact_cpf(value: Any) -> Any:
    """Troca qualquer CPF (cru ou formatado) por `<cpf>`; no-op se nao houver CPF.

    Defensivo para JSONField heterogeneo: valores nao-string voltam intactos.
    """
    if not isinstance(value, str):
        return value
    return _CPF_RE.sub(_CPF_PLACEHOLDER, value)


def email_de_reserva(email: str) -> bool:
    """True para o e-mail `<cpf>@placeholder.local` dado a conta importada sem e-mail."""
    return email.strip().lower().endswith(EMAIL_DE_RESERVA_SUFIXO)


def email_sem_cpf(email: str | None) -> str | None:
    """E-mail para mostrar fora da administração de contas: None se for o de reserva ou levar CPF."""
    if not email or email_de_reserva(email) or redact_cpf(email) != email:
        return None
    return email


def busca_por_nome(q: str, prefixo: str = "") -> Q:
    """Busca de pessoa por nome (`icontains`), sem virar oráculo de CPF (S5, C6).

    O e-mail entra só quando o termo não tem dígito: sem dígito não há pedaço de CPF a testar,
    e o e-mail (sem acento) é o que acha "Conceição" por quem digita "conceicao".
    `prefixo` é o caminho até o usuário (ex.: `"usuario__"`).
    """
    campos = ["first_name", "last_name"]
    if not any(c.isdigit() for c in q):
        campos.append("email")
    return Q(*[(f"{prefixo}{campo}__icontains", q) for campo in campos], _connector=Q.OR)


def redact_cpf_deep(value: Any) -> Any:
    """`redact_cpf` em todo texto de um valor JSON (dict e lista inclusive); o resto volta intacto.

    Para ler `AuditLog.details` gravado antes da redação na escrita (S5: a mensagem de erro do
    GCal levava o login, que é o CPF).
    """
    if isinstance(value, dict):
        return {k: redact_cpf_deep(v) for k, v in cast(dict[Any, Any], value).items()}
    if isinstance(value, list):
        return [redact_cpf_deep(v) for v in cast(list[Any], value)]
    return redact_cpf(value)


# O login aceita qualquer mistura de `.`, `-` e espaço (`auth_normalize`).
_LOGIN_PUNCT_RE = re.compile(r"[.\-\s]")
# CPF digitado com um ou dois dígitos a menos ou a mais ainda é o CPF de alguém.
_MIN_DIGITOS_CPF_DIGITADO = 9


def redact_login_identifier(value: Any) -> Any:
    """Identificador digitado no login, sem CPF em nenhuma grafia (S5, AuditLog de login).

    Só dígitos e pontuação de CPF, com 9 ou mais dígitos: vira `<cpf>` (cobre grafias que o
    `redact_cpf` não reconhece e CPF digitado errado). Fora isso, `redact_cpf` limpa um CPF
    no meio do texto. Não-string volta intacto.
    """
    if not isinstance(value, str):
        return value
    digitos = _LOGIN_PUNCT_RE.sub("", value)
    if digitos.isdigit() and len(digitos) >= _MIN_DIGITOS_CPF_DIGITADO:
        return _CPF_PLACEHOLDER
    return redact_cpf(value)
