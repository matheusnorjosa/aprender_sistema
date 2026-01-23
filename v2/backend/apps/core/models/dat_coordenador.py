"""
AS v2 — DAT Coordenador e Area Models

Models para gestao de coordenadores do DAT e suas areas de atuacao.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.usuario import Usuario


class DATArea(models.Model):
    """
    Tabela de referencia para areas de atuacao dos coordenadores.

    Ex: DAT, Tecnologia, Pedagogico, Administrativo, etc.
    """

    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Area")
    cor = models.CharField(
        max_length=20, blank=True, verbose_name="Cor", help_text="Cor para exibicao na UI (ex: blue, green, red)"
    )
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveSmallIntegerField(default=0, verbose_name="Ordem de Exibicao")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_dat_area"
        verbose_name = "Area DAT"
        verbose_name_plural = "Areas DAT"
        ordering = ["ordem", "nome"]

    def __str__(self) -> str:
        return self.nome


class DATCoordenador(models.Model):
    """
    Gestao de coordenadores do DAT.

    Registra informacoes de contato, area de atuacao e status.
    Rastreia carga de trabalho via relacionamentos com DATAcao e DATFormacao.

    Ref: CoordenadoresPage.jsx (29 registros)
    """

    # Dados pessoais
    nome = models.CharField(max_length=200, verbose_name="Nome Completo")
    email = models.EmailField(blank=True, verbose_name="Email Principal")
    email_alternativo = models.EmailField(blank=True, verbose_name="Email Alternativo")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone Principal")
    telefone_alternativo = models.CharField(max_length=20, blank=True, verbose_name="Telefone Alternativo")

    # Area e cargo
    area = models.CharField(max_length=100, verbose_name="Area de Atuacao", help_text="Ex: DAT, Tecnologia, Pedagogico")
    cargo = models.CharField(max_length=100, blank=True, verbose_name="Cargo")

    # Status
    ativo = models.BooleanField(default=True)
    data_admissao = models.DateField(null=True, blank=True, verbose_name="Data de Admissao")

    # Foto
    foto_url = models.URLField(max_length=500, blank=True, verbose_name="URL da Foto")

    # Observacoes
    observacoes = models.TextField(blank=True, max_length=2000, verbose_name="Observacoes")

    # Auditoria
    created_by: models.ForeignKey[Usuario] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario", on_delete=models.PROTECT, related_name="dat_coordenadores_criados", verbose_name="Criado por"
    )
    updated_by: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_coordenadores_atualizados",
        verbose_name="Atualizado por",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_dat_coordenador"
        verbose_name = "Coordenador DAT"
        verbose_name_plural = "Coordenadores DAT"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["area", "ativo"]),
            models.Index(fields=["nome"]),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.area})"

    @property
    def total_municipios(self) -> int:
        """Conta municipios unicos das acoes atribuidas."""
        return self.dat_acoes.values("municipio").distinct().count()

    @property
    def total_projetos(self) -> int:
        """Conta projetos unicos das acoes atribuidas."""
        return self.dat_acoes.values("projeto").distinct().count()

    @property
    def total_formacoes(self) -> int:
        """Conta formacoes atribuidas."""
        return self.dat_formacoes.count()
