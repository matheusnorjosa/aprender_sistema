"""
AS v2 — Core Models

Cláusulas Pétreas:
- RD-01 a RD-08: Regras de disponibilidade
- PA-01 a PA-07: Política de aprovação manual
- SSOT: Single Source of Truth (elimina IMPORTRANGE)
"""

from django.contrib.auth.models import AbstractUser
from django.conf import settings
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

    FLUXO_CHOICES = [
        ('SUPER', 'Superintendência'),
        ('NAO_SUPER', 'Não-Super'),
    ]

    nome = models.CharField(max_length=200, unique=True, db_index=True)
    codigo = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Código único do projeto (ex: ACERTA, NLENDO)"
    )
    fluxo = models.CharField(
        max_length=12,
        choices=FLUXO_CHOICES,
        default='NAO_SUPER',
        db_index=True,
        help_text="SUPER: requer aprovação da Superintendência. NAO_SUPER: auto-aprovado."
    )
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
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.PROTECT,
        related_name="solicitacoes",
        null=True,
        blank=True,
        help_text="Projeto associado ao evento (determina fluxo de aprovação)",
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

    # Hash único para idempotência de ETL (importação de planilhas)
    external_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Hash SHA1 para identificar evento de fonte externa (ETL)",
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


class Compra(models.Model):
    """
    Registro de compras de materiais/produtos para projetos.

    - Idempotência: external_hash (SHA256 da linha normalizada)
    - Chave natural: (codigo + municipio + projeto + data)
    - Import: Suporta CSV/XLSX via import_compras service
    """

    codigo = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Código da compra (ex: COMP-001)"
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.PROTECT,
        related_name="compras",
        help_text="Projeto vinculado à compra"
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name="compras",
        help_text="Município destino da compra"
    )
    quantidade = models.IntegerField(
        help_text="Quantidade de itens comprados"
    )
    data = models.DateField(
        help_text="Data da compra"
    )
    uso = models.TextField(
        help_text="Uso/finalidade da compra (ex: Formação inicial)"
    )
    external_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Hash SHA256 para idempotência de import"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_compra"
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-data", "-created_at"]
        indexes = [
            models.Index(fields=["codigo", "data"]),
            models.Index(fields=["projeto", "municipio"]),
            models.Index(fields=["external_hash"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_hash"],
                name="core_compra_external_hash_unique",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.projeto.nome} ({self.data.strftime('%d/%m/%Y')})"


class Deslocamento(models.Model):
    """
    Registro de deslocamentos de usuários entre municípios.

    Utilizado para:
    - Marcar períodos em que um usuário está em trânsito
    - Exibir código "D" na grade mensal
    - Precedência "D1" quando há evento + deslocamento
    - Import via ETL (CSV/XLSX)
    """

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="deslocamentos",
        help_text="Usuário que realizou o deslocamento"
    )
    origem = models.CharField(
        max_length=200,
        help_text="Município/local de origem"
    )
    destino = models.CharField(
        max_length=200,
        help_text="Município/local de destino"
    )
    start_date = models.DateField(
        help_text="Data de início do deslocamento"
    )
    end_date = models.DateField(
        help_text="Data de fim do deslocamento"
    )
    observacao = models.TextField(
        null=True,
        blank=True,
        help_text="Observações sobre o deslocamento"
    )
    external_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Hash SHA1 para idempotência de import"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_deslocamento"
        verbose_name = "Deslocamento"
        verbose_name_plural = "Deslocamentos"
        ordering = ["usuario_id", "start_date", "end_date"]
        indexes = [
            models.Index(fields=["usuario", "start_date", "end_date"]),
            models.Index(fields=["external_hash"]),
        ]

    def __str__(self):
        start_fmt = self.start_date.strftime('%d/%m/%Y')
        end_fmt = self.end_date.strftime('%d/%m/%Y')
        return f"{self.usuario_id} {start_fmt}→{end_fmt} {self.origem}->{self.destino}"


class AuditLog(models.Model):
    """
    Log de auditoria para rastreamento de operações críticas.

    - Registra ações como: CELERY_GCAL_SYNC, approve, reject, create, update, delete
    - Details: JSON com contexto da operação (status, applied, reason, etc.)
    - PA-05: Obrigatório para aprovações/reprovações
    """

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Usuário que executou a ação (se aplicável)"
    )
    action = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Ação executada (ex: CELERY_GCAL_SYNC, approve, reject)"
    )
    model_name = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        db_index=True,
        help_text="Nome do modelo relacionado (opcional, ex: Solicitacao, Compra)"
    )
    details = models.JSONField(
        default=dict,
        help_text="Detalhes da operação (status, applied, reason, etc.)"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "core_audit_log"
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["usuario", "created_at"]),
        ]

    def __str__(self):
        usuario_str = self.usuario.get_full_name() if self.usuario else "Sistema"
        return f"{usuario_str} - {self.action} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"


class Participation(models.Model):
    """
    Participação de usuários em eventos (Solicitações).

    Permite representar múltiplos papéis:
    - COORDENADOR: Coordenador do evento
    - FORMADOR: Formador/instrutor do evento
    - COORD_ACOMPANHA: Coordenador que acompanha (não coordena)
    - CONVIDADO: Convidado/participante

    Unicidade: (solicitacao, usuario, role)
    """

    class Role(models.TextChoices):
        COORDENADOR = "COORDENADOR", "Coordenador"
        FORMADOR = "FORMADOR", "Formador"
        COORD_ACOMPANHA = "COORD_ACOMPANHA", "Coord. Acompanha"
        CONVIDADO = "CONVIDADO", "Convidado"

    solicitacao = models.ForeignKey(
        "core.Solicitacao",
        on_delete=models.CASCADE,
        related_name="participations",
        verbose_name="Solicitação",
    )
    # Usuário é obrigatório para todos os papéis, exceto CONVIDADO
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_participations",
        null=True,
        blank=True,
        verbose_name="Usuário",
    )
    # Convidado externo identificado por e-mail quando não há usuário cadastrado
    guest_email = models.EmailField(null=True, blank=True, verbose_name="E-mail do convidado")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        verbose_name="Papel",
    )
    ch_horas = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="CH (horas)"
    )
    observacao = models.TextField(null=True, blank=True, verbose_name="Observação")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        db_table = "core_participation"
        verbose_name = "Participação"
        verbose_name_plural = "Participações"
        ordering = ["solicitacao_id", "role", "usuario_id"]
        constraints = [
            # Pelo menos um entre usuário ou guest_email deve estar preenchido
            models.CheckConstraint(
                name="core_participation_user_or_email",
                check=(models.Q(usuario__isnull=False) | models.Q(guest_email__isnull=False)),
            ),
            # Se não for convidado, usuário é obrigatório
            models.CheckConstraint(
                name="core_participation_user_required_when_not_guest",
                check=(
                    models.Q(role="CONVIDADO")
                    | (models.Q(role__in=["COORDENADOR", "FORMADOR", "COORD_ACOMPANHA"]) & models.Q(usuario__isnull=False))
                ),
            ),
            # Unicidade por usuário (quando usuário existe)
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

    def __str__(self):
        return f"{self.solicitacao_id} — {self.usuario or self.guest_email} ({self.get_role_display()})"
