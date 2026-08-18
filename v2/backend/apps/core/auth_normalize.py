"""SSOT da canonicalização do identificador de login (CPF ou username) — AS v2.

Motivação (M03-03 / #1614): antes, `CPFOrUsernameBackend.authenticate` removia a
pontuação do CPF para resolver a conta, mas o contador de lockout chaveava por
`username.lower()` cru. Resultado: cada grafia do mesmo CPF (com/sem pontos, hífens
ou espaços) caía num balde de lockout independente, enquanto todas autenticavam a
mesma conta — o lockout ficava sem teto efetivo.

Esta função é a fonte única: o backend de autenticação **e** a derivação da chave de
lockout consomem exatamente o mesmo valor canônico, de modo que todas as grafias de
um mesmo CPF colapsam num único balde.
"""

from __future__ import annotations

import re

# Mesma classe de caracteres que o backend historicamente removia do CPF
# (pontos, hífens e espaços, em qualquer quantidade/posição).
_LOGIN_PUNCT_RE = re.compile(r"[.\-\s]")

# Comprimento de um CPF só-dígitos.
_CPF_DIGITS = 11


def normalize_login_identifier(raw: str) -> str:
    """Canonicaliza o identificador EXATAMENTE como o backend resolve a conta.

    - Remove pontuação de CPF (``.``, ``-`` e espaços). Se o resultado for 11 dígitos,
      essa é a forma canônica do CPF — todas as grafias equivalentes colapsam nela.
    - Caso contrário, devolve o input **cru** (sem lowercase): é o valor com que o
      backend faz ``User.objects.get(username=...)`` (lookup case-sensitive), então
      preservá-lo garante que a chave de lockout case com a identidade que autentica.

    Não é mais agressiva que a normalização histórica do backend (só ``[.\\-\\s]``),
    para não quebrar login por ``username`` que contenha esses caracteres.
    """
    clean = _LOGIN_PUNCT_RE.sub("", raw)
    if len(clean) == _CPF_DIGITS and clean.isdigit():
        return clean
    return raw
