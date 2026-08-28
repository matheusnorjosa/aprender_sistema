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
                regex=r"^\d{11}$", message="CPF deve conter exatamente 11 dígitos numéricos.", code="invalid_cpf"
            )
        ],
    )
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    desativado_localmente = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Marca desativação decidida NO SISTEMA (admin/anonimização), não pela planilha. "
            "O import nunca reativa (False->True) um usuário com esta flag — reativar é ação humana "
            "(#1894). A planilha pode reativar quem ela mesma desativou (flag False)."
        ),
    )

    class Meta:  # type: ignore[misc]
        db_table = "core_usuario"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self) -> str:
        # LGPD: nao expor CPF (nem o username, que == CPF para importados) no __str__,
        # que vaza em logs/reprs/mensagens de erro do DRF. Nome, ou um id nao-PII.
        return self.get_full_name() or f"Usuario #{self.pk}"
