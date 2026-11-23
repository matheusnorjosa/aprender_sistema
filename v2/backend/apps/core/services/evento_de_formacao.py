"""Evento de formação e o Nº da formação (CON-09, plano aprovado pelo dono em 23/11/2026).

Evento de formação é o de tipo Presencial, Online ou Workshop, pelo nome sem acento e sem maiúscula. É a
definição única: nenhum outro lugar decide se o tipo é de formação. O nome do tipo é lido em outros pontos, para
outro fim: o título do Google trata "Acompanhamento" à parte (`gcal/payload.py`) e o comando de dev
`backfill_is_online` deduz a modalidade pelo nome. Quem renomear um tipo confere os três. O nome conta porque é
ele que vai ao título do evento no Google ("EF - Presencial"), e é pelo título que o DFF lê a formação.

O Nº da formação (`Solicitacao.encontro`) do evento de formação é só o número, de 1 a 999. Aceita "3º", "3°",
"03" e espaço nas pontas e guarda "3" (o título põe o "º"). Só algarismos comuns: "²" ou o "3" de largura cheia
quebrariam a leitura do título. Tipo que não é de formação segue com o campo livre.

Quem usa: o serializer (criar, criar em lote e editar evento que ainda não terminou; a marca e a falta do número
para a tela), `motivo_nao_publicavel` (Publicar, Reenviar e Reaplicar), a guarda do CREATE no `upsert_one` (por
onde passam o `preagenda_to_gcal` e o auto-apply), o lookup de tipos e a carga export-contract (lista no ensaio,
sem barrar).
"""

from __future__ import annotations

import re
import unicodedata
from typing import cast

from apps.core.models import Solicitacao, TipoEvento

TIPOS_DE_FORMACAO = frozenset({"presencial", "online", "workshop"})

MSG_NUMERO_DA_FORMACAO = (
    "Este tipo de evento pede o Nº da formação, que vai para o título do evento no Google: só o número, "
    "de 1 a 999 (ex.: 4)."
)

# [0-9] e não \d: \d aceita algarismo de outras escritas.
_NUMERO = re.compile(r"([0-9]{1,3})[º°]?")


def eh_tipo_de_formacao(nome: str | None) -> bool:
    """O tipo com este nome é de formação (Presencial, Online ou Workshop, sem acento e sem maiúscula)?"""
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", nome or "") if not unicodedata.combining(c))
    return sem_acento.strip().casefold() in TIPOS_DE_FORMACAO


def numero_da_formacao(valor: str | None) -> str | None:
    """O número como se guarda ("03º" vira "3"), ou None quando o valor não é um número de 1 a 999."""
    achado = _NUMERO.fullmatch((valor or "").strip())
    if achado is None:
        return None
    numero = int(achado.group(1))
    return str(numero) if 1 <= numero <= 999 else None


def eh_evento_de_formacao(s: Solicitacao) -> bool:
    """O tipo do evento é de formação."""
    tipo = cast(TipoEvento, s.tipo_evento)  # pyright: ignore[reportUnknownMemberType]  (FK sem tipo no model)
    return eh_tipo_de_formacao(tipo.nome)


def falta_numero_da_formacao(s: Solicitacao) -> bool:
    """O evento é de formação e está sem um Nº da formação válido."""
    return eh_evento_de_formacao(s) and numero_da_formacao(s.encontro) is None
