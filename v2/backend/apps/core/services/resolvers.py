"""
Funções para resolver Foreign Keys (FKs) a partir de nomes/emails.

Funções utilitárias para resolver entidades do banco a partir de texto,
usadas tanto pelo ETL quanto por validações em runtime.

Movido de dat_ingest/services/resolvers.py para desacoplar
ETL do sistema principal (Issue: decouple-etl).
"""

# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportReturnType=false

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.core.models import Municipio, Projeto, TipoEvento

from .normalize import norm_text

if TYPE_CHECKING:
    from apps.core.models import Usuario

User = get_user_model()


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
    Resolve usuário por nome completo (match simples).

    Tenta match exato em first_name + last_name (normalizado).
    Se não encontrar, tenta por partes do nome.

    Args:
        name: Nome completo do usuário

    Returns:
        Usuario ou None se não encontrado
    """
    if not name:
        return None

    name_norm = norm_text(name)

    # Tentativa 1: Match exato em first_name ou last_name
    user = User.objects.filter(Q(first_name__iexact=name_norm) | Q(last_name__iexact=name_norm)).first()

    if user:
        return user

    # Tentativa 2: Match por partes do nome (heurística)
    parts = name_norm.split()
    if len(parts) >= 2:
        first_part = parts[0]
        last_part = parts[-1]

        # Tenta primeiro nome + último nome
        user = User.objects.filter(first_name__icontains=first_part, last_name__icontains=last_part).first()

        if user:
            return user

        # Tentativa 3: Match mais relaxado (qualquer parte em qualquer nome)
        user = User.objects.filter(Q(first_name__icontains=first_part) | Q(last_name__icontains=last_part)).first()

        if user:
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


def _split_city_uf(raw: str | None) -> tuple[str, str | None]:
    """
    Separa município e UF de formatos variados:
    - "Cidade - UF"
    - "Cidade (UF)"
    - "Cidade/UF"

    Returns:
        (nome_cidade, uf) ou (texto_original, None) se não separou
    """
    if raw is None:
        return ("", None)

    txt = str(raw).strip()
    # Normaliza separadores (diferentes tipos de hífen)
    txt = txt.replace("–", "-").replace("—", "-").replace("/", "-")
    txt = re.sub(r"\s+", " ", txt)  # Collapse espaços

    # Padrão 1: "Cidade - UF"
    m = re.match(r"^(?P<nome>.+?)\s*-\s*(?P<uf>[A-Za-z]{2})$", txt)
    if not m:
        # Padrão 2: "Cidade (UF)"
        m = re.match(r"^(?P<nome>.+?)\s*\((?P<uf>[A-Za-z]{2})\)\s*$", txt)

    if m:
        nome = m.group("nome").strip()
        uf = m.group("uf").upper()
        return (nome, uf)

    return (txt, None)


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


def normalize_projeto_name(nome: str) -> str:
    """
    Normaliza nome de projeto aplicando aliases.

    ALIASES:
    - "IDEB" / "IDEB10" → "GESTÃO ESCOLAR"
    - "Vida & Ciências" → "VIDA E CIÊNCIAS"
    - "Vida & Linguagem" → "VIDA E LINGUAGEM"
    - "Vida & Matemática" → "VIDA E MATEMÁTICA"
    - "Cataventos" → "PROJETO CATAVENTO 2"
    - "Miudezas" → "PROJETO MIUDEZAS E DESCOBERTAS"
    - "ACerta" → "ACERTA MATEMATICA"
    - "Superativar" → "SUPERATIVAR - LINGUAGENS"
    - "Avançando Juntos Língua Portuguesa" → "AVANÇANDO JUNTOS PORTUGUÊS"

    Args:
        nome: Nome bruto do projeto

    Returns:
        Nome normalizado/mapeado
    """
    if not nome:
        return nome

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
    Resolve projeto por nome (setor canonizado).

    Aplica aliases (IDEB → GESTÃO ESCOLAR) antes de resolver.

    Args:
        nome: Nome do projeto (setor normalizado)

    Returns:
        Projeto ou None se não encontrado
    """
    if not nome:
        return None

    # PR20: Aplicar aliases antes de resolver
    nome_mapped = normalize_projeto_name(nome)
    nome_norm = norm_text(nome_mapped)

    try:
        return Projeto.objects.get(nome__iexact=nome_mapped)
    except Projeto.DoesNotExist:
        # Tenta com nome normalizado
        projetos = Projeto.objects.all()
        for p in projetos:
            if norm_text(p.nome) == nome_norm:
                return p
        return None
    except Projeto.MultipleObjectsReturned:
        return Projeto.objects.filter(nome__iexact=nome_mapped).first()


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

    try:
        return TipoEvento.objects.get(nome__iexact=nome)
    except TipoEvento.DoesNotExist:
        # Tenta com nome normalizado
        tipos = TipoEvento.objects.all()
        for t in tipos:
            if norm_text(t.nome) == nome_norm:
                return t
        return None
    except TipoEvento.MultipleObjectsReturned:
        return TipoEvento.objects.filter(nome__iexact=nome).first()
