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
    deve_trocar_senha = models.BooleanField(
        default=False,
        help_text=(
            "Ligado quando a senha em uso foi definida por outra pessoa (administrador ou carga). "
            "Enquanto ligado, a API só aceita ler o próprio /me, CSRF, trocar a senha e sair "
            "(`TrocaDeSenhaObrigatoriaMiddleware`). Desliga quando a própria pessoa troca a senha."
        ),
    )
    senha_recebida_hash = models.CharField(
        max_length=128,
        blank=True,
        default="",
        editable=False,
        help_text=(
            "Hash da última senha recebida de outra pessoa, guardado quando a própria pessoa a troca. "
            "Serve só para recusar a volta a ela (a senha padrão é a mesma para todos). Nunca o texto da senha."
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
