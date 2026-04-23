"""
AS v2 — Permissao Funcional (RBAC configuravel)

Mapeia capacidades de negocio (codename) para grupos do Django.
Permite gerenciar acesso via UI sem hardcode de nomes de grupo no codigo.
"""

# pyright: reportUnknownVariableType=false
from __future__ import annotations

from django.contrib.auth.models import Group
from django.db import models


class PermissaoFuncional(models.Model):
    """
    Permissao funcional de alto nivel da aplicacao.

    Exemplo:
    - codename: pode_operar_dat
    - category: cadastros_administrativos

    Categorias canônicas (Epic 1 RBAC Refactor, 2026-04-23):
    solicitacao, importacao, cadastros_administrativos, dashboard,
    operacao, supervisao. Ver v2/docs/plans/rbac-refactor/master-plan.md §3.4.
    """

    codename = models.SlugField(
        max_length=80,
        unique=True,
        db_index=True,
        help_text="Identificador tecnico estavel usado nas regras de autorizacao.",
    )
    label = models.CharField(max_length=120, help_text="Nome amigavel exibido na UI.")
    description = models.TextField(
        blank=True,
        default="",
        help_text="Descricao opcional da permissao funcional.",
    )
    category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Categoria para agrupamento (ex.: admin_dat, dashboard, solicitacao).",
    )
    is_system = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Quando true, permissao faz parte do conjunto base do sistema.",
    )
    groups = models.ManyToManyField(
        Group,
        related_name="permissoes_funcionais",
        blank=True,
        help_text="Grupos que recebem esta permissao funcional.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_permissao_funcional"
        verbose_name = "Permissao Funcional"
        verbose_name_plural = "Permissoes Funcionais"
        ordering = ["category", "label"]

    def __str__(self) -> str:
        return f"{self.codename} ({self.label})"
