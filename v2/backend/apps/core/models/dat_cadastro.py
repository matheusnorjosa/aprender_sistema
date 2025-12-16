"""
AS v2 — DAT Cadastro Model

Model para gestao de cadastros nas plataformas FORMAR e AVALIAR.
Rastreia workflow de criação de cursos, chaves, instruções e envio.

Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.organizacao import Municipio, ProjetoGeral
    from apps.core.models.usuario import Usuario


class DATCadastro(models.Model):
    """
    Gestao de cadastros nas plataformas FORMAR e AVALIAR.

    Plataformas:
    - FORMAR: Cursos de formação online
    - AVALIAR: Avaliações e diagnósticos

    Workflow FORMAR: Criação Curso → Chaves → Instruções → Envio
    Workflow AVALIAR: Recebimento → Validação → Importação

    Ref: CadastrosPage.jsx
    """

    class Plataforma(models.TextChoices):
        FORMAR = "FORMAR", "FORMAR"
        AVALIAR = "AVALIAR", "AVALIAR"

    class StatusEtapa(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_ANDAMENTO = "em_andamento", "Em Andamento"
        CONCLUIDO = "concluido", "Concluído"
        ERRO = "erro", "Erro"
        NA = "na", "N/A"

    # Relacionamentos principais
    municipio: models.ForeignKey[Municipio] = models.ForeignKey(  # type: ignore[assignment]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="dat_cadastros",
        verbose_name="Município"
    )
    projeto_geral: models.ForeignKey[ProjetoGeral] = models.ForeignKey(  # type: ignore[assignment]
        "core.ProjetoGeral",
        on_delete=models.PROTECT,
        related_name="dat_cadastros",
        verbose_name="Projeto Geral"
    )
    plataforma = models.CharField(
        max_length=10,
        choices=Plataforma.choices,
        verbose_name="Plataforma"
    )

    # === Workflow FORMAR ===
    # Etapa 1: Criação do Curso
    status_criacao_curso = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Criação do Curso"
    )
    data_criacao_curso = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Criação Curso"
    )

    # Etapa 2: Chaves de Acesso
    status_chaves = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Chaves de Acesso"
    )
    data_chaves = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Geração Chaves"
    )
    quantidade_chaves = models.PositiveIntegerField(
        default=0,
        verbose_name="Quantidade de Chaves"
    )

    # Etapa 3: Instruções
    status_instrucoes = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Instruções"
    )
    data_instrucoes = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Envio Instruções"
    )

    # Etapa 4: Envio para Município
    status_envio = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Envio ao Município"
    )
    data_envio = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Envio"
    )

    # === Workflow AVALIAR ===
    # Etapa 1: Recebimento
    status_recebidos = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Dados Recebidos"
    )
    data_recebidos = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Recebimento"
    )
    quantidade_recebidos = models.PositiveIntegerField(
        default=0,
        verbose_name="Quantidade Recebida"
    )

    # Etapa 2: Validação
    status_validados = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Dados Validados"
    )
    data_validados = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Validação"
    )
    quantidade_validados = models.PositiveIntegerField(
        default=0,
        verbose_name="Quantidade Validada"
    )

    # Etapa 3: Importação
    status_importados = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Dados Importados"
    )
    data_importados = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Importação"
    )
    quantidade_importados = models.PositiveIntegerField(
        default=0,
        verbose_name="Quantidade Importada"
    )

    # Status geral
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(
        blank=True,
        max_length=1000,
        verbose_name="Observações"
    )

    # Auditoria
    created_by: models.ForeignKey[Usuario] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="dat_cadastros_criados",
        verbose_name="Criado por"
    )
    updated_by: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_cadastros_atualizados",
        verbose_name="Atualizado por"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_dat_cadastro"
        verbose_name = "Cadastro DAT"
        verbose_name_plural = "Cadastros DAT"
        ordering = ["plataforma", "municipio__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "projeto_geral", "plataforma"],
                name="unique_dat_cadastro_mun_proj_plat"
            ),
        ]
        indexes = [
            models.Index(fields=["municipio", "projeto_geral"]),
            models.Index(fields=["plataforma", "ativo"]),
        ]

    def __str__(self) -> str:
        return f"{self.plataforma} - {self.municipio} - {self.projeto_geral}"

    @property
    def progresso_formar(self) -> int:
        """Progresso do workflow FORMAR (0-100%)."""
        if self.plataforma != self.Plataforma.FORMAR:
            return 0
        etapas = [
            self.status_criacao_curso,
            self.status_chaves,
            self.status_instrucoes,
            self.status_envio,
        ]
        concluidas = sum(1 for s in etapas if s == self.StatusEtapa.CONCLUIDO)
        return int((concluidas / 4) * 100)

    @property
    def progresso_avaliar(self) -> int:
        """Progresso do workflow AVALIAR (0-100%)."""
        if self.plataforma != self.Plataforma.AVALIAR:
            return 0
        etapas = [
            self.status_recebidos,
            self.status_validados,
            self.status_importados,
        ]
        concluidas = sum(1 for s in etapas if s == self.StatusEtapa.CONCLUIDO)
        return int((concluidas / 3) * 100)

    @property
    def progresso(self) -> int:
        """Progresso geral baseado na plataforma."""
        if self.plataforma == self.Plataforma.FORMAR:
            return self.progresso_formar
        return self.progresso_avaliar
