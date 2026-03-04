"""
AS v2 — Workflow Models

Models de workflow operacional: Deslocamento, AcaoControle, AcaoDAT.
Type-checked with Pyright (strict mode).
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class Deslocamento(models.Model):
    """
    Registro de deslocamentos de usuarios entre municipios.

    Utilizado para:
    - Marcar periodos em que um usuario esta em transito
    - Exibir codigo "D" na grade mensal
    - Precedencia "D1" quando ha evento + deslocamento
    - Import via ETL (CSV/XLSX)
    """

    usuario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="deslocamentos",
        help_text="Usuario que realizou o deslocamento",
    )
    origem = models.CharField(max_length=200, help_text="Municipio/local de origem")
    destino = models.CharField(max_length=200, help_text="Municipio/local de destino")
    start_date = models.DateField(help_text="Data de inicio do deslocamento")
    end_date = models.DateField(help_text="Data de fim do deslocamento")
    observacao = models.TextField(null=True, blank=True, help_text="Observacoes sobre o deslocamento")
    external_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Hash SHA1 para idempotencia de import",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_deslocamento"
        verbose_name = "Deslocamento"
        verbose_name_plural = "Deslocamentos"
        ordering = ["usuario_id", "start_date", "end_date"]
        indexes = [
            models.Index(fields=["usuario", "start_date", "end_date"]),
            models.Index(fields=["external_hash"]),
        ]

    def __str__(self) -> str:
        start_fmt = self.start_date.strftime("%d/%m/%Y")
        end_fmt = self.end_date.strftime("%d/%m/%Y")
        return f"{self.usuario_id} {start_fmt}->{end_fmt} {self.origem}->{self.destino}"  # type: ignore[attr-defined]


class AcaoControle(models.Model):
    """
    Acoes do setor Controle: acompanhamento de entregas, cartas, reunioes.

    Campos:
    - municipio, projeto, coordenador
    - datas: data_entrega, data_carta, contato_inicial, data_reuniao
    - observacao, external_hash (idempotencia ETL)
    """

    municipio = models.ForeignKey(  # type: ignore[misc]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="acoes_controle",
        verbose_name="Municipio",
    )
    projeto = models.ForeignKey(  # type: ignore[misc]
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="acoes_controle",
        verbose_name="Projeto",
    )
    coordenador = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acoes_controle",
        verbose_name="Coordenador",
    )
    data_entrega = models.DateField(null=True, blank=True, verbose_name="Data da Entrega")
    data_carta = models.DateField(null=True, blank=True, verbose_name="Data da Carta")
    contato_inicial = models.DateField(null=True, blank=True, verbose_name="Contato inicial")
    data_reuniao = models.DateField(null=True, blank=True, verbose_name="Data Reuniao Alinhamento")
    observacao = models.TextField(null=True, blank=True, verbose_name="Observacao")
    external_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="External Hash",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_acao_controle"
        ordering = ["-data_reuniao", "-data_entrega", "municipio_id"]
        indexes = [
            models.Index(fields=["municipio", "projeto"]),
            models.Index(fields=["coordenador"]),
            models.Index(fields=["external_hash"]),
        ]

    def __str__(self) -> str:
        data_display = self.data_entrega or self.data_reuniao or ""
        return f"{self.municipio_id} | {self.projeto_id} | {data_display}"  # type: ignore[attr-defined]


class TipoAcaoDAT(models.TextChoices):
    """Valores canônicos de tipo_acao para AcaoDAT (planilha DAT)."""

    CRIACAO_CURSO = "FORMAR - Criação de Curso", "FORMAR - Criação de Curso"
    CRIACAO_CHAVES = "FORMAR - Criação de Chaves", "FORMAR - Criação de Chaves"
    CRIACAO_INSTRUCOES = "FORMAR - Criação de Instruções", "FORMAR - Criação de Instruções"
    CHAVES_ENVIADAS = "FORMAR - Chaves enviadas", "FORMAR - Chaves enviadas"
    CODIGOS_ENVIADOS = "Códigos enviados", "Códigos enviados"
    REUNIAO_DAT = "Reunião DAT", "Reunião DAT"


class AcaoDAT(models.Model):
    """
    Acoes do setor DAT: cadastros diversos por municipio/projeto.

    Campos:
    - municipio, projeto, tipo_acao, responsavel
    - data_registro, observacao, external_hash (idempotencia ETL)
    """

    municipio = models.ForeignKey(  # type: ignore[misc]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="acoes_dat",
        verbose_name="Municipio",
    )
    projeto = models.ForeignKey(  # type: ignore[misc]
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="acoes_dat",
        verbose_name="Projeto",
    )
    tipo_acao = models.CharField(
        max_length=120,
        choices=TipoAcaoDAT.choices,
        verbose_name="Tipo de Ação",
    )
    responsavel = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acoes_dat",
        verbose_name="Responsavel",
    )
    observacao = models.TextField(null=True, blank=True, verbose_name="Observacao")
    data_registro = models.DateField(null=True, blank=True, verbose_name="Data de registro")
    external_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="External Hash",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_acao_dat"
        ordering = ["-data_registro", "municipio_id"]
        indexes = [
            models.Index(fields=["municipio", "projeto"]),
            models.Index(fields=["tipo_acao"]),
            models.Index(fields=["external_hash"]),
        ]

    def __str__(self) -> str:
        return f"{self.municipio_id} | {self.projeto_id} | {self.tipo_acao}"  # type: ignore[attr-defined]
