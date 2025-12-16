"""
AS v2 — DAT Acao Model

Model para gestao do ciclo de vida de acoes DAT em municipios.
Workflow: Carta → Contato → Reunião → Entrega

Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.dat_coordenador import DATCoordenador
    from apps.core.models.organizacao import Municipio, Projeto
    from apps.core.models.usuario import Usuario


class DATAcao(models.Model):
    """
    Gestao do ciclo de vida de acoes DAT por municipio/projeto.

    Workflow de 4 etapas:
    1. Carta - Envio de carta oficial
    2. Contato - Primeiro contato com municipio
    3. Reunião - Reuniao de alinhamento
    4. Entrega - Entrega de materiais/conclusao

    Ref: AcoesPage.jsx (ciclo de vida)
    """

    class StatusEtapa(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_ANDAMENTO = "em_andamento", "Em Andamento"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    # Relacionamentos principais
    municipio: models.ForeignKey[Municipio] = models.ForeignKey(  # type: ignore[assignment]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="dat_acoes",
        verbose_name="Município"
    )
    projeto: models.ForeignKey[Projeto] = models.ForeignKey(  # type: ignore[assignment]
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="dat_acoes",
        verbose_name="Projeto"
    )
    coordenador: models.ForeignKey[DATCoordenador | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.DATCoordenador",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_acoes",
        verbose_name="Coordenador Responsável"
    )

    # Etapa 1: Carta
    status_carta = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Status da Carta"
    )
    data_carta = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Envio da Carta"
    )
    observacao_carta = models.TextField(
        blank=True,
        max_length=500,
        verbose_name="Observação Carta"
    )

    # Etapa 2: Contato
    status_contato = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Status do Contato"
    )
    data_contato = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data do Contato"
    )
    observacao_contato = models.TextField(
        blank=True,
        max_length=500,
        verbose_name="Observação Contato"
    )

    # Etapa 3: Reunião
    status_reuniao = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Status da Reunião"
    )
    data_reuniao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data da Reunião"
    )
    observacao_reuniao = models.TextField(
        blank=True,
        max_length=500,
        verbose_name="Observação Reunião"
    )

    # Etapa 4: Entrega
    status_entrega = models.CharField(
        max_length=20,
        choices=StatusEtapa.choices,
        default=StatusEtapa.PENDENTE,
        verbose_name="Status da Entrega"
    )
    data_entrega = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data da Entrega"
    )
    observacao_entrega = models.TextField(
        blank=True,
        max_length=500,
        verbose_name="Observação Entrega"
    )

    # Status geral
    ativo = models.BooleanField(default=True)
    prioridade = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Prioridade",
        help_text="0 = normal, 1+ = alta prioridade"
    )

    # Auditoria
    created_by: models.ForeignKey[Usuario] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="dat_acoes_criadas",
        verbose_name="Criado por"
    )
    updated_by: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_acoes_atualizadas",
        verbose_name="Atualizado por"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_dat_acao"
        verbose_name = "Ação DAT"
        verbose_name_plural = "Ações DAT"
        ordering = ["-prioridade", "municipio__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "projeto"],
                name="unique_dat_acao_municipio_projeto"
            ),
        ]
        indexes = [
            models.Index(fields=["municipio", "projeto"]),
            models.Index(fields=["coordenador", "ativo"]),
            models.Index(fields=["status_carta"]),
            models.Index(fields=["status_entrega"]),
        ]

    def __str__(self) -> str:
        return f"{self.municipio} - {self.projeto}"

    @property
    def progresso(self) -> int:
        """Calcula progresso de 0-100% baseado nas etapas concluidas."""
        etapas = [
            self.status_carta,
            self.status_contato,
            self.status_reuniao,
            self.status_entrega,
        ]
        concluidas = sum(1 for s in etapas if s == self.StatusEtapa.CONCLUIDO)
        return int((concluidas / 4) * 100)

    @property
    def etapa_atual(self) -> str:
        """Retorna nome da etapa atual (primeira não concluída)."""
        if self.status_carta != self.StatusEtapa.CONCLUIDO:
            return "Carta"
        if self.status_contato != self.StatusEtapa.CONCLUIDO:
            return "Contato"
        if self.status_reuniao != self.StatusEtapa.CONCLUIDO:
            return "Reunião"
        if self.status_entrega != self.StatusEtapa.CONCLUIDO:
            return "Entrega"
        return "Concluído"
