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

from django.db import transaction

from apps.core.models import AuditLog, GoogleOAuthCredential, Usuario
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


def usuario_anonimizado(usuario: Usuario) -> bool:
    """True se `usuario` ja foi anonimizado (para tornar a operacao idempotente)."""
    return usuario.username.startswith(_ANON_USERNAME_PREFIX) and not usuario.is_active


def _cpf_tombstone(pk: int) -> str:
    """Marcador unico p/ o campo `cpf` (unique + NOT NULL, max_length=11).

    Nao pode ser NULL nem colidir com um CPF real (11 digitos). `ANON` + pk
    zero-paddeado cabe em 11 chars ate ~10M usuarios e nunca casa o regex de CPF.
    """
    return f"ANON{pk:07d}"[:11]


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
            },
        )
    return True
