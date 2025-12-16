"""
AS v2 — DAT Formacao Model

Model para gestao de formacoes e treinamentos do DAT.
Rastreia agendamento, participantes e documentacao.

Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.dat_coordenador import DATCoordenador
    from apps.core.models.municipio import Municipio
    from apps.core.models.projeto import Projeto
    from apps.core.models.usuario import Usuario


class DATFormacao(models.Model):
    """
    Gestao de formacoes e treinamentos do DAT.

    Rastreia:
    - Agendamento (data, horario, modalidade)
    - Participantes (previsto, confirmado, presente)
    - Documentacao (material, lista presenca, relatorio, fotos)
    - Status do ciclo de vida

    Ref: FormacoesPage.jsx (calendario de formacoes)
    """

    class StatusFormacao(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        CONFIRMADA = "confirmada", "Confirmada"
        EM_ANDAMENTO = "em_andamento", "Em Andamento"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"
        ADIADA = "adiada", "Adiada"

    class Modalidade(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        ONLINE = "online", "Online"
        HIBRIDO = "hibrido", "Híbrido"

    # Relacionamentos principais
    municipio: models.ForeignKey[Municipio] = models.ForeignKey(  # type: ignore[assignment]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="dat_formacoes",
        verbose_name="Município"
    )
    projeto: models.ForeignKey[Projeto] = models.ForeignKey(  # type: ignore[assignment]
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="dat_formacoes",
        verbose_name="Projeto"
    )
    coordenador: models.ForeignKey[DATCoordenador | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.DATCoordenador",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_formacoes",
        verbose_name="Coordenador Responsável"
    )

    # Identificacao
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título da Formação"
    )
    descricao = models.TextField(
        blank=True,
        max_length=2000,
        verbose_name="Descrição"
    )

    # Agendamento
    data_formacao = models.DateField(
        verbose_name="Data da Formação"
    )
    horario_inicio = models.TimeField(
        verbose_name="Horário de Início"
    )
    horario_fim = models.TimeField(
        verbose_name="Horário de Término"
    )
    modalidade = models.CharField(
        max_length=20,
        choices=Modalidade.choices,
        default=Modalidade.PRESENCIAL,
        verbose_name="Modalidade"
    )
    local = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Local",
        help_text="Endereço ou link da reunião online"
    )

    # Participantes
    quantidade_prevista = models.PositiveIntegerField(
        default=0,
        verbose_name="Participantes Previstos"
    )
    quantidade_confirmada = models.PositiveIntegerField(
        default=0,
        verbose_name="Participantes Confirmados"
    )
    quantidade_presente = models.PositiveIntegerField(
        default=0,
        verbose_name="Participantes Presentes"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=StatusFormacao.choices,
        default=StatusFormacao.AGENDADA,
        verbose_name="Status"
    )
    motivo_cancelamento = models.TextField(
        blank=True,
        max_length=500,
        verbose_name="Motivo Cancelamento/Adiamento"
    )

    # Documentação
    material_preparado = models.BooleanField(
        default=False,
        verbose_name="Material Preparado"
    )
    lista_presenca_enviada = models.BooleanField(
        default=False,
        verbose_name="Lista de Presença Enviada"
    )
    relatorio_enviado = models.BooleanField(
        default=False,
        verbose_name="Relatório Enviado"
    )
    fotos_enviadas = models.BooleanField(
        default=False,
        verbose_name="Fotos Enviadas"
    )

    # Links de documentos
    link_material = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Link do Material"
    )
    link_lista_presenca = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Link Lista de Presença"
    )
    link_relatorio = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Link do Relatório"
    )
    link_fotos = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Link das Fotos"
    )

    # Observações
    observacoes = models.TextField(
        blank=True,
        max_length=2000,
        verbose_name="Observações"
    )

    # Controle
    ativo = models.BooleanField(default=True)

    # Auditoria
    created_by: models.ForeignKey[Usuario] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="dat_formacoes_criadas",
        verbose_name="Criado por"
    )
    updated_by: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_formacoes_atualizadas",
        verbose_name="Atualizado por"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_dat_formacao"
        verbose_name = "Formação DAT"
        verbose_name_plural = "Formações DAT"
        ordering = ["-data_formacao", "horario_inicio"]
        indexes = [
            models.Index(fields=["municipio", "projeto"]),
            models.Index(fields=["coordenador", "status"]),
            models.Index(fields=["data_formacao", "status"]),
            models.Index(fields=["modalidade"]),
        ]

    def __str__(self) -> str:
        return f"{self.titulo} - {self.municipio} ({self.data_formacao})"

    @property
    def duracao_horas(self) -> float:
        """Duração da formação em horas."""
        from datetime import datetime, timedelta
        inicio = datetime.combine(self.data_formacao, self.horario_inicio)
        fim = datetime.combine(self.data_formacao, self.horario_fim)
        delta = fim - inicio
        return delta.total_seconds() / 3600

    @property
    def taxa_presenca(self) -> float:
        """Taxa de presença (presentes/previstos * 100)."""
        if self.quantidade_prevista == 0:
            return 0.0
        return (self.quantidade_presente / self.quantidade_prevista) * 100

    @property
    def documentacao_completa(self) -> bool:
        """Verifica se toda documentação foi enviada."""
        return all([
            self.material_preparado,
            self.lista_presenca_enviada,
            self.relatorio_enviado,
            self.fotos_enviadas,
        ])
