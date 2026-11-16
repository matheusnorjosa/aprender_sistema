"""
Token Manager - §7 Epic #459

Handles encryption, decryption, refresh, and rotation of OAuth tokens.
Extracted from google_oauth.py to separate token management concerns.

Security features:
- Fernet encryption (AES-128-CBC + HMAC-SHA256)
- Thread-safe refresh with select_for_update (GAP-1)
- Zero-downtime key rotation (GAP-2)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import OuterRef, QuerySet, Subquery
from django.utils import timezone

import requests
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from apps.core.models import AuditLog, GoogleOAuthCredential, Usuario
from apps.core.services.db_retry import retry_on_deadlock

logger: logging.Logger = logging.getLogger(__name__)

# `details.status` do AuditLog GOOGLE_DISCONNECT quando o SISTEMA removeu a credencial
# (invalid_grant). O "Desconectar" da pessoa grava `status="success"`.
AUTO_REMOVED = "auto_removed"


# ============================================================================
# ENCRYPTION (GAP-2: Chave dedicada)
# ============================================================================


class OAuthNaoConfiguradoError(ValueError):
    """O servidor não tem `GCAL_OAUTH_CLIENT_ID`/`GCAL_OAUTH_CLIENT_SECRET`: o cliente do Google não monta.

    Subclasse de `ValueError` para quem já trata `ValueError` seguir igual; a view de listar
    calendários a separa para devolver 409 tratado em vez de 500 (ensaio r3, 28/10/2026).
    """


def _get_fernet_key() -> bytes:
    """
    Retorna chave Fernet dedicada para criptografia de tokens OAuth.

    Prioridade:
    1. GCAL_ENCRYPTION_KEY (obrigatória em produção)
    2. Fallback: SECRET_KEY (apenas dev/staging com warning)

    Raises:
        ValueError: Se nenhuma chave válida for encontrada
    """
    key: str | None = os.getenv("GCAL_ENCRYPTION_KEY")

    if key:
        return key.encode("utf-8")

    # Fallback para SECRET_KEY (dev/staging apenas)
    if settings.ENVIRONMENT != "production":
        logger.warning(
            "⚠️ GCAL_ENCRYPTION_KEY não definida. Usando SECRET_KEY (não recomendado). "
            "Defina GCAL_ENCRYPTION_KEY para produção."
        )
        # Derivar chave Fernet-compatible de SECRET_KEY
        from hashlib import sha256

        return base64.urlsafe_b64encode(sha256(settings.SECRET_KEY.encode()).digest())

    raise ValueError(
        "❌ GCAL_ENCRYPTION_KEY obrigatória em produção. "
        "Gere com: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )


def _get_fallback_keys() -> list[str]:
    """Chaves antigas, só para decifrar: `GCAL_ENCRYPTION_KEY_FALLBACKS`, separadas por vírgula (FER-59)."""
    raw: str = os.getenv("GCAL_ENCRYPTION_KEY_FALLBACKS", "")
    return [key.strip() for key in raw.split(",") if key.strip()]


def _get_multifernet() -> MultiFernet:
    """
    Cifra com a chave principal (`GCAL_ENCRYPTION_KEY`) e decifra com ela ou com qualquer fallback.

    É o que deixa a troca de chave sem parada: com a nova como principal e a antiga em
    `GCAL_ENCRYPTION_KEY_FALLBACKS`, o que já está no banco continua abrindo enquanto
    `rotate_encryption_key()` recifra tudo.

    Raises:
        ValueError: chave principal ausente em produção, ou alguma fallback malformada
            (a mensagem nunca mostra a chave).
    """
    fernets: list[Fernet] = [Fernet(_get_fernet_key())]
    for position, key in enumerate(_get_fallback_keys(), start=1):
        try:
            fernets.append(Fernet(key.encode("utf-8")))
        except ValueError:
            raise ValueError(
                f"GCAL_ENCRYPTION_KEY_FALLBACKS: a chave na posição {position} não é uma chave Fernet válida."
            ) from None
    return MultiFernet(fernets)


def encrypt_token(token: str) -> bytes:
    """
    Criptografa token usando Fernet (AES-128-CBC + HMAC-SHA256) com a chave principal.

    Args:
        token: Token em plaintext (access_token ou refresh_token)

    Returns:
        bytes: Token criptografado (formato Fernet)

    Raises:
        ValueError: Se chave de criptografia não estiver configurada
    """
    return _get_multifernet().encrypt(token.encode("utf-8"))


def decrypt_token(encrypted: bytes | memoryview) -> str:
    """
    Descriptografa token criptografado com Fernet (chave principal ou qualquer fallback).

    Args:
        encrypted: Token criptografado (bytes ou memoryview do PostgreSQL)

    Returns:
        str: Token em plaintext

    Raises:
        InvalidToken: Se token estiver corrompido ou nenhuma chave configurada o abrir
    """
    if isinstance(encrypted, memoryview):
        encrypted = bytes(encrypted)
    return _get_multifernet().decrypt(encrypted).decode("utf-8")


# Aliases for backward compatibility (used internally with underscore prefix)
_encrypt_token = encrypt_token
_decrypt_token = decrypt_token


# ============================================================================
# TOKEN REFRESH (GAP-1: Concorrência)
# ============================================================================


@retry_on_deadlock(operation="oauth.refresh_access_token")
def refresh_access_token_safe(credential: GoogleOAuthCredential, *, force: bool = False) -> GoogleOAuthCredential:
    """
    Atualiza access_token usando refresh_token (thread-safe).

    **Concorrência (GAP-1)**:
    - Usa select_for_update() para row-level lock (PostgreSQL)
    - Double-check pattern: verifica se outro thread já refrescou
    - Previne race conditions em refresh simultâneos

    Args:
        credential: Instância de GoogleOAuthCredential a ser atualizada
        force: pula o double-check e chama o Google mesmo com token válido — é o que prova que
            o refresh_token ainda vive (job diário `probe_google_credentials`, #2039)

    Returns:
        GoogleOAuthCredential: Credencial atualizada (re-fetched do DB)

    Raises:
        ValueError: Se refresh_token inválido (invalid_grant)
        Exception: Se Google API retornar erro

    Example:
        >>> credential = request.user.google_oauth
        >>> if credential.is_expired():
        ...     credential = refresh_access_token_safe(credential)
        >>> # Usar credential.access_token_encrypted atualizado
    """
    with transaction.atomic():
        # Row-level lock (GAP-1: Concorrência)
        try:
            cred: GoogleOAuthCredential = GoogleOAuthCredential.objects.select_for_update().get(id=credential.id)
        except GoogleOAuthCredential.DoesNotExist:
            # Corrida: outra task removeu a credencial enquanto esta esperava o lock. A pessoa vê a
            # orientação de reconectar, não o erro cru do ORM.
            raise ValueError("Sua conta Google foi desconectada. Conecte sua conta Google de novo.") from None

        # Double-check: outro thread já refrescou?
        if not force and cred.token_expiry > timezone.now() + timedelta(minutes=5):
            logger.info(f"✅ Token já válido (outro thread refrescou). " f"Expira em: {cred.token_expiry}")
            return cred

        # Refresh via Google API
        client_id: str | None = os.getenv("GCAL_OAUTH_CLIENT_ID")
        client_secret: str | None = os.getenv("GCAL_OAUTH_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise OAuthNaoConfiguradoError("❌ GCAL_OAUTH_CLIENT_ID e GCAL_OAUTH_CLIENT_SECRET não configuradas")

        refresh_token: str = decrypt_token(cred.refresh_token_encrypted)

        token_url: str = "https://oauth2.googleapis.com/token"
        payload: dict[str, str] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        logger.info("🔄 Refreshing access token: credencial #%s", cred.pk)  # sem e-mail no log (LGPD)

        try:
            response: requests.Response = requests.post(
                token_url, data=payload, timeout=settings.GCAL_OAUTH_TOKEN_TIMEOUT
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            # Atualizar credencial
            cred.access_token_encrypted = encrypt_token(data["access_token"])
            cred.token_expiry = timezone.now() + timedelta(seconds=data.get("expires_in", 3600))
            cred.save(update_fields=["access_token_encrypted", "token_expiry", "updated_at"])

            logger.info(f"✅ Access token refreshed. Nova expiração: {cred.token_expiry}")

            # Auditoria (PA-05)
            AuditLog.objects.create(
                usuario=cred.user,
                action=AuditLog.Action.GOOGLE_REFRESH_TOKEN,
                model_name="GoogleOAuthCredential",
                details={
                    "google_email": cred.google_email,
                    "new_expiry": cred.token_expiry.isoformat(),
                    "status": "success",
                },
            )

            return cred

        except requests.exceptions.HTTPError as e:
            # invalid_grant: refresh_token revogado pelo usuário
            if e.response.status_code == 400 and e.response.json().get("error") == "invalid_grant":
                # Sem e-mail no log (LGPD): o id basta para achar a credencial no AuditLog.
                logger.error("❌ Refresh token inválido (revogado): credencial #%s removida", cred.pk)

                # Remover credencial (usuário precisa reconectar)
                cred.delete()

                # Auditoria (PA-05)
                AuditLog.objects.create(
                    usuario=cred.user,
                    action=AuditLog.Action.GOOGLE_DISCONNECT,
                    model_name="GoogleOAuthCredential",
                    details={
                        "google_email": cred.google_email,
                        "reason": "invalid_grant (refresh token revogado pelo usuário)",
                        "status": AUTO_REMOVED,
                    },
                )
            else:
                logger.error(f"❌ Erro ao refresh access token: {e}")
                raise Exception(f"Falha ao atualizar token Google: {str(e)}")

    # M12-10: o erro sai FORA do atomic. Levantado dentro, o rollback desfazia o delete e o
    # audit acima — a credencial revogada nunca sumia e ninguém ficava sabendo.
    raise ValueError("Sua conexão com o Google foi revogada. Conecte sua conta Google de novo.")


def usuarios_para_reconectar() -> QuerySet[Usuario]:
    """Pessoas ativas cuja conexão Google o SISTEMA removeu (invalid_grant) e que não reconectaram.

    Regra: sem credencial E o último evento de conexão da pessoa no AuditLog (`GOOGLE_CONNECT` /
    `GOOGLE_DISCONNECT`) é uma remoção automática. O "Desconectar" manual não conta (#2039).
    """
    ultimo_evento = (
        AuditLog.objects.filter(
            usuario=OuterRef("pk"),
            action__in=[AuditLog.Action.GOOGLE_CONNECT, AuditLog.Action.GOOGLE_DISCONNECT],
        )
        .order_by("-created_at", "-pk")
        .values("pk")[:1]
    )
    remocoes_automaticas = AuditLog.objects.filter(
        action=AuditLog.Action.GOOGLE_DISCONNECT, details__status=AUTO_REMOVED
    ).values("pk")
    return (
        Usuario.objects.filter(is_active=True, google_oauth__isnull=True)
        .annotate(ultimo_evento_google=Subquery(ultimo_evento))
        .filter(ultimo_evento_google__in=remocoes_automaticas)
    )


def revoke_token(credential: GoogleOAuthCredential) -> bool:
    """
    Revoga refresh_token no Google e remove credencial local.

    Args:
        credential: Instância de GoogleOAuthCredential a ser revogada

    Returns:
        bool: True se revogado com sucesso, False caso contrário

    Example:
        >>> credential = request.user.google_oauth
        >>> if revoke_token(credential):
        ...     messages.success(request, "Conta Google desconectada com sucesso")
    """
    try:
        # Descriptografar refresh_token
        refresh_token: str = decrypt_token(credential.refresh_token_encrypted)

        # Revogar no Google
        revoke_url: str = "https://oauth2.googleapis.com/revoke"
        payload: dict[str, str] = {"token": refresh_token}

        logger.info(f"🔓 Revogando refresh token para {credential.google_email}")

        response: requests.Response = requests.post(revoke_url, data=payload, timeout=settings.GCAL_OAUTH_TOKEN_TIMEOUT)

        # 200 OK: revogado com sucesso. 400: token já inválido no Google (também
        # efetivamente revogado). Qualquer OUTRO status = revogação NÃO confirmada →
        # S4 (#1742): NÃO apagar a credencial local, senão o refresh_token fica vivo
        # no Google e órfão localmente (sem como retentar). Preserva p/ retry + sinaliza
        # falha. (Exceções de rede já caem no except abaixo, que também preserva.)
        if response.status_code not in [200, 400]:
            logger.error(
                f"❌ Revoke Google retornou status {response.status_code}; " "credencial local preservada para retry"
            )
            return False

        # Revogado com sucesso → remover credencial local
        user: Usuario = credential.user
        google_email: str = credential.google_email
        credential.delete()

        # Auditoria (PA-05)
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.GOOGLE_DISCONNECT,
            model_name="GoogleOAuthCredential",
            details={
                "google_email": google_email,
                "reason": "user_requested",
                "status": "success",
            },
        )

        logger.info(f"✅ Credencial removida: {google_email}")
        return True

    except Exception as e:
        logger.error(f"❌ Erro ao revogar token: {e}")
        return False


# ============================================================================
# KEY ROTATION (GAP-2)
# ============================================================================


@dataclass(frozen=True)
class RotacaoResultado:
    """Resultado de `rotate_encryption_key()` (FER-59).

    `so_com_fallback` conta as credenciais que NÃO abriam com a principal antes da rotação.
    Zero com credenciais no banco quer dizer que a chave não mudou neste processo
    (ex.: `GCAL_ENCRYPTION_KEY` ainda com a antiga) ou que tudo já tinha sido recifrado.
    """

    recifradas: int
    so_com_fallback: int


def rotate_encryption_key() -> RotacaoResultado:
    """
    Recifra todos os tokens com a chave principal (`GCAL_ENCRYPTION_KEY`), sem parada (FER-59).

    **Troca de chave sem parada** (passo a passo: GUIDE_GCAL.md, seção 8):
    1. `GCAL_ENCRYPTION_KEY_FALLBACKS=<nova>` e reiniciar (todo processo já abre a nova);
    2. `GCAL_ENCRYPTION_KEY=<nova>` e `GCAL_ENCRYPTION_KEY_FALLBACKS=<antiga>` e reiniciar
       (o sistema segue abrindo os tokens antigos e já cifra os novos com a nova);
    3. Rodar esta função (`python manage.py rotate_gcal_encryption_key`);
    4. Tirar `GCAL_ENCRYPTION_KEY_FALLBACKS` e reiniciar.

    Tudo numa transação, com as credenciais travadas (`select_for_update`) contra o refresh que roda
    ao mesmo tempo: se uma credencial não abrir com nenhuma chave, nada é gravado.
    As chaves vêm só do ambiente; nunca são recebidas por argumento nem registradas.

    Returns:
        RotacaoResultado: credenciais recifradas e quantas só abriam com uma chave de FALLBACKS

    Raises:
        InvalidToken: Se alguma credencial não abrir com nenhuma chave configurada
        ValueError: Se a chave principal faltar em produção ou alguma fallback for malformada
    """
    multifernet: MultiFernet = _get_multifernet()
    principal: Fernet = Fernet(_get_fernet_key())
    fallbacks_count: int = len(_get_fallback_keys())
    if fallbacks_count == 0:
        logger.warning(
            "Rotação sem GCAL_ENCRYPTION_KEY_FALLBACKS: os tokens só são recifrados com a mesma chave principal."
        )

    count: int = 0
    so_com_fallback: int = 0
    with transaction.atomic():
        credentials: Any = GoogleOAuthCredential.objects.select_for_update().order_by("pk")
        for cred in credentials:
            # bytes(): em produção o psycopg2 devolve memoryview para o BinaryField.
            tokens: tuple[bytes, bytes] = (bytes(cred.access_token_encrypted), bytes(cred.refresh_token_encrypted))
            try:
                for token in tokens:
                    principal.decrypt(token)
            except InvalidToken:
                so_com_fallback += 1
            try:
                cred.access_token_encrypted = multifernet.rotate(tokens[0])
                cred.refresh_token_encrypted = multifernet.rotate(tokens[1])
            except InvalidToken:
                logger.error("Rotação desfeita: a credencial pk=%s não abre com nenhuma chave configurada.", cred.pk)
                raise
            cred.save(update_fields=["access_token_encrypted", "refresh_token_encrypted"])
            count += 1

        # Auditoria (PA-05)
        AuditLog.objects.create(
            usuario=None,
            action=AuditLog.Action.GCAL_ENCRYPTION_KEY_ROTATION,
            model_name="GoogleOAuthCredential",
            details={
                "credentials_updated": count,
                "credentials_from_fallback": so_com_fallback,
                "fallbacks_count": fallbacks_count,
                "status": "success",
            },
        )

    logger.info(
        "Rotação concluída: %s credenciais recifradas com a chave principal (%s só abriam com FALLBACKS).",
        count,
        so_com_fallback,
    )
    return RotacaoResultado(recifradas=count, so_com_fallback=so_com_fallback)
