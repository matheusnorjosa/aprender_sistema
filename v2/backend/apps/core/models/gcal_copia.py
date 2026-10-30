"""
AS v2 — Cópia Google → Sistema

GCalCopiaCursor: ponto de leitura incremental (syncToken) de um calendário e o interruptor da cópia.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

from django.db import models


class GCalCopiaCursor(models.Model):
    """
    Estado da cópia Google → Sistema de um calendário.

    Nasce desligado (`ativo=False`) e em `observar` (lê e decide, só grava o `resumo`). Ligar,
    desligar e trocar o modo é feito no banco, sem redeploy; a task relê a linha em toda execução.
    Nada de dado pessoal aqui: `adiados` guarda só event ids e `resumo`/`ultimo_erro` só
    contagens, s<id> e motivos curtos.
    """

    class Modo(models.TextChoices):
        OBSERVAR = "observar", "Observar"
        COPIAR = "copiar", "Copiar"

    calendar_id = models.CharField(max_length=255, unique=True, verbose_name="Calendário")
    sync_token = models.TextField(null=True, blank=True, verbose_name="syncToken do Google")
    ativo = models.BooleanField(default=False, verbose_name="Ativo")
    modo = models.CharField(max_length=10, choices=Modo.choices, default=Modo.OBSERVAR, verbose_name="Modo")
    operador = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Operador",
        help_text="Conta cuja credencial Google faz a leitura",
    )
    adiados = models.JSONField(default=list, blank=True, verbose_name="Adiados")  # type: ignore[misc]
    resumo = models.JSONField(default=dict, blank=True, verbose_name="Resumo da última rodada")  # type: ignore[misc]
    ultimo_sucesso_em = models.DateTimeField(null=True, blank=True, verbose_name="Último sucesso em")
    ultimo_erro = models.CharField(max_length=300, blank=True, default="", verbose_name="Último erro")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:  # type: ignore[misc]
        verbose_name = "Cursor da cópia Google"
        verbose_name_plural = "Cursores da cópia Google"

    def __str__(self) -> str:
        return f"{self.calendar_id} ({self.modo}, {'ativo' if self.ativo else 'inativo'})"
