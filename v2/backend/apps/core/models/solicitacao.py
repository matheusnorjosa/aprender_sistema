"""
AS v2 — Solicitacao Models

Models de solicitacao de eventos: Solicitacao, Participation.
Clausulas Petreas: PA-01 a PA-07, RD-06.
Type-checked with Pyright (strict mode).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.organizacao import Municipio, Projeto, TipoEvento
    from apps.core.models.usuario import Usuario


class Solicitacao(models.Model):
    """
    Solicitacao de evento (pre-agenda).

    PA-01: Status inicial = pendente (NUNCA auto-aprovar).
    PA-02: Apenas Superintendencia pode aprovar/reprovar.
    PA-03: Integracoes externas so executam APOS aprovacao.
    RD-06: Armazena UTC, compara em America/Fortaleza.
    """

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
    ]

    class GCalStatus(models.TextChoices):
        """Status de sincronizacao com Google Calendar."""
        NONE = "NONE", "Nao publicado"
        PENDING = "PENDING", "Aguardando publicacao"
        PUBLISHED = "PUBLISHED", "Publicado"
        ERROR = "ERROR", "Erro na publicacao"

    usuario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario", on_delete=models.PROTECT, related_name="solicitacoes"
    )
    municipio = models.ForeignKey(  # type: ignore[misc]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="solicitacoes",
        null=True,
        blank=True,
        help_text="Municipio onde ocorrera o evento",
    )
    projeto = models.ForeignKey(  # type: ignore[misc]
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="solicitacoes",
        null=True,
        blank=True,
        help_text="Projeto associado ao evento (determina fluxo de aprovacao)",
    )
    tipo_evento = models.ForeignKey(  # type: ignore[misc]
        "core.TipoEvento", on_delete=models.PROTECT, related_name="solicitacoes"
    )

    inicio = models.DateTimeField(help_text="Inicio do evento (UTC)")
    fim = models.DateTimeField(help_text="Fim do evento (UTC)")

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pendente",
        help_text="PA-01: Sempre comeca pendente",
    )

    observacoes = models.TextField(
        blank=True, help_text="Observacoes adicionais sobre o evento"
    )

    # Reservado para integracao idempotente com Google Calendar (RF05/RF06)
    external_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID do evento no Google Calendar (para idempotencia)",
    )

    # Hash unico para idempotencia de ETL (importacao de planilhas)
    external_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Hash SHA1 para identificar evento de fonte externa (ETL)",
    )

    # Observabilidade de sincronizacao (para debugging e monitoramento)
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Ultima vez que sync foi executado (sucesso ou falha)",
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
        help_text="Ultima acao de sync executada",
    )
    last_sync_error = models.TextField(
        null=True,
        blank=True,
        help_text="Mensagem de erro da ultima tentativa de sync (se houver)",
    )

    # Campos de negocio adicionais (PR-08)
    tipo = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Tipo de solicitacao (ex: evento, reuniao)",
    )
    encontro = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Identificacao do encontro (ex: Encontro 1)",
    )
    segmento = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Segmento educacional (ex: Fundamental I, Fundamental II)",
    )
    coordenador_acompanha = models.BooleanField(
        default=False,
        help_text="Indica se o coordenador acompanha o evento",
    )
    coordenador = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_coordenados",
        help_text="Coordenador responsavel pelo evento",
    )
    formadores = models.ManyToManyField(  # type: ignore[misc]
        "core.Usuario",
        blank=True,
        related_name="eventos_como_formador",
        help_text="Formadores que participam do evento",
    )

    # Campos de rastreamento de publicacao Google Calendar (PR14)
    gcal_status = models.CharField(
        max_length=16,
        choices=GCalStatus.choices,
        default=GCalStatus.NONE,
        db_index=True,
        verbose_name="Status GCal",
        help_text="Status de sincronizacao com Google Calendar",
    )
    gcal_last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ultimo sync GCal",
        help_text="Timestamp da ultima tentativa de sincronizacao com GCal",
    )
    gcal_last_error = models.TextField(
        null=True,
        blank=True,
        verbose_name="Ultimo erro GCal",
        help_text="Mensagem de erro da ultima tentativa de publicacao",
    )
    gcal_payload_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA1 do payload aplicado no GCal (drift detection)",
    )
    is_online = models.BooleanField(
        default=False,
        verbose_name="Evento online",
        help_text="Evento online? Gera link do Google Meet no APPLY.",
    )
    meet_link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Link do Google Meet",
        help_text="Link do Google Meet gerado automaticamente (RF06)",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_solicitacao"
        verbose_name = "Solicitacao de Evento"
        verbose_name_plural = "Solicitacoes de Evento"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "inicio"]),
            models.Index(fields=["usuario", "fim"]),
            models.Index(fields=["status"]),
            models.Index(fields=["external_event_id"]),
            # Indice para sync incremental eficiente
            models.Index(fields=["status", "inicio", "fim", "updated_at"]),
            # Indice para queries de sync incremental por timestamp
            models.Index(fields=["updated_at", "last_synced_at"]),
            # Indice composto para queries do painel GCal (PR14)
            models.Index(fields=["gcal_status", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fim__gt=models.F("inicio")),
                name="solicitacao_fim_gt_inicio",
            ),
            # Issue #136: Check constraint for status choices
            models.CheckConstraint(
                check=models.Q(status__in=['pendente', 'aprovado', 'reprovado']),
                name='solicitacao_status_valid',
            ),
            # Issue #136: Check constraint for gcal_status choices
            models.CheckConstraint(
                check=models.Q(gcal_status__in=['NONE', 'PENDING', 'PUBLISHED', 'ERROR']),
                name='solicitacao_gcal_status_valid',
            ),
        ]

    def __str__(self) -> str:
        return f"{self.usuario.get_full_name()} - {self.tipo_evento.nome} ({self.inicio.strftime('%d/%m/%Y %H:%M')})"

    def mark_gcal(
        self,
        *,
        status: str,
        payload_hash: str | None = None,
        error: str | None = None,
        sync_at: Any = None,
        meet_link: str | None = None,
    ) -> None:
        """
        Atualiza campos de rastreamento GCal (PR14, PR19).

        Args:
            status: Um dos valores de GCalStatus (NONE, PENDING, PUBLISHED, ERROR)
            payload_hash: SHA1 do payload aplicado (opcional)
            error: Mensagem de erro (truncada para 500 chars)
            sync_at: Timestamp do sync (default: timezone.now())
            meet_link: URL do Google Meet gerado automaticamente (RF06, opcional)

        Usage:
            solicitacao.mark_gcal(
                status=Solicitacao.GCalStatus.PUBLISHED,
                payload_hash="abc123...",
                meet_link="https://meet.google.com/abc-defg-hij",
                error=""
            )
        """
        if sync_at is None:
            sync_at = timezone.now()

        self.gcal_status = status
        self.gcal_payload_hash = payload_hash
        self.gcal_last_error = error[:500] if error else ""
        self.gcal_last_sync_at = sync_at

        # RF06: Atualizar meet_link se fornecido
        if meet_link is not None:
            self.meet_link = meet_link

        update_fields = [
            "gcal_status",
            "gcal_payload_hash",
            "gcal_last_error",
            "gcal_last_sync_at",
        ]

        if meet_link is not None:
            update_fields.append("meet_link")

        self.save(update_fields=update_fields)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save para implementar auto-aprovacao de fluxo NAO_SUPER.

        Fluxos do sistema:
        - SUPER: Requer aprovacao manual pela Superintendencia (PA-01 a PA-07)
        - NAO_SUPER: Auto-aprovado automaticamente na criacao

        Historico:
        - PR 13/N: Auto-aprovacao implementada para NAO_SUPER
        - PR17: REMOVEU auto-aprovacao (INCORRETO - revertido em PR18)
        - PR18: RESTAURA auto-aprovacao para NAO_SUPER conforme especificacao correta
        """
        # Auto-aprovar apenas projetos NAO_SUPER na criacao
        if self.pk is None and self.projeto and self.projeto.fluxo == 'NAO_SUPER':
            self.status = 'aprovado'

        super().save(*args, **kwargs)


class Participation(models.Model):
    """
    Participacao de usuarios em eventos (Solicitacoes).

    Permite representar multiplos papeis:
    - COORDENADOR: Coordenador do evento
    - FORMADOR: Formador/instrutor do evento
    - COORD_ACOMPANHA: Coordenador que acompanha (nao coordena)
    - CONVIDADO: Convidado/participante

    Unicidade: (solicitacao, usuario, role)
    """

    class Role(models.TextChoices):
        COORDENADOR = "COORDENADOR", "Coordenador"
        FORMADOR = "FORMADOR", "Formador"
        COORD_ACOMPANHA = "COORD_ACOMPANHA", "Coord. Acompanha"
        CONVIDADO = "CONVIDADO", "Convidado"

    solicitacao = models.ForeignKey(  # type: ignore[misc]
        "core.Solicitacao",
        on_delete=models.CASCADE,
        related_name="participations",
        verbose_name="Solicitacao",
    )
    # Usuario ou guest_email e obrigatorio (pelo menos um deve estar preenchido)
    usuario = models.ForeignKey(  # type: ignore[misc]
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_participations",
        null=True,
        blank=True,
        verbose_name="Usuario",
    )
    # Convidado externo identificado por e-mail quando nao ha usuario cadastrado
    guest_email = models.EmailField(null=True, blank=True, verbose_name="E-mail do convidado")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        verbose_name="Papel",
    )
    ch_horas = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="CH (horas)"
    )
    observacao = models.TextField(null=True, blank=True, verbose_name="Observacao")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:  # type: ignore[misc]
        db_table = "core_participation"
        verbose_name = "Participacao"
        verbose_name_plural = "Participacoes"
        ordering = ["solicitacao_id", "role", "usuario_id"]
        constraints = [
            # Pelo menos um entre usuario ou guest_email deve estar preenchido
            models.CheckConstraint(
                name="core_participation_user_or_email",
                check=(models.Q(usuario__isnull=False) | models.Q(guest_email__isnull=False)),
            ),
            # Unicidade por usuario (quando usuario existe)
            models.UniqueConstraint(
                fields=["solicitacao", "usuario", "role"],
                name="core_participation_unique_user",
                condition=models.Q(usuario__isnull=False),
            ),
            # Unicidade por convidado externo (quando email de convidado existe)
            models.UniqueConstraint(
                fields=["solicitacao", "guest_email", "role"],
                name="core_participation_unique_guest",
                condition=models.Q(guest_email__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=["solicitacao", "role"]),
            models.Index(fields=["usuario", "role"]),
            models.Index(fields=["guest_email"]),
        ]

    def __str__(self) -> str:
        return f"{self.solicitacao_id} - {self.usuario or self.guest_email} ({self.get_role_display()})"  # type: ignore[attr-defined]
