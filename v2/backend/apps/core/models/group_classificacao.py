"""
Classificação de grupos para RBAC no Admin DAT.

Permite distinguir grupos de setor e função de forma dinâmica (sem hardcode).
"""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.db import models


class GroupClassificacao(models.Model):
    """Classificação de um grupo como setor ou função."""

    class Tipo(models.TextChoices):
        SETOR = "setor", "Setor"
        FUNCAO = "funcao", "Função"

    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name="rbac_classificacao",
    )
    tipo = models.CharField(
        max_length=16,
        choices=Tipo.choices,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_group_classificacao"
        verbose_name = "Classificação de Grupo"
        verbose_name_plural = "Classificações de Grupo"
        ordering = ["group__name"]

    def __str__(self) -> str:
        return f"{self.group.name} ({self.get_tipo_display()})"
