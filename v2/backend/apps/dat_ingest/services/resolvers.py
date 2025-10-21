"""
Funções para resolver Foreign Keys (FKs) a partir de nomes/emails.

Usado pelo ETL de Acompanhamento para encontrar objetos existentes no banco.
"""

from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.core.models import Municipio, Projeto, TipoEvento
from .acompanhamento_normalize import norm_text


User = get_user_model()


def resolve_user_by_email(email: str) -> Optional[User]:
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


def resolve_user_by_name(name: str) -> Optional[User]:
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

    # Tenta match exato em nome completo
    users = User.objects.annotate(
        full_name_lower=Q(
            Q(first_name__isnull=False) & Q(last_name__isnull=False),
            then=Q(first_name__iexact=name_norm) | Q(last_name__iexact=name_norm),
        )
    ).filter(full_name_lower=True)

    if users.exists():
        return users.first()

    # Fallback: tenta por partes do nome
    parts = name_norm.split()
    if len(parts) >= 2:
        first_part = parts[0]
        last_part = parts[-1]

        users = User.objects.filter(
            Q(first_name__icontains=first_part) & Q(last_name__icontains=last_part)
        )

        if users.exists():
            return users.first()

    return None


def resolve_municipio(nome: str) -> Optional[Municipio]:
    """
    Resolve município por nome (normalizado).

    Args:
        nome: Nome do município

    Returns:
        Municipio ou None se não encontrado
    """
    if not nome:
        return None

    nome_norm = norm_text(nome)

    try:
        return Municipio.objects.get(nome__iexact=nome)
    except Municipio.DoesNotExist:
        # Tenta com nome normalizado
        municipios = Municipio.objects.all()
        for m in municipios:
            if norm_text(m.nome) == nome_norm:
                return m
        return None
    except Municipio.MultipleObjectsReturned:
        return Municipio.objects.filter(nome__iexact=nome).first()


def resolve_projeto(nome: str) -> Optional[Projeto]:
    """
    Resolve projeto por nome (setor canonizado).

    Args:
        nome: Nome do projeto (setor normalizado)

    Returns:
        Projeto ou None se não encontrado
    """
    if not nome:
        return None

    nome_norm = norm_text(nome)

    try:
        return Projeto.objects.get(nome__iexact=nome)
    except Projeto.DoesNotExist:
        # Tenta com nome normalizado
        projetos = Projeto.objects.all()
        for p in projetos:
            if norm_text(p.nome) == nome_norm:
                return p
        return None
    except Projeto.MultipleObjectsReturned:
        return Projeto.objects.filter(nome__iexact=nome).first()


def resolve_tipo_evento(nome: str) -> Optional[TipoEvento]:
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
