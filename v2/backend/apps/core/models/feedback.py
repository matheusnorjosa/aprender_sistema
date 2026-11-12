"""
AS v2 — Feedback de uso da plataforma

Feedback: nota, tipo e comentário que a pessoa logada envia pelo botão "Dar feedback" (pedido do
dono, 11/11/2026), com a tela em que estava. Identificado (`usuario`), sem user-agent, IP nem e-mail.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

from django.db import models


class Feedback(models.Model):
    """Uma resposta do botão "Dar feedback". Quem lê: o superusuário e o DAT (`manage_admin_registries`)."""

    class Tipo(models.TextChoices):
        ELOGIO = "ELOGIO", "Elogio"
        PROBLEMA = "PROBLEMA", "Problema"
        SUGESTAO = "SUGESTAO", "Sugestão"
        DUVIDA = "DUVIDA", "Dúvida"

    usuario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedbacks",
        verbose_name="Pessoa",
    )
    nota = models.PositiveSmallIntegerField(verbose_name="Nota (1 a 5)")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, verbose_name="Tipo")
    # O limite de 2.000 caracteres é do serializer (a tela conta junto).
    comentario = models.TextField(blank=True, default="", verbose_name="Comentário")
    pagina = models.CharField(max_length=200, verbose_name="Tela", help_text="Rota do frontend, sem query string")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Enviado em")

    class Meta:  # type: ignore[misc]
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(nota__gte=1, nota__lte=5), name="feedback_nota_1_a_5"),
        ]

    def __str__(self) -> str:
        return f"Feedback #{self.pk} ({self.tipo}, nota {self.nota})"
