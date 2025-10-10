"""
AS v2 — Core Models

Cláusulas Pétreas:
- RD-01 a RD-08: Regras de disponibilidade
- PA-01 a PA-07: Política de aprovação manual
- SSOT: Single Source of Truth (elimina IMPORTRANGE)
"""

from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    """
    Modelo de usuário customizado.
    SSOT: Substitui IMPORTRANGE de Usuários.xlsx
    """

    cpf = models.CharField(max_length=11, unique=True, db_index=True)
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "core_usuario"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.cpf})"


class Municipio(models.Model):
    """SSOT: Substitui IMPORTRANGE de Municípios"""

    nome = models.CharField(max_length=100, unique=True, db_index=True)
    uf = models.CharField(max_length=2)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "core_municipio"
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome}-{self.uf}"


class Projeto(models.Model):
    """SSOT: Substitui IMPORTRANGE de Projetos"""

    nome = models.CharField(max_length=200, unique=True, db_index=True)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "core_projeto"
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
