"""
AS v2 — Config Model

Model de configuracoes dinamicas do sistema.
Type-checked with Pyright (strict mode).
"""
from __future__ import annotations

from django.db import models


class Config(models.Model):
    """
    Configuracoes mutaveis sem deploy (ex.: TRAVEL_BUFFER_MINUTES, AVAILABILITY_DAILY_LIMIT_HOURS).

    - Cache: 5min TTL via config_service.py
    - Invalidacao: Automatica via signal post_save
    - Ordem: effective_at DESC, updated_at DESC (mais recente primeiro)
    - Uso: get_cfg("availability", {}).get("TRAVEL_BUFFER_MINUTES", 120)

    Exemplos:
        # Config para RD-04 (buffer de deslocamento)
        Config.objects.create(
            key="availability",
            value={"TRAVEL_BUFFER_MINUTES": 120, "AVAILABILITY_DAILY_LIMIT_HOURS": 8},
            effective_at=timezone.now()
        )

        # Config para RD-05 (limite diario)
        Config.objects.create(
            key="gcal_sync",
            value={"BATCH_SIZE": 200, "LOCK_TTL_SECONDS": 300},
            effective_at=timezone.now()
        )
    """

    key = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Chave da configuracao (ex: 'availability', 'gcal_sync')",
    )
    value = models.JSONField(  # type: ignore[misc]
        default=dict, help_text="Valor da configuracao (dict JSON)"
    )
    effective_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data de vigencia (opcional, para config futura)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_config"
        verbose_name = "Configuracao"
        verbose_name_plural = "Configuracoes"
        ordering = ["-effective_at", "-updated_at"]
        indexes = [
            models.Index(fields=["key", "updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.key} (updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
