"""
AS v2 — Integracao Models

Models de integracao com servicos externos: GoogleOAuthCredential.
Type-checked with Pyright (strict mode).
"""
from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone


class GoogleOAuthCredential(models.Model):
    """
    Credenciais OAuth 2.0 do Google para usuarios do grupo Controle.

    Permite que usuarios autorizem individualmente o acesso ao Google Calendar
    para publicacao de eventos, substituindo o modelo de service account.

    **Seguranca**:
    - Tokens criptografados com Fernet (GCAL_ENCRYPTION_KEY dedicada)
    - Relacao OneToOne com Usuario (1 credencial por usuario)
    - Validacao de dominio (@aprendereditora.com.br)
    - Auditoria completa (AuditLog + google_email tracking)

    **Refresh automatico**:
    - `refresh_access_token_safe()` usa select_for_update() (concorrencia)
    - Refresh executado automaticamente antes de publicar eventos

    **Rotacao de chave**:
    - Management command: `python manage.py rotate_gcal_encryption_key`
    - Zero downtime: le com chave antiga, salva com chave nova

    Refs:
    - Sprint 1 (Issue #1): Modelo + Migration + Servico OAuth
    - GAP-1: Concorrencia com select_for_update
    - GAP-2: Encryption key dedicada com rotacao
    - GAP-5: Multi-calendar preparado (allowed_calendars)
    """

    user = models.OneToOneField(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.CASCADE,
        related_name="google_oauth",
        verbose_name="Usuario",
        help_text="Usuario Controle que conectou sua conta Google"
    )
    google_email = models.EmailField(
        max_length=255,
        db_index=True,
        verbose_name="E-mail Google",
        help_text="E-mail da conta Google conectada (ex: operacional1@aprendereditora.com.br)"
    )
    access_token_encrypted = models.BinaryField(
        verbose_name="Access Token (criptografado)",
        help_text="Access token criptografado com Fernet (GCAL_ENCRYPTION_KEY)"
    )
    refresh_token_encrypted = models.BinaryField(
        verbose_name="Refresh Token (criptografado)",
        help_text="Refresh token criptografado com Fernet (GCAL_ENCRYPTION_KEY)"
    )
    token_expiry = models.DateTimeField(
        verbose_name="Expiracao do Token",
        help_text="Timestamp UTC de expiracao do access token (geralmente 1h)"
    )
    scope = models.CharField(
        max_length=500,
        default="https://www.googleapis.com/auth/calendar",
        verbose_name="Scopes OAuth",
        help_text="Permissoes concedidas pelo usuario (separadas por espaco)"
    )
    default_calendar_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Calendario Padrao",
        help_text="ID do calendario padrao (ex: 'primary' ou ID especifico)"
    )
    allowed_calendars = models.JSONField(  # type: ignore[misc]
        default=list,
        blank=True,
        verbose_name="Calendarios Permitidos",
        help_text="Lista de IDs de calendarios que o usuario pode publicar (GAP-5: multi-calendar futuro)"
    )

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Conectado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:  # type: ignore[misc]
        db_table = "core_google_oauth_credential"
        verbose_name = "Credencial OAuth Google"
        verbose_name_plural = "Credenciais OAuth Google"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "token_expiry"]),
            models.Index(fields=["google_email"]),
            models.Index(fields=["token_expiry"]),  # Para job diario de alertas
        ]

    def __str__(self) -> str:
        expiry_fmt = self.token_expiry.strftime('%d/%m/%Y %H:%M') if self.token_expiry else "N/A"
        return f"{self.user.username} ({self.google_email}) - expira: {expiry_fmt}"

    def is_expired(self) -> bool:
        """Verifica se o access token esta expirado (com margem de 5 minutos)."""
        return timezone.now() >= self.token_expiry - timedelta(minutes=5)

    def days_until_expiry(self) -> int:
        """Retorna numero de dias ate expiracao (usado pelo job de alertas)."""
        if self.is_expired():
            return 0
        delta = self.token_expiry - timezone.now()
        return delta.days
