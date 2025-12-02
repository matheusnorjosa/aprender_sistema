"""
AS v2 — Usuario Model

SSOT: Substitui IMPORTRANGE de Usuarios.xlsx
Type-checked with Pyright (strict mode).
"""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario customizado.

    SSOT: Substitui IMPORTRANGE de Usuarios.xlsx
    """

    cpf = models.CharField(
        max_length=11,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^\d{11}$',
                message='CPF deve conter exatamente 11 dígitos numéricos.',
                code='invalid_cpf'
            )
        ]
    )
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_usuario"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.cpf})"
