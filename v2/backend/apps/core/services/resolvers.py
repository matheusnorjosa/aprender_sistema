"""
Funções para resolver Foreign Keys (FKs) a partir de nomes/emails.

Funções utilitárias para resolver entidades do banco a partir de texto,
usadas tanto pelo ETL quanto por validações em runtime.

Movido de dat_ingest/services/resolvers.py para desacoplar
ETL do sistema principal (Issue: decouple-etl).
"""

# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportReturnType=false

from __future__ import annotations

import logging
import re
import unicodedata
from typing import TYPE_CHECKING, TypeVar

from django.contrib.auth import get_user_model

from apps.core.models import Municipio, Projeto, TipoEvento

from .normalize import norm_text

if TYPE_CHECKING:
    from apps.core.models import Usuario

User = get_user_model()

logger = logging.getLogger(__name__)

_M = TypeVar("_M")


def _pick_unique(hits: list[_M], *, kind: str, needle: str) -> tuple[str, _M | None]:
    """Escolhe um único candidato ou REJEITA ambiguidade (M02-09/#1613).

    Nunca escolhe "o primeiro" quando há mais de um alvo distinto: em vez de
    ``.first()`` (que gravava o alvo errado em silêncio), devolve ``ambiguous``
    e registra um WARNING com os candidatos, para o chamador tratar como
    pendência em vez de resolver no chute.

    Returns:
        ``("matched", obj)`` para exatamente 1 candidato distinto;
        ``("ambiguous", None)`` para 2+; ``("none", None)`` para 0.
    """
    unique = {getattr(h, "pk", id(h)): h for h in hits}
    if len(unique) == 1:
        return "matched", next(iter(unique.values()))
    if len(unique) > 1:
        candidatos = ", ".join(sorted(str(getattr(h, "nome", h)) for h in unique.values()))
        logger.warning(
            "%s ambíguo para %r: %d candidatos (%s) — rejeitado, não escolho no " "chute (M02-09/#1613).",
            kind,
            needle,
            len(unique),
            candidatos,
        )
        return "ambiguous", None
    return "none", None


def resolve_user_by_email(email: str) -> Usuario | None:
    """
    Resolve usuário por email (case-insensitive).

    Args:
        email: Email do usuário

    Returns:
        Usuario ou None se não encontrado
    """
    if not email:
        return None

    email_norm = email.strip().lower()

    try:
        return User.objects.get(email__iexact=email_norm)
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        # Se houver duplicatas, retorna o primeiro
        return User.objects.filter(email__iexact=email_norm).first()


def resolve_user_by_name(name: str) -> Usuario | None:
    """
    Resolve usuário por nome EXIGINDO candidato único em cada degrau (#1643).

    Escada determinística (reusa ``_pick_unique`` do #1613), comparando por
    ``norm_text`` dos DOIS lados (remove acento/caixa; simétrico, como
    ``resolve_projeto`` — ``icontains`` cru erraria nomes acentuados):

      1. nome completo exato (``get_full_name`` normalizado);
      2. todos os tokens do nome presentes nos tokens do usuário (subconjunto).

    Ambiguidade (2+ candidatos distintos) NUNCA vira chute: devolve ``None`` e
    loga WARNING (o chamador trata como pendência). Substitui as antigas
    Tentativas 2/3 (``icontains`` + ``.first()`` sem unicidade = match único
    errado silencioso).

    Args:
        name: Nome completo do usuário.

    Returns:
        Usuario para exatamente 1 candidato distinto; None para 0 ou ambiguidade.
    """
    if not name:
        return None

    name_norm = norm_text(name)
    tokens = set(name_norm.split())
    if not tokens:
        return None

    # Candidatos = usuários com nome preenchido. norm_text nos DOIS lados torna a
    # comparação acento/caixa-insensível. Tabela de usuários é pequena (interno),
    # mesmo padrão de resolve_projeto/resolve_tipo_evento.
    usuarios = [u for u in User.objects.all() if u.get_full_name().strip()]

    # Degrau 1: nome completo exato, único.
    status, user = _pick_unique(
        [u for u in usuarios if norm_text(u.get_full_name()) == name_norm],
        kind="Usuario (nome completo exato)",
        needle=name,
    )
    if status == "matched":
        return user
    if status == "ambiguous":
        return None

    # Degrau 2: todos os tokens do nome presentes nos tokens do usuário, único.
    status, user = _pick_unique(
        [u for u in usuarios if tokens <= set(norm_text(u.get_full_name()).split())],
        kind="Usuario (todos os tokens)",
        needle=name,
    )
    if status == "matched":
        return user

    return None


def _nfkd(value: str | None) -> str:
    """
    Normaliza string para comparação: NFKD + casefold + ASCII.

    Remove acentos e converte para minúsculas.
    """
    if value is None:
        return ""
    v = str(value).strip()
    v = " ".join(v.split())  # Collapse espaços
    v = unicodedata.normalize("NFKD", v).encode("ASCII", "ignore").decode("ASCII")
    return v.casefold()


# Comprimento máximo aceito para texto Município/UF antes de short-circuit.
# Guard defensivo (CodeQL py/polynomial-redos): mesmo o algoritmo sem regex
# evita processar entradas absurdas vindas de planilhas / API.
_MAX_CITY_UF_LEN = 200


def _split_city_uf(raw: str | None) -> tuple[str, str | None]:
    """
    Separa município e UF de formatos variados.

    Implementação sem regex backtracking (CodeQL py/polynomial-redos):
    usa ``rpartition`` / ``rfind`` por separadores conhecidos, em ordem
    de precedência. Cada operação é O(n).

    Formatos aceitos:
    - ``"Cidade - UF"``
    - ``"Cidade (UF)"``
    - ``"Cidade/UF"``
    - ``"Cidade, UF"``
    - ``"Cidade"`` (sem UF)

    Returns:
        ``(nome_cidade, uf)`` ou ``(texto_original, None)`` se não separou.
    """
    if raw is None:
        return ("", None)

    txt = str(raw).strip()
    # Defensive cap: entrada muito longa volta como-está sem tentar parse
    # (CodeQL py/polynomial-redos — limitar tamanho como segunda camada).
    if not txt or len(txt) > _MAX_CITY_UF_LEN:
        return (txt[:_MAX_CITY_UF_LEN], None)

    # Normaliza variantes de hífen para "-"; mantém os demais separadores
    # explícitos para o algoritmo abaixo.
    txt = txt.replace("–", "-").replace("—", "-")
    # Collapse espaços sem regex (split() trata qualquer whitespace).
    txt = " ".join(txt.split())

    # Padrão "Cidade (UF)" — UF em parênteses no final.
    if txt.endswith(")") and "(" in txt:
        before, sep, after = txt.rpartition("(")
        if sep == "(":
            candidate = after[:-1].strip()  # remove ")" final
            if _is_uf(candidate):
                return (before.strip(), candidate.upper())

    # Padrões "Cidade <sep> UF" — separadores em ordem de precedência
    # (mais específico primeiro para evitar match espúrio em nomes com
    # vírgula/hífen internos).
    for sep in (" - ", " – ", " — ", "/", ",", "-"):
        idx = txt.rfind(sep)
        if idx == -1:
            continue
        candidate = txt[idx + len(sep) :].strip()
        if _is_uf(candidate):
            return (txt[:idx].strip(), candidate.upper())

    return (txt, None)


def _is_uf(value: str) -> bool:
    """``True`` se ``value`` parece sigla de UF brasileira (2 letras ASCII)."""
    return len(value) == 2 and value.isascii() and value.isalpha()


def resolve_municipio(nome: str) -> Municipio | None:
    """
    Resolve município por nome, aceitando formatos variados:
    - "Cidade" (apenas nome)
    - "Cidade - UF"
    - "Cidade (UF)"
    - "Cidade/UF"

    Normaliza com NFKD (remove acentos) para matching robusto.

    Args:
        nome: Nome do município (pode incluir UF)

    Returns:
        Municipio ou None se não encontrado
    """
    if not nome:
        return None

    # 1) Tentar separar Cidade/UF
    cidade, uf = _split_city_uf(nome)
    cidade_nfkd = _nfkd(cidade)

    qs = Municipio.objects.all()

    # 2) Se UF veio, tentar match direto por (UF + nome case-insensitive)
    if uf:
        hit = qs.filter(uf=uf).filter(nome__iexact=cidade).first()
        if hit:
            return hit

    # 3) Fallback: match por nome exato (case-insensitive), sem UF
    hit = qs.filter(nome__iexact=cidade).first()
    if hit:
        return hit

    # 4) Fallback: compare NFKD casefold em Python (para acentos)
    for m in qs:
        m_nfkd = _nfkd(m.nome)
        if m_nfkd == cidade_nfkd:
            # Se UF foi especificada, validar
            if uf and m.uf != uf:
                continue
            return m

    # Não encontrado
    return None


_YEAR_PREFIX_RE = re.compile(r"^\d{4}\s+")

_NIVEL_MAP: dict[str, str] = {
    "Nível 1": "N1",
    "Nível 2": "N2",
    "Nível 3": "N3",
    "Nivel 1": "N1",
    "Nivel 2": "N2",
    "Nivel 3": "N3",
}


def _strip_year_prefix(nome: str) -> str:
    """Remove prefixo de ano (ex: '2026 ') do início do nome."""
    # Collapse múltiplos espaços antes de testar o padrão
    nome_clean = " ".join(nome.split())
    return _YEAR_PREFIX_RE.sub("", nome_clean).strip()


def normalize_projeto_name(nome: str) -> str:
    """
    Normaliza nome de projeto removendo prefixo de ano e aplicando aliases.

    Transformações aplicadas (em ordem):
    1. Strip de prefixo de ano: "2026 Novo Lendo" → "Novo Lendo"
    2. Normalização de nível: "Fluir das Emoções Nível 1" → "Fluir das Emoções N1"
    3. Aliases canônicos (IDEB, Vida &, Cataventos, etc.)

    Args:
        nome: Nome bruto do projeto (pode vir de CSV exportado das planilhas)

    Returns:
        Nome normalizado/mapeado
    """
    if not nome:
        return nome

    # 1) Strip prefixo de ano ("2026 ", "2025 ", etc.)
    nome = _strip_year_prefix(nome)
    if not nome:
        return nome

    # 2) Normalizar variantes de nível ("Nível X" → "NX")
    for nivel_raw, nivel_short in _NIVEL_MAP.items():
        nome = nome.replace(nivel_raw, nivel_short)

    # Normalizar: lowercase, sem acentos, trim
    nome_norm = norm_text(nome)

    # Mapeamento de aliases para nomes canônicos
    alias_map: dict[str, str] = {
        # IDEB → GESTÃO ESCOLAR
        "ideb": "GESTÃO ESCOLAR",
        "ideb10": "GESTÃO ESCOLAR",
        "ideb/ideb10": "GESTÃO ESCOLAR",
        "ideb 10": "GESTÃO ESCOLAR",
        "ideb-10": "GESTÃO ESCOLAR",
        # Vida & → VIDA E
        "vida & ciencias": "VIDA E CIÊNCIAS",
        "vida e ciencias": "VIDA E CIÊNCIAS",
        "vida & linguagem": "VIDA E LINGUAGEM",
        "vida e linguagem": "VIDA E LINGUAGEM",
        "vida & matematica": "VIDA E MATEMÁTICA",
        "vida e matematica": "VIDA E MATEMÁTICA",
        # Variações de projetos
        "cataventos": "PROJETO CATAVENTO 2",
        "catavento": "PROJETO CATAVENTO 2",
        "miudezas": "PROJETO MIUDEZAS E DESCOBERTAS",
        "acerta": "ACERTA MATEMATICA",
        "superativar": "SUPERATIVAR - LINGUAGENS",
        # Avançando Juntos
        "avancando juntos lingua portuguesa": "AVANÇANDO JUNTOS PORTUGUÊS",
        "avancando juntos portugues": "AVANÇANDO JUNTOS PORTUGUÊS",
    }

    if nome_norm in alias_map:
        return alias_map[nome_norm]

    # Retornar nome original (não normalizado) para manter case
    return nome


def resolve_projeto(nome: str) -> Projeto | None:
    """
    Resolve projeto por nome ou codigo.

    Estrategia:
    1. Tenta codigo exato (case-insensitive).
    2. Tenta nome bruto informado (exato e normalizado).
    3. Aplica aliases (IDEB -> GESTAO ESCOLAR, etc.) e tenta novamente.

    Args:
        nome: Nome/codigo do projeto

    Returns:
        Projeto ou None se não encontrado
    """
    if not nome:
        return None

    nome_raw = nome.strip()
    if not nome_raw:
        return None

    # Cada estágio REJEITA ambiguidade (M02-09/#1613): 2+ alvos distintos → None
    # + WARNING, em vez de escolher o primeiro no chute.

    # 1) Codigo exato
    status, projeto = _pick_unique(
        list(Projeto.objects.filter(codigo__iexact=nome_raw)),
        kind="Projeto (código)",
        needle=nome_raw,
    )
    if status == "matched":
        return projeto
    if status == "ambiguous":
        return None

    # 2) Nome bruto (exato)
    status, projeto = _pick_unique(
        list(Projeto.objects.filter(nome__iexact=nome_raw)),
        kind="Projeto (nome)",
        needle=nome_raw,
    )
    if status == "matched":
        return projeto
    if status == "ambiguous":
        return None

    # 2b) Nome normalizado (simétrico: NFKD dos DOIS lados)
    nome_raw_norm = norm_text(nome_raw)
    projetos = list(Projeto.objects.all())
    status, projeto = _pick_unique(
        [p for p in projetos if norm_text(p.nome) == nome_raw_norm],
        kind="Projeto (nome normalizado)",
        needle=nome_raw,
    )
    if status == "matched":
        return projeto
    if status == "ambiguous":
        return None

    # 3) Alias/canonizacao
    nome_mapped = normalize_projeto_name(nome_raw)
    if nome_mapped == nome_raw:
        return None

    status, projeto = _pick_unique(
        list(Projeto.objects.filter(codigo__iexact=nome_mapped)),
        kind="Projeto (código via alias)",
        needle=nome_mapped,
    )
    if status == "matched":
        return projeto
    if status == "ambiguous":
        return None

    status, projeto = _pick_unique(
        list(Projeto.objects.filter(nome__iexact=nome_mapped)),
        kind="Projeto (nome via alias)",
        needle=nome_mapped,
    )
    if status == "matched":
        return projeto
    if status == "ambiguous":
        return None

    nome_mapped_norm = norm_text(nome_mapped)
    status, projeto = _pick_unique(
        [p for p in projetos if norm_text(p.nome) == nome_mapped_norm],
        kind="Projeto (nome normalizado via alias)",
        needle=nome_mapped,
    )
    if status == "matched":
        return projeto

    return None


def resolve_tipo_evento(nome: str) -> TipoEvento | None:
    """
    Resolve tipo de evento por nome.

    Args:
        nome: Nome do tipo de evento

    Returns:
        TipoEvento ou None se não encontrado
    """
    if not nome:
        return None

    nome_norm = norm_text(nome)

    # 1) Nome exato (case-insensitive) — REJEITA ambiguidade (M02-09/#1613):
    # 2+ tipos com o mesmo nome → None, em vez do antigo .first() no chute.
    status, tipo = _pick_unique(
        list(TipoEvento.objects.filter(nome__iexact=nome)),
        kind="TipoEvento (nome)",
        needle=nome,
    )
    if status == "matched":
        return tipo
    if status == "ambiguous":
        return None

    # 2) Nome normalizado (NFKD dos dois lados)
    status, tipo = _pick_unique(
        [t for t in TipoEvento.objects.all() if norm_text(t.nome) == nome_norm],
        kind="TipoEvento (nome normalizado)",
        needle=nome,
    )
    if status == "matched":
        return tipo

    return None
