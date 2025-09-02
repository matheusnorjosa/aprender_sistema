# aprender_sistema/core/models.py
import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.conf import settings
from django.utils import timezone

# =========================
# 1) USUÁRIO CUSTOMIZADO
# =========================
class Usuario(AbstractUser):
    """
    User model using Django Groups for role-based permissions
    Roles are now managed through Django Groups instead of papel field
    
    Campos adicionais para migração das planilhas:
    - cpf: CPF único do usuário
    - telefone: Telefone de contato
    - municipio: Município de atuação
    """
    
    # Campos extras para dados das planilhas
    cpf = models.CharField(
        max_length=11, 
        unique=True, 
        blank=True,
        null=True,
        verbose_name="CPF",
        help_text="CPF sem formatação (apenas números)"
    )
    
    telefone = models.CharField(
        max_length=15, 
        blank=True,
        verbose_name="Telefone",
        help_text="Telefone de contato"
    )
    
    municipio = models.ForeignKey(
        'Municipio',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Município",
        help_text="Município de atuação do usuário"
    )
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.username
    
    @property
    def nome_completo(self):
        """Compatibilidade com planilhas - Nome completo"""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def role_names(self):
        """Get user's role names from groups"""
        return list(self.groups.values_list('name', flat=True))
    
    @property
    def primary_role(self):
        """Get primary role (first group) for display purposes"""
        groups = self.role_names
        return groups[0] if groups else None
    
    def has_role(self, role_name):
        """Check if user has specific role"""
        return self.groups.filter(name=role_name).exists()
    
    def has_any_role(self, role_names):
        """Check if user has any of the specified roles"""
        return self.groups.filter(name__in=role_names).exists()


# =========================
# 2) CADASTROS DE REFERÊNCIA
# =========================
class Projeto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Projeto")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    vinculado_superintendencia = models.BooleanField(
        default=False, 
        verbose_name="Vinculado à Superintendência",
        help_text="Projetos vinculados à superintendência requerem aprovação para eventos"
    )

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Municipio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, verbose_name="Nome do Município")
    uf = models.CharField(max_length=2, blank=True, default="", verbose_name="UF")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        unique_together = [("nome", "uf")]
        indexes = [models.Index(fields=["nome", "uf"])]
        ordering = ["nome", "uf"]

    def __str__(self):
        return f"{self.nome}/{self.uf}" if self.uf else self.nome


class Formador(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, verbose_name="Nome do Formador")
    email = models.EmailField(max_length=255, unique=True, verbose_name="E-mail")
    area_atuacao = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Área de Atuação")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    # Connection to User model for authentication/authorization
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name='formador_profile',
        verbose_name="Usuário"
    )

    class Meta:
        verbose_name = "Formador"
        verbose_name_plural = "Formadores"
        ordering = ["nome"]
        indexes = [models.Index(fields=["email"])]
        permissions = [
            ('view_own_events', 'Can view own events (Formador)'),
        ]

    def __str__(self):
        return f"{self.nome} <{self.email}>"

    @property
    def user_groups(self):
        """Return user groups if usuario is connected"""
        if self.usuario:
            return self.usuario.groups.all()
        return []

    @property
    def has_formador_role(self):
        """Check if connected user has formador role"""
        if self.usuario:
            return self.usuario.groups.filter(name='formador').exists()
        return False


class TipoEvento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Tipo de Evento")
    online = models.BooleanField(default=False, verbose_name="É Online?")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Tipo de Evento"
        verbose_name_plural = "Tipos de Evento"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# =========================
# 3) FLUXO OPERACIONAL
# =========================
class SolicitacaoStatus(models.TextChoices):
    PENDENTE = "Pendente", "Pendente"
    PRE_AGENDA = "PreAgenda", "Pré-Agenda"
    APROVADO = "Aprovado", "Aprovado"
    REPROVADO = "Reprovado", "Reprovado"


class Solicitacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    usuario_solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="solicitacoes_criadas"
    )
    projeto = models.ForeignKey(Projeto, on_delete=models.PROTECT)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT)
    tipo_evento = models.ForeignKey(TipoEvento, on_delete=models.PROTECT)

    titulo_evento = models.CharField(max_length=255)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()

    numero_encontro_formativo = models.CharField(max_length=50, blank=True, null=True)
    coordenador_acompanha = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=SolicitacaoStatus.choices, default=SolicitacaoStatus.PENDENTE
    )
    usuario_aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="solicitacoes_decididas"
    )
    data_aprovacao_rejeicao = models.DateTimeField(null=True, blank=True)
    justificativa_rejeicao = models.TextField(blank=True, null=True)

    # M2M por through
    formadores = models.ManyToManyField("Formador", through="FormadoresSolicitacao", related_name="solicitacoes")

    class Meta:
        ordering = ["-data_solicitacao"]
        indexes = [
            models.Index(fields=["data_inicio"]),
            models.Index(fields=["data_fim"]),
            models.Index(fields=["status"]),
            models.Index(fields=["municipio", "data_inicio"]),
            models.Index(fields=["tipo_evento", "data_inicio"]),
        ]
        constraints = [
            # Evitar títulos duplicados no mesmo dia
            models.UniqueConstraint(
                fields=["titulo_evento", "data_inicio"],
                name="unique_titulo_evento_data",
                violation_error_message="Já existe uma solicitação com o mesmo título nesta data."
            ),
            # Validar que data_fim > data_inicio
            models.CheckConstraint(
                check=models.Q(data_fim__gt=models.F('data_inicio')),
                name="data_fim_after_inicio",
                violation_error_message="Data de fim deve ser posterior à data de início."
            ),
            # Evitar solicitações muito longas (mais de 12 horas)
            models.CheckConstraint(
                check=models.Q(data_fim__lte=models.F('data_inicio') + timedelta(hours=12)),
                name="max_duracao_12_horas",
                violation_error_message="Duração máxima de evento é 12 horas."
            ),
        ]
        permissions = [
            ('sync_calendar', 'Can sync with Google Calendar'),
            ('view_own_solicitacoes', 'Can view own solicitações (Coordenador)'),
        ]

    def __str__(self):
        return f"{self.titulo_evento} ({self.data_inicio:%d/%m/%Y %H:%M})"


class FormadoresSolicitacao(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE)
    formador = models.ForeignKey(Formador, on_delete=models.PROTECT)

    class Meta:
        unique_together = [("solicitacao", "formador")]
        verbose_name = "Formador da Solicitação"
        verbose_name_plural = "Formadores da Solicitação"

    def __str__(self):
        return f"{self.formador} em {self.solicitacao}"


class AprovacaoStatus(models.TextChoices):
    APROVADO = "Aprovado", "Aprovado"
    REPROVADO = "Reprovado", "Reprovado"


class Aprovacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name="aprovacoes")
    usuario_aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="aprovacoes_realizadas"
    )
    data_aprovacao = models.DateTimeField(auto_now_add=True)
    status_decisao = models.CharField(max_length=20, choices=AprovacaoStatus.choices)
    justificativa = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-data_aprovacao"]

    def __str__(self):
        return f"{self.status_decisao} — {self.solicitacao.titulo_evento}"


class EventoGoogleCalendar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    solicitacao = models.OneToOneField(Solicitacao, on_delete=models.CASCADE, related_name="evento_google")
    usuario_criador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="eventos_criados"
    )
    # RF05: Campos atualizados para nova estrutura
    provider_event_id = models.CharField(max_length=255, verbose_name="ID do evento no provedor")  # google_calendar_id renomeado
    html_link = models.TextField(blank=True, null=True, verbose_name="Link do evento")  # link_evento renomeado
    meet_link = models.TextField(blank=True, null=True, verbose_name="Link do Meet")  # link_meet renomeado
    raw_payload = models.JSONField(blank=True, null=True, verbose_name="Payload bruto da resposta")  # novo campo
    data_criacao = models.DateTimeField(auto_now_add=True)

    class SincronizacaoStatus(models.TextChoices):
        PENDENTE = "Pendente", "Pendente"
        OK = "OK", "OK"
        ERRO = "Erro", "Erro"

    status_sincronizacao = models.CharField(
        max_length=20, choices=SincronizacaoStatus.choices, default=SincronizacaoStatus.PENDENTE
    )
    mensagem_erro = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Evento Google Calendar"
        verbose_name_plural = "Eventos Google Calendar"
        indexes = [models.Index(fields=["provider_event_id"])]

    def __str__(self):
        return f"GC:{self.provider_event_id} — {self.solicitacao}"


class DisponibilidadeFormadores(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    formador = models.ForeignKey(Formador, on_delete=models.CASCADE, related_name="disponibilidades")
    data_bloqueio = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    tipo_bloqueio = models.CharField(max_length=50)
    motivo = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Disponibilidade de Formador"
        verbose_name_plural = "Disponibilidades de Formadores"
        ordering = ["formador", "data_bloqueio", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(hora_fim__gt=models.F("hora_inicio")),
                name="hora_fim_maior_que_inicio",
            ),
            models.UniqueConstraint(
                fields=["formador", "data_bloqueio", "hora_inicio", "hora_fim"],
                name="uniq_formador_intervalo",
            ),
        ]

    def __str__(self):
        return f"{self.formador} — {self.data_bloqueio} {self.hora_inicio}-{self.hora_fim}"


class LogAuditoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    acao = models.CharField(max_length=255)
    entidade_afetada_id = models.UUIDField(null=True, blank=True)
    detalhes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-data_hora"]
        permissions = [
            ('view_relatorios', 'Can view consolidated reports'),
        ]

    def __str__(self):
        return f"[{self.data_hora:%d/%m/%Y %H:%M}] {self.acao}"


# =========================
# 4) Deslocamento (para mapa mensal)
# =========================
class Deslocamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.DateField()
    origem = models.CharField(max_length=255, blank=True, default="")
    destino = models.CharField(max_length=255, blank=True, default="")
    formadores = models.ManyToManyField("Formador", related_name="deslocamentos")

    class Meta:
        verbose_name = "Deslocamento"
        verbose_name_plural = "Deslocamentos"
        indexes = [models.Index(fields=["data"])]
        ordering = ["-data"]

    def __str__(self):
        return f"{self.data:%d/%m/%Y} {self.origem} → {self.destino}"
