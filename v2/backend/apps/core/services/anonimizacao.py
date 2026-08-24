# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false

"""LGPD art. 18-VI — anonimizacao de Usuario (direito ao esquecimento).

O hard-delete de Usuario e' barrado por FKs PROTECT (Solicitacao,
AvailabilityBlock, dat_*): qualquer titular com historico dispara
`ProtectedError`. A via LGPD-correta nesse caso e' ANONIMIZAR — remover a PII e
MANTER a linha, preservando a integridade referencial dos registros de negocio.

Idempotente. Audita `USER_ANONYMIZE` no MESMO `atomic()` da mutacao — padrao do
servico transacional de auditoria (#1672): em autocommit (o projeto nao seta
`ATOMIC_REQUESTS`) o `on_commit` dispararia ANTES do save e deixaria
trilha-fantasma se a mutacao falhasse. Ver `apps.core.services.audit`.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.core.imports.normalization import normalize_cpf_digits
from apps.core.models import AuditLog, DATCoordenador, GoogleOAuthCredential, Usuario
from apps.core.services.audit import registrar_auditoria

# PII scrubbada — SSOT p/ o `details` da auditoria e p/ os testes.
CAMPOS_ANONIMIZADOS: tuple[str, ...] = (
    "cpf",
    "username",
    "first_name",
    "last_name",
    "email",
    "telefone",
    "cargo",
)

# Prefixo do username anonimo; serve tambem de sentinela de idempotencia.
_ANON_USERNAME_PREFIX = "anon_"

# PII do DATCoordenador scrubbada quando o titular (mesmo CPF) e' esquecido. O CPF novo
# (opcao A #1837) e' a chave de join que finalmente permite o direito ao esquecimento
# alcancar o coordenador — cuja PII (nome/email/telefone) ate' entao ficava orfa.
CAMPOS_ANONIMIZADOS_COORD: tuple[str, ...] = (
    "nome",
    "email",
    "email_alternativo",
    "telefone",
    "telefone_alternativo",
    "cargo",
    "foto_url",
    "observacoes",
    "cpf",
)

# Chave do cache de options do coordenador (serve `nome` por 5 min; sem signal de invalidacao).
_COORD_OPTIONS_CACHE_KEY = "static_endpoint:coordenadores_options"


def usuario_anonimizado(usuario: Usuario) -> bool:
    """True se `usuario` ja foi anonimizado (para tornar a operacao idempotente)."""
    return usuario.username.startswith(_ANON_USERNAME_PREFIX) and not usuario.is_active


def _cpf_tombstone(pk: int) -> str:
    """Marcador unico p/ o campo `cpf` (unique + NOT NULL, max_length=11).

    Nao pode ser NULL nem colidir com um CPF real (11 digitos). `ANON` + pk
    zero-paddeado cabe em 11 chars ate ~10M usuarios e nunca casa o regex de CPF.
    """
    return f"ANON{pk:07d}"[:11]


def _coordenador_nome_tombstone(pk: int) -> str:
    """Marcador do `nome` (NOT NULL, sem blank): `""` quebraria full_clean/__str__/ordering."""
    return f"Coordenador anonimizado #{pk}"[:200]


def _anonimizar_coordenadores_por_cpf(cpf_original: Any, actor: Any) -> int:
    """Scrubba a PII de todo `DATCoordenador` cujo CPF == o do titular (chave de join).

    Guard OBRIGATORIO: so' filtra com 11 digitos exatos — senao um `cpf` vazio/tombstone
    (`""`, `ANON…`) casaria em massa e apagaria coordenadores nao relacionados. NAO usa
    `is_valid_cpf` (mod-11): CPF legado malformado ainda tem direito a erasure. Roda DENTRO
    do `atomic()` do caller. Retorna a contagem (para a trilha — nunca a PII).
    """
    digits = normalize_cpf_digits(cpf_original)
    if len(digits) != 11:
        return 0
    updated_by = actor if (actor is not None and getattr(actor, "is_authenticated", False)) else None
    count = 0
    for coord in DATCoordenador.objects.filter(cpf=digits):
        coord.nome = _coordenador_nome_tombstone(coord.pk)
        coord.email = ""
        coord.email_alternativo = ""
        coord.telefone = ""
        coord.telefone_alternativo = ""
        coord.cargo = ""
        coord.foto_url = ""
        coord.observacoes = ""
        coord.cpf = None
        coord.ativo = False
        coord.updated_by = updated_by
        coord.save(
            update_fields=[
                "nome",
                "email",
                "email_alternativo",
                "telefone",
                "telefone_alternativo",
                "cargo",
                "foto_url",
                "observacoes",
                "cpf",
                "ativo",
                "updated_by",
                "updated_at",
            ]
        )
        count += 1
    if count:
        # o endpoint de options serve `nome` por 5 min e nada invalida em write de coordenador.
        transaction.on_commit(lambda: cache.delete(_COORD_OPTIONS_CACHE_KEY))
    return count


def anonimizar_usuario(*, usuario: Usuario, actor: Any) -> bool:
    """Anonimiza a PII de `usuario`, preservando a linha e as FKs.

    - Scrubba os campos de `CAMPOS_ANONIMIZADOS`, desativa a conta e torna a
      senha inutilizavel.
    - Remove a credencial Google OAuth (google_email + tokens = PII do titular).
    - Audita `USER_ANONYMIZE` (o FATO — NUNCA os valores antigos de PII, para nao
      re-introduzir dado pessoal na trilha).

    Retorna True se anonimizou; False se ja estava anonimizado (idempotente).
    """
    if usuario_anonimizado(usuario):
        return False

    target_pk: int = usuario.pk
    # CPF cru ANTES do tombstone (`:cpf =` abaixo) — e' a chave para alcancar o coordenador.
    cpf_original = usuario.cpf

    with transaction.atomic():
        deleted_oauth, _ = GoogleOAuthCredential.objects.filter(user=usuario).delete()

        usuario.cpf = _cpf_tombstone(target_pk)
        usuario.username = f"{_ANON_USERNAME_PREFIX}{target_pk}"
        usuario.first_name = ""
        usuario.last_name = ""
        usuario.email = ""
        usuario.telefone = ""
        usuario.cargo = ""
        usuario.is_active = False
        usuario.set_unusable_password()
        usuario.save(
            update_fields=[
                "cpf",
                "username",
                "first_name",
                "last_name",
                "email",
                "telefone",
                "cargo",
                "is_active",
                "password",
            ]
        )

        # Reach por CPF ao DATCoordenador (mesma pessoa) — DENTRO do atomic, ANTES da auditoria
        # (o `on_commit` da trilha materializa `details` por valor; a contagem precisa ja' existir).
        coordenadores_anonimizados = _anonimizar_coordenadores_por_cpf(cpf_original, actor)

        actor_id = getattr(actor, "id", None) if getattr(actor, "is_authenticated", False) else None
        registrar_auditoria(
            actor=actor,
            action=AuditLog.Action.USER_ANONYMIZE,
            model_name="Usuario",
            details={
                "actor_user_id": actor_id,
                "target_user_id": target_pk,
                "campos_anonimizados": list(CAMPOS_ANONIMIZADOS),
                "oauth_removido": deleted_oauth > 0,
                "coordenadores_anonimizados": coordenadores_anonimizados,
                "campos_anonimizados_coordenador": list(CAMPOS_ANONIMIZADOS_COORD),
            },
        )
    return True
