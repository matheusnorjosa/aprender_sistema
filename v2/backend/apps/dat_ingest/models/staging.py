"""
Staging models para ETL - Tabelas temporárias para importação
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false, reportIncompatibleMethodOverride=false, reportInvalidTypeForm=false


from __future__ import annotations

from django.db import models


class StgUsuario(models.Model):
    """Staging: Usuários importados de planilhas"""

    nome = models.CharField(max_length=255)
    email = models.EmailField()
    cpf = models.CharField(max_length=11, blank=True, default="")
    telefone = models.CharField(max_length=20, blank=True, default="")
    perfil = models.CharField(max_length=50)  # "Formador"/"Coordenador"/"Superintendência"
    ativo = models.BooleanField(default=True)
    src = models.CharField(max_length=100)  # nome do arquivo / aba
    rownum = models.IntegerField()

    class Meta:  # type: ignore[misc]
        db_table = "stg_usuario"
        verbose_name = "Staging Usuario"
        verbose_name_plural = "Staging Usuarios"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["src"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.email}) - {self.src}:{self.rownum}"


class StgMunicipio(models.Model):
    """Staging: Municípios importados de planilhas"""

    nome = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    ativo = models.BooleanField(default=True)
    src = models.CharField(max_length=100)
    rownum = models.IntegerField()

    class Meta:  # type: ignore[misc]
        db_table = "stg_municipio"
        verbose_name = "Staging Municipio"
        verbose_name_plural = "Staging Municipios"
        indexes = [
            models.Index(fields=["nome", "uf"]),
        ]

    def __str__(self):
        return f"{self.nome}-{self.uf} - {self.src}:{self.rownum}"


class StgProjeto(models.Model):
    """Staging: Projetos importados de planilhas"""

    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, default="")
    ativo = models.BooleanField(default=True)
    src = models.CharField(max_length=100)
    rownum = models.IntegerField()

    class Meta:  # type: ignore[misc]
        db_table = "stg_projeto"
        verbose_name = "Staging Projeto"
        verbose_name_plural = "Staging Projetos"
        indexes = [
            models.Index(fields=["nome"]),
        ]

    def __str__(self):
        return f"{self.nome} - {self.src}:{self.rownum}"


class StgTipoEvento(models.Model):
    """Staging: Tipos de Evento importados de planilhas"""

    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, default="")
    cor = models.CharField(max_length=7, blank=True, default="")  # hex color
    src = models.CharField(max_length=100)
    rownum = models.IntegerField()

    class Meta:  # type: ignore[misc]
        db_table = "stg_tipo_evento"
        verbose_name = "Staging Tipo Evento"
        verbose_name_plural = "Staging Tipos Evento"
        indexes = [
            models.Index(fields=["nome"]),
        ]

    def __str__(self):
        return f"{self.nome} - {self.src}:{self.rownum}"
