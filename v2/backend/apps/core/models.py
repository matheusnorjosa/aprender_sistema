"""
AS v2 — Core Models

Cláusulas Pétreas:
- RD-01 a RD-08: Regras de disponibilidade
- PA-01 a PA-07: Política de aprovação manual
- SSOT: Single Source of Truth (elimina IMPORTRANGE)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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


class TipoEvento(models.Model):
    """SSOT: Substitui IMPORTRANGE de Tipos de Evento"""

    nome = models.CharField(max_length=100, unique=True, db_index=True)
    descricao = models.TextField(blank=True)
    cor = models.CharField(max_length=7, blank=True, help_text="Cor hex (#RRGGBB)")

    class Meta:
        db_table = "core_tipo_evento"
        verbose_name = "Tipo de Evento"
        verbose_name_plural = "Tipos de Evento"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class AvailabilityBlock(models.Model):
    """
    Bloqueio de disponibilidade (RD-02, RD-03).

    - Total (T): bloqueia qualquer evento no intervalo
    - Parcial (P): bloqueia apenas sub-janela especificada

    PA-01: Status começa pendente, aprovação manual obrigatória.
    RD-06: Armazena UTC, compara em America/Fortaleza.
    """

    TIPO_CHOICES = [
        ("T", "Total"),
        ("P", "Parcial"),
    ]

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
    ]

    usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="availability_blocks"
    )
    inicio = models.DateTimeField(help_text="Início do bloqueio (UTC)")
    fim = models.DateTimeField(help_text="Fim do bloqueio (UTC)")
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default="T")
    motivo = models.CharField(
        max_length=255, blank=True, help_text="Motivo do bloqueio"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_availability_block"
        verbose_name = "Bloqueio de Disponibilidade"
        verbose_name_plural = "Bloqueios de Disponibilidade"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "inicio"]),
            models.Index(fields=["usuario", "fim"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fim__gt=models.F("inicio")),
                name="availability_block_fim_gt_inicio",
            ),
        ]

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_tipo_display()} ({self.inicio.strftime('%d/%m/%Y %H:%M')} - {self.fim.strftime('%d/%m/%Y %H:%M')})"


class Solicitacao(models.Model):
    """
    Solicitação de evento (pré-agenda).

    PA-01: Status inicial = pendente (NUNCA auto-aprovar).
    PA-02: Apenas Superintendência pode aprovar/reprovar.
    PA-03: Integrações externas só executam APÓS aprovação.
    RD-06: Armazena UTC, compara em America/Fortaleza.
    """

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
    ]

    usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="solicitacoes"
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name="solicitacoes",
        null=True,
        blank=True,
        help_text="Município onde ocorrerá o evento",
    )
    tipo_evento = models.ForeignKey(
        TipoEvento, on_delete=models.PROTECT, related_name="solicitacoes"
    )

    inicio = models.DateTimeField(help_text="Início do evento (UTC)")
    fim = models.DateTimeField(help_text="Fim do evento (UTC)")

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pendente",
        help_text="PA-01: Sempre começa pendente",
    )

    observacoes = models.TextField(
        blank=True, help_text="Observações adicionais sobre o evento"
    )

    # Reservado para integração idempotente com Google Calendar (RF05/RF06)
    external_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID do evento no Google Calendar (para idempotência)",
    )

    # Observabilidade de sincronização (para debugging e monitoramento)
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última vez que sync foi executado (sucesso ou falha)",
    )
    last_sync_action = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[
            ("CREATE", "Create"),
            ("UPDATE", "Update"),
            ("ADOPT", "Adopt"),
            ("DELETE", "Delete"),
            ("SKIP", "Skip"),
        ],
        help_text="Última ação de sync executada",
    )
    last_sync_error = models.TextField(
        null=True,
        blank=True,
        help_text="Mensagem de erro da última tentativa de sync (se houver)",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_solicitacao"
        verbose_name = "Solicitação de Evento"
        verbose_name_plural = "Solicitações de Evento"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "inicio"]),
            models.Index(fields=["usuario", "fim"]),
            models.Index(fields=["status"]),
            models.Index(fields=["external_event_id"]),
            # Índice para sync incremental eficiente
            models.Index(fields=["status", "inicio", "fim", "updated_at"]),
            # Índice para queries de sync incremental por timestamp
            models.Index(fields=["updated_at", "last_synced_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fim__gt=models.F("inicio")),
                name="solicitacao_fim_gt_inicio",
            ),
        ]

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.tipo_evento.nome} ({self.inicio.strftime('%d/%m/%Y %H:%M')})"


class Config(models.Model):
    """
    Configurações mutáveis sem deploy (ex.: TRAVEL_BUFFER_MINUTES, AVAILABILITY_DAILY_LIMIT_HOURS).

    - Cache: 5min TTL via config_service.py
    - Invalidação: Automática via signal post_save
    - Ordem: effective_at DESC, updated_at DESC (mais recente primeiro)
    - Uso: get_cfg("availability", {}).get("TRAVEL_BUFFER_MINUTES", 120)

    Exemplos:
        # Config para RD-04 (buffer de deslocamento)
        Config.objects.create(
            key="availability",
            value={"TRAVEL_BUFFER_MINUTES": 120, "AVAILABILITY_DAILY_LIMIT_HOURS": 8},
            effective_at=timezone.now()
        )

        # Config para RD-05 (limite diário)
        Config.objects.create(
            key="gcal_sync",
            value={"BATCH_SIZE": 200, "LOCK_TTL_SECONDS": 300},
            effective_at=timezone.now()
        )
    """

    key = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Chave da configuração (ex: 'availability', 'gcal_sync')",
    )
    value = models.JSONField(
        default=dict, help_text="Valor da configuração (dict JSON)"
    )
    effective_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data de vigência (opcional, para config futura)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_config"
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"
        ordering = ["-effective_at", "-updated_at"]
        indexes = [
            models.Index(fields=["key", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.key} (updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
