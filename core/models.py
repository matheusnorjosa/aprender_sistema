# aprender_sistema/core/models.py
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils import timezone


# =========================
# 0) ESTRUTURA ORGANIZACIONAL
# =========================
class Setor(models.Model):
    """
    Representa os setores organizacionais da empresa.
    Cada setor tem sua própria estrutura hierárquica completa:
    gerentes → coordenadores → apoios de coordenação → formadores
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome do Setor",
        help_text="Ex: Superintendência, Vidas, Brincando e Aprendendo",
    )
    sigla = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Sigla",
        help_text="Abreviação do setor (ex: SUPER, VIDAS, BRINC)",
    )
    vinculado_superintendencia = models.BooleanField(
        default=False,
        verbose_name="É Setor Superintendência",
        help_text="Marque apenas para o setor Superintendência. Projetos deste setor requerem aprovação.",
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# =========================
# 1) USUÁRIO CUSTOMIZADO
# =========================

class UsuarioManager(models.Manager):
    """
    Manager customizado para Usuario - Single Source of Truth
    Centraliza todas as queries para evitar duplicação e inconsistências
    """

    def get_queryset(self):
        """QuerySet base otimizado com relacionamentos comuns"""
        return super().get_queryset().select_related('setor', 'municipio')

    def ativos(self):
        """Usuários ativos no sistema"""
        return self.filter(is_active=True)

    def inativos(self):
        """Usuários inativos no sistema"""
        return self.filter(is_active=False)

    # === FORMADORES ===
    def formadores(self):
        """Todos os formadores (fonte única de verdade)"""
        return self.ativos().filter(
            formador_ativo=True,
            groups__name='formador'
        ).distinct()

    def formadores_por_area(self, area=None):
        """Formadores filtrados por área de especialização"""
        qs = self.formadores()
        if area:
            qs = qs.filter(area_especializacao=area)
        return qs

    def formadores_por_municipio(self, municipio=None):
        """Formadores filtrados por município"""
        qs = self.formadores()
        if municipio:
            qs = qs.filter(municipio=municipio)
        return qs

    # === COORDENADORES ===
    def coordenadores(self):
        """Todos os coordenadores"""
        return self.ativos().filter(cargo='coordenador')

    def coordenadores_superintendencia(self):
        """Coordenadores vinculados à superintendência"""
        return self.coordenadores().filter(
            setor__vinculado_superintendencia=True
        )

    def coordenadores_outros_setores(self):
        """Coordenadores de outros setores (não-superintendência)"""
        return self.coordenadores().filter(
            setor__vinculado_superintendencia=False
        )

    def coordenadores_por_vinculacao(self, superintendencia_only=None):
        """
        Coordenadores filtrados por vinculação organizacional

        Args:
            superintendencia_only (bool):
                - True: apenas superintendência
                - False: apenas outros setores
                - None: todos os coordenadores
        """
        qs = self.coordenadores()

        if superintendencia_only is True:
            qs = qs.filter(setor__vinculado_superintendencia=True)
        elif superintendencia_only is False:
            qs = qs.filter(setor__vinculado_superintendencia=False)

        return qs

    # === GERENTES ===
    def gerentes(self):
        """Todos os gerentes"""
        return self.ativos().filter(cargo='gerente')

    def gerentes_superintendencia(self):
        """Gerentes que podem aprovar solicitações"""
        return self.gerentes().filter(
            setor__vinculado_superintendencia=True
        )

    # === CONTROLE ===
    def controle(self):
        """Usuários do controle"""
        return self.ativos().filter(cargo='controle')

    # === QUERIES OTIMIZADAS PARA DASHBOARD ===
    def formadores_dashboard(self):
        """Formadores otimizados para dashboard com prefetch"""
        return self.formadores().prefetch_related(
            'groups',
            'solicitacoes_como_formador'
        )

    def coordenadores_dashboard(self):
        """Coordenadores otimizados para dashboard com prefetch"""
        return self.coordenadores().prefetch_related(
            'groups',
            'solicitacoes_criadas'
        )

    # === QUERIES POR SETOR ===
    def por_setor(self, setor):
        """Usuários filtrados por setor"""
        return self.ativos().filter(setor=setor)

    def por_cargo(self, cargo):
        """Usuários filtrados por cargo"""
        return self.ativos().filter(cargo=cargo)


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
        verbose_name="CPF (Login)",
        help_text="CPF sem formatação (apenas números) - usado como login no sistema",
        validators=[],  # Validação será feita no formulário
    )

    telefone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Telefone",
        help_text="Telefone de contato",
    )

    municipio = models.ForeignKey(
        "Municipio",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Município",
        help_text="Município de atuação do usuário",
    )

    # Novos campos para estrutura organizacional
    setor = models.ForeignKey(
        "Setor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Setor",
        help_text="Setor organizacional do usuário",
    )

    CARGO_CHOICES = [
        ("gerente", "Gerente"),
        ("coordenador", "Coordenador"),
        ("apoio_coordenacao", "Apoio de Coordenação"),
        ("formador", "Formador"),
        ("controle", "Controle"),
        ("admin", "Administrador"),
        ("outros", "Outros"),
    ]

    cargo = models.CharField(
        max_length=20,
        choices=CARGO_CHOICES,
        blank=True,
        verbose_name="Cargo",
        help_text="Cargo/função do usuário na organização",
    )

    # Campos específicos para formadores (migrados do modelo Formador)
    AREA_ESPECIALIZACAO_CHOICES = [
        ("alfabetizacao", "Alfabetização"),
        ("matematica", "Matemática"),
        ("linguagem", "Linguagem e Portugês"),
        ("ciencias", "Ciências"),
        ("educacao_infantil", "Educação Infantil"),
        ("gestao_escolar", "Gestão Escolar"),
        ("tecnologia_educacional", "Tecnologia Educacional"),
        ("outros", "Outros"),
    ]

    area_especializacao = models.CharField(
        max_length=30,
        choices=AREA_ESPECIALIZACAO_CHOICES,
        blank=True,
        verbose_name="Área de Especialização",
        help_text="Área principal de especialização do formador",
    )

    anos_experiencia = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Anos de Experiência",
        help_text="Anos de experiência como formador",
    )

    observacoes_formador = models.TextField(
        blank=True,
        verbose_name="Observações do Formador",
        help_text="Informações adicionais sobre competências, certificações, etc.",
    )

    # Campo para compatibilidade durante migração
    formador_ativo = models.BooleanField(
        default=False,
        verbose_name="É Formador Ativo",
        help_text="Indica se este usuário atua como formador",
    )

    # === CAMPOS MIGRADOS DO FORMADOR (CONSOLIDAÇÃO) ===
    # Dados que antes estavam no modelo Formador separado
    area_atuacao = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Área de Atuação (Group)",
        help_text="Área de atuação como Group (compatibilidade com Formador)",
        related_name="usuarios_area_atuacao"
    )

    # === MANAGER CUSTOMIZADO ===
    objects = UsuarioManager()

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
        return list(self.groups.values_list("name", flat=True))

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

    # Novos métodos para estrutura organizacional
    @property
    def setor_nome(self):
        """Nome do setor do usuário"""
        return self.setor.nome if self.setor else None

    @property
    def cargo_display(self):
        """Nome do cargo formatado"""
        return dict(self.CARGO_CHOICES).get(self.cargo, self.cargo)

    def is_gerente(self):
        """Verifica se o usuário é gerente"""
        return self.cargo == "gerente"

    def can_approve_requests(self):
        """Verifica se pode aprovar solicitações (gerente da superintendência)"""
        return (
            self.cargo == "gerente"
            and self.setor
            and self.setor.vinculado_superintendencia
        )

    def can_create_requests(self):
        """Verifica se pode criar solicitações (coordenador ou apoio)"""
        return self.cargo in ["coordenador", "apoio_coordenacao"]

    # ===== MÉTODOS DE DIFERENCIAÇÃO DE COORDENADORES =====

    def is_coordenador(self):
        """Verifica se o usuário é coordenador"""
        return self.cargo == "coordenador"

    def is_coordenador_superintendencia(self):
        """Verifica se é coordenador vinculado à superintendência"""
        return (
            self.cargo == "coordenador"
            and self.setor
            and self.setor.vinculado_superintendencia
        )

    def is_coordenador_outros_setores(self):
        """Verifica se é coordenador de outros setores (não-superintendência)"""
        return (
            self.cargo == "coordenador"
            and self.setor
            and not self.setor.vinculado_superintendencia
        )

    @classmethod
    def get_coordenadores_superintendencia(cls):
        """Retorna coordenadores vinculados à superintendência"""
        return cls.objects.filter(
            cargo="coordenador",
            setor__vinculado_superintendencia=True,
            is_active=True
        ).select_related('setor')

    @classmethod
    def get_coordenadores_outros_setores(cls):
        """Retorna coordenadores de outros setores (não-superintendência)"""
        return cls.objects.filter(
            cargo="coordenador",
            setor__vinculado_superintendencia=False,
            is_active=True
        ).select_related('setor')

    @classmethod
    def get_coordenadores_por_vinculacao(cls, superintendencia_only=None):
        """
        Retorna coordenadores filtrados por vinculação à superintendência

        Args:
            superintendencia_only (bool):
                - True: apenas superintendência
                - False: apenas outros setores
                - None: todos os coordenadores
        """
        queryset = cls.objects.filter(
            cargo="coordenador",
            is_active=True
        ).select_related('setor')

        if superintendencia_only is True:
            queryset = queryset.filter(setor__vinculado_superintendencia=True)
        elif superintendencia_only is False:
            queryset = queryset.filter(setor__vinculado_superintendencia=False)

        return queryset

    @property
    def tipo_coordenador(self):
        """Retorna o tipo de coordenador para exibição"""
        if not self.is_coordenador():
            return None

        if self.is_coordenador_superintendencia():
            return "Superintendência"
        elif self.is_coordenador_outros_setores():
            return f"Setor {self.setor.nome}"
        else:
            return "Sem setor definido"

    # === MÉTODOS UNIFICADOS PARA FORMADORES ===
    def is_formador(self):
        """Verifica se o usuário é um formador ativo (fonte única de verdade)"""
        return self.formador_ativo and self.groups.filter(name="formador").exists()

    @property
    def area_especializacao_display(self):
        """Nome da área de especialização formatado"""
        return dict(self.AREA_ESPECIALIZACAO_CHOICES).get(self.area_especializacao, self.area_especializacao)

    @property
    def area_atuacao_display(self):
        """Nome da área de atuação (Group) formatado"""
        return self.area_atuacao.name if self.area_atuacao else None

    def get_disponibilidades(self):
        """Retorna as disponibilidades/bloqueios do formador"""
        if hasattr(self, 'disponibilidades'):
            return self.disponibilidades.all()
        return []

    def get_solicitacoes_como_formador(self):
        """Retorna solicitações onde este usuário é formador"""
        if hasattr(self, 'solicitacoes_como_formador'):
            return self.solicitacoes_como_formador.all()
        return []

    def get_eventos_realizados(self):
        """Retorna eventos realizados pelo formador (query otimizada)"""
        return self.get_solicitacoes_como_formador().filter(
            status='Aprovado'
        ).select_related('projeto', 'municipio', 'tipo_evento')

    def get_eventos_proximos(self):
        """Retorna próximos eventos do formador"""
        from django.utils import timezone
        return self.get_solicitacoes_como_formador().filter(
            status='Aprovado',
            data_inicio__gte=timezone.now()
        ).select_related('projeto', 'municipio', 'tipo_evento')

    # === COMPATIBILIDADE COM MODELO FORMADOR ===
    @property
    def nome_formador(self):
        """Nome para compatibilidade com modelo Formador"""
        return self.nome_completo

    @property
    def email_formador(self):
        """Email para compatibilidade com modelo Formador"""
        return self.email

    @property
    def user_groups(self):
        """Return user groups (compatibilidade com Formador)"""
        return self.groups.all()

    @property
    def has_formador_role(self):
        """Check if user has formador role (compatibilidade com Formador)"""
        return self.groups.filter(name="formador").exists()


# =========================
# 2) CADASTROS DE REFERÊNCIA
# =========================
class Projeto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Projeto")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")

    # Vinculação ao setor organizacional
    setor = models.ForeignKey(
        "Setor",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="Setor",
        help_text="Setor organizacional responsável pelo projeto",
    )

    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    # DEPRECATED: Mantido para compatibilidade durante migração
    vinculado_superintendencia = models.BooleanField(
        default=False,
        verbose_name="Vinculado à Superintendência (DEPRECATED)",
        help_text="DEPRECATED: Use setor.vinculado_superintendencia",
    )

    # Campos adicionais da planilha produtos.xlsx
    codigo_produto = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Código do Produto",
        help_text="ID/código do produto da planilha",
    )

    tipo_produto = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Tipo do Produto",
        help_text="Tipo/categoria do produto",
    )

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ["setor__nome", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.setor.sigla if self.setor else 'SEM SETOR'})"

    @property
    def requer_aprovacao_superintendencia(self):
        """Verifica se o projeto requer aprovação da superintendência"""
        return self.setor and self.setor.vinculado_superintendencia

    @property
    def setor_nome(self):
        """Nome do setor do projeto"""
        return self.setor.nome if self.setor else None


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
        # Se o nome já contém a UF (formato "Nome - UF"), não duplicar
        if self.uf and f"- {self.uf}" in self.nome:
            return self.nome
        else:
            return f"{self.nome}/{self.uf}" if self.uf else self.nome


class Formador(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, verbose_name="Nome do Formador")
    email = models.EmailField(max_length=255, unique=True, verbose_name="E-mail")
    area_atuacao = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Área de Atuação",
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    # Connection to User model for authentication/authorization
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="formador_profile",
        verbose_name="Usuário",
    )

    class Meta:
        verbose_name = "Formador"
        verbose_name_plural = "Formadores"
        ordering = ["nome"]
        indexes = [models.Index(fields=["email"])]
        permissions = [
            ("view_own_events", "Can view own events (Formador)"),
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
            return self.usuario.groups.filter(name="formador").exists()
        return False


class TipoEvento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(
        max_length=255, unique=True, verbose_name="Nome do Tipo de Evento"
    )
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
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitacoes_criadas",
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
        max_length=20,
        choices=SolicitacaoStatus.choices,
        default=SolicitacaoStatus.PENDENTE,
    )
    usuario_aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitacoes_decididas",
    )
    data_aprovacao_rejeicao = models.DateTimeField(null=True, blank=True)
    justificativa_rejeicao = models.TextField(blank=True, null=True)

    # M2M por through
    # Alterado para Usuario através do modelo intermediário atualizado
    formadores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="FormadoresSolicitacao",
        related_name="solicitacoes_como_formador",
        limit_choices_to={'formador_ativo': True}
    )

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
                violation_error_message="Já existe uma solicitação com o mesmo título nesta data.",
            ),
            # Validar que data_fim > data_inicio
            models.CheckConstraint(
                check=models.Q(data_fim__gt=models.F("data_inicio")),
                name="data_fim_after_inicio",
                violation_error_message="Data de fim deve ser posterior à data de início.",
            ),
            # Evitar solicitações muito longas (mais de 12 horas)
            models.CheckConstraint(
                check=models.Q(
                    data_fim__lte=models.F("data_inicio") + timedelta(hours=12)
                ),
                name="max_duracao_12_horas",
                violation_error_message="Duração máxima de evento é 12 horas.",
            ),
        ]
        permissions = [
            ("sync_calendar", "Can sync with Google Calendar"),
            ("view_own_solicitacoes", "Can view own solicitações (Coordenador)"),
        ]

    def __str__(self):
        return f"{self.titulo_evento} ({self.data_inicio:%d/%m/%Y %H:%M})"

    def save(self, *args, **kwargs):
        """
        Implementa aprovação automática para setores não-superintendência.

        FLUXO A (Superintendência): Coordenador → Pendente → Gerente aprova → Aprovado
        FLUXO B (Outros setores): Coordenador → Aprovado automaticamente
        """
        # Se é uma nova solicitação (verificar se existe no banco)
        is_new_record = self._state.adding

        if is_new_record:
            # Verificar se o projeto é da superintendência
            if self.projeto.setor.vinculado_superintendencia:
                # FLUXO A: Superintendência - fica pendente para aprovação manual
                self.status = SolicitacaoStatus.PENDENTE
            else:
                # FLUXO B: Outros setores - aprovação automática
                self.status = SolicitacaoStatus.APROVADO
                self.data_aprovacao_rejeicao = timezone.now()
                # Não define usuario_aprovador pois é automático

        super().save(*args, **kwargs)


class FormadoresSolicitacao(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE)
    # Alterado para Usuario com filtro por grupo formador
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'formador_ativo': True},
        verbose_name="Formador"
    )

    class Meta:
        unique_together = [("solicitacao", "usuario")]
        verbose_name = "Formador da Solicitação"
        verbose_name_plural = "Formadores da Solicitação"

    def __str__(self):
        return f"{self.usuario.nome_completo} em {self.solicitacao}"

    @property
    def formador(self):
        """Propriedade para compatibilidade - retorna o usuário"""
        return self.usuario


class AprovacaoStatus(models.TextChoices):
    APROVADO = "Aprovado", "Aprovado"
    REPROVADO = "Reprovado", "Reprovado"


class Aprovacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    solicitacao = models.ForeignKey(
        Solicitacao, on_delete=models.CASCADE, related_name="aprovacoes"
    )
    usuario_aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="aprovacoes_realizadas",
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
    solicitacao = models.OneToOneField(
        Solicitacao, on_delete=models.CASCADE, related_name="evento_google"
    )
    usuario_criador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eventos_criados",
    )
    # RF05: Campos atualizados para nova estrutura
    provider_event_id = models.CharField(
        max_length=255, verbose_name="ID do evento no provedor"
    )  # google_calendar_id renomeado
    html_link = models.TextField(
        blank=True, null=True, verbose_name="Link do evento"
    )  # link_evento renomeado
    meet_link = models.TextField(
        blank=True, null=True, verbose_name="Link do Meet"
    )  # link_meet renomeado
    raw_payload = models.JSONField(
        blank=True, null=True, verbose_name="Payload bruto da resposta"
    )  # novo campo
    data_criacao = models.DateTimeField(auto_now_add=True)

    class SincronizacaoStatus(models.TextChoices):
        PENDENTE = "Pendente", "Pendente"
        OK = "OK", "OK"
        ERRO = "Erro", "Erro"

    status_sincronizacao = models.CharField(
        max_length=20,
        choices=SincronizacaoStatus.choices,
        default=SincronizacaoStatus.PENDENTE,
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
    # Alterado para Usuario
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="disponibilidades",
        limit_choices_to={'formador_ativo': True},
        verbose_name="Formador",
        null=True,  # Temporário para migração
        blank=True
    )
    data_bloqueio = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    tipo_bloqueio = models.CharField(max_length=50)
    motivo = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Disponibilidade de Formador"
        verbose_name_plural = "Disponibilidades de Formadores"
        ordering = ["usuario", "data_bloqueio", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(hora_fim__gt=models.F("hora_inicio")),
                name="hora_fim_maior_que_inicio",
            ),
            models.UniqueConstraint(
                fields=["usuario", "data_bloqueio", "hora_inicio", "hora_fim"],
                name="uniq_usuario_intervalo",
            ),
        ]

    @property
    def formador(self):
        """Propriedade para compatibilidade - retorna o usuário"""
        return self.usuario

    def __str__(self):
        return (
            f"{self.usuario.nome_completo} — {self.data_bloqueio} {self.hora_inicio}-{self.hora_fim}"
        )


class LogAuditoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    data_hora = models.DateTimeField(auto_now_add=True)
    acao = models.CharField(max_length=255)
    entidade_afetada_id = models.UUIDField(null=True, blank=True)
    detalhes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-data_hora"]
        permissions = [
            ("view_relatorios", "Can view consolidated reports"),
        ]

    def __str__(self):
        return f"[{self.data_hora:%d/%m/%Y %H:%M}] {self.acao}"


# =========================
# 4) Deslocamento (para mapa mensal)
# =========================
class Deslocamento(models.Model):
    """
    Modelo para registrar deslocamentos de formadores entre municípios.
    Suporta até 6 pessoas por deslocamento, com tipo Deslocamento ou Retorno.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.DateField(verbose_name="Data")
    
    # Origem e destino - municípios ou locais
    origem = models.CharField(
        max_length=255, 
        verbose_name="Origem",
        help_text="Local de partida do deslocamento"
    )
    destino = models.CharField(
        max_length=255, 
        verbose_name="Destino",
        help_text="Local de chegada do deslocamento"
    )
    
    # Tipo de deslocamento
    TIPO_CHOICES = [
        ('deslocamento', 'Deslocamento'),
        ('retorno', 'Retorno'),
    ]
    tipo = models.CharField(
        max_length=15, 
        choices=TIPO_CHOICES, 
        default='deslocamento',
        verbose_name="Tipo",
        help_text="Tipo do deslocamento: ida ou volta"
    )
    
    # Até 6 pessoas por deslocamento (conforme planilha)
    pessoa_1 = models.ForeignKey(
        "Formador", 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name='deslocamentos_p1',
        verbose_name="Pessoa 1"
    )
    pessoa_2 = models.ForeignKey(
        "Formador", 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name='deslocamentos_p2',
        verbose_name="Pessoa 2"
    )
    pessoa_3 = models.ForeignKey(
        "Formador", 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name='deslocamentos_p3',
        verbose_name="Pessoa 3"
    )
    pessoa_4 = models.ForeignKey(
        "Formador", 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name='deslocamentos_p4',
        verbose_name="Pessoa 4"
    )
    pessoa_5 = models.ForeignKey(
        "Formador", 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name='deslocamentos_p5',
        verbose_name="Pessoa 5"
    )
    pessoa_6 = models.ForeignKey(
        "Formador", 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name='deslocamentos_p6',
        verbose_name="Pessoa 6"
    )
    
    # Campos de auditoria (serão adicionados na próxima migration)
    # created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    # updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    # DEPRECATED: Mantido por compatibilidade - remover em futuras versões
    formadores = models.ManyToManyField(
        "Formador", 
        related_name="deslocamentos_old",
        blank=True,
        help_text="DEPRECATED: Use pessoa_1 até pessoa_6"
    )

    class Meta:
        verbose_name = "Deslocamento"
        verbose_name_plural = "Deslocamentos"
        indexes = [
            models.Index(fields=["data"]),
            models.Index(fields=["data", "tipo"]),
            models.Index(fields=["origem", "destino"]),
        ]
        ordering = ["-data", "tipo"]
        constraints = [
            # Evitar deslocamentos muito no futuro (mais de 1 ano)
            models.CheckConstraint(
                check=models.Q(data__lte=timezone.now().date() + timedelta(days=365)),
                name="data_not_too_far_future",
                violation_error_message="Data não pode ser mais de 1 ano no futuro.",
            ),
        ]

    def __str__(self):
        tipo_icon = "→" if self.tipo == "deslocamento" else "←"
        return f"{self.data:%d/%m/%Y} {self.origem} {tipo_icon} {self.destino} ({self.get_tipo_display()})"
    
    @property
    def pessoas(self):
        """Retorna lista de pessoas não-nulas do deslocamento"""
        return [p for p in [
            self.pessoa_1, self.pessoa_2, self.pessoa_3, 
            self.pessoa_4, self.pessoa_5, self.pessoa_6
        ] if p is not None]
    
    @property
    def total_pessoas(self):
        """Retorna quantidade de pessoas no deslocamento"""
        return len(self.pessoas)
    
    def clean(self):
        """Validações customizadas"""
        from django.core.exceptions import ValidationError
        
        if not self.origem or not self.destino:
            raise ValidationError("Origem e destino são obrigatórios.")
        
        if self.origem == self.destino:
            raise ValidationError("Origem e destino não podem ser iguais.")
        
        # Verificar pessoas duplicadas
        pessoas = self.pessoas
        if len(pessoas) != len(set(pessoas)):
            raise ValidationError("Não é possível ter a mesma pessoa em posições diferentes.")
        
        # Deve ter pelo menos uma pessoa
        if len(pessoas) == 0:
            raise ValidationError("Deve ter pelo menos uma pessoa no deslocamento.")
    
    def save(self, *args, **kwargs):
        """Override save para executar validações"""
        self.clean()
        super().save(*args, **kwargs)


# =========================
# 5) SISTEMA DE NOTIFICAÇÕES
# =========================
class Notificacao(models.Model):
    """
    Sistema de notificações em tempo real para usuários.
    Exibe avisos no dashboard de cada perfil.
    """

    TIPOS_NOTIFICACAO = [
        # Solicitações
        ("solicitacao_nova", "Nova solicitação"),
        ("solicitacao_confirmacao", "Confirmação de solicitação"),
        ("solicitacao_aprovada", "Solicitação aprovada"),
        ("solicitacao_reprovada", "Solicitação reprovada"),
        # Pré-agenda e controle
        ("pre_agenda_nova", "Nova solicitação em pré-agenda"),
        ("pre_agenda_aprovada", "Solicitação aprovada → pré-agenda"),
        # Eventos
        ("evento_preparacao", "Evento em preparação"),
        ("evento_confirmado", "Evento confirmado"),
        ("evento_criado", "Evento criado no Google Calendar"),
        ("evento_cancelado", "Evento cancelado"),
        # Processos
        ("processo_concluido", "Processo concluído"),
        # Sistema
        ("sistema_manutencao", "Manutenção do sistema"),
        ("sistema_atualizacao", "Atualização disponível"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificacoes",
        verbose_name="Usuário",
    )

    tipo = models.CharField(
        max_length=30, choices=TIPOS_NOTIFICACAO, verbose_name="Tipo"
    )

    titulo = models.CharField(max_length=100, verbose_name="Título")

    mensagem = models.TextField(verbose_name="Mensagem")

    link_acao = models.URLField(blank=True, null=True, verbose_name="Link da ação")

    entidade_relacionada_id = models.UUIDField(
        blank=True,
        null=True,
        verbose_name="ID da entidade relacionada",
        help_text="ID da solicitação, evento, etc. relacionado à notificação",
    )

    lida = models.BooleanField(default=False, verbose_name="Lida")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "lida"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["tipo"]),
        ]

    def __str__(self):
        status = "✓" if self.lida else "●"
        return f"{status} {self.usuario.username}: {self.titulo}"


class LogComunicacao(models.Model):
    """
    Log de todas as comunicações enviadas pelo sistema.
    Visível apenas para administradores.
    """

    TIPOS_COMUNICACAO = [
        ("notificacao_sistema", "Notificação no sistema"),
        ("email", "E-mail"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("push_notification", "Push notification"),
    ]

    STATUS_ENVIO = [
        ("enviado", "Enviado com sucesso"),
        ("falhado", "Falha no envio"),
        ("pendente", "Pendente"),
        ("cancelado", "Cancelado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Quem enviou (sistema ou usuário específico)
    usuario_remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comunicacoes_enviadas",
        verbose_name="Remetente",
    )

    # Quem recebeu
    usuario_destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comunicacoes_recebidas",
        verbose_name="Destinatário",
    )

    # Para comunicações em massa (grupos)
    grupo_destinatario = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Grupo destinatário",
        help_text="superintendencia, controle, coordenador, etc.",
    )

    tipo_comunicacao = models.CharField(
        max_length=20, choices=TIPOS_COMUNICACAO, verbose_name="Tipo de comunicação"
    )

    assunto = models.CharField(max_length=200, verbose_name="Assunto")

    conteudo = models.TextField(verbose_name="Conteúdo")

    # Dados técnicos do envio
    endereco_destinatario = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Endereço destinatário",
        help_text="E-mail, telefone, etc.",
    )

    status_envio = models.CharField(
        max_length=20,
        choices=STATUS_ENVIO,
        default="pendente",
        verbose_name="Status do envio",
    )

    erro_envio = models.TextField(blank=True, verbose_name="Erro no envio")

    # Relacionamento com entidades
    entidade_relacionada_id = models.UUIDField(
        blank=True, null=True, verbose_name="ID da entidade relacionada"
    )

    entidade_relacionada_tipo = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Tipo da entidade",
        help_text="solicitacao, evento, etc.",
    )

    # Metadados
    metadados = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Metadados",
        help_text="Dados adicionais em JSON",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    enviado_em = models.DateTimeField(blank=True, null=True, verbose_name="Enviado em")

    class Meta:
        verbose_name = "Log de Comunicação"
        verbose_name_plural = "Logs de Comunicações"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["tipo_comunicacao", "status_envio"]),
            models.Index(fields=["usuario_destinatario", "status_envio"]),
            models.Index(fields=["grupo_destinatario"]),
        ]
        permissions = [
            ("view_logs_comunicacao", "Can view communication logs"),
        ]

    def __str__(self):
        destinatario = (
            self.usuario_destinatario.username
            if self.usuario_destinatario
            else self.grupo_destinatario
        )
        status_icon = (
            "✓"
            if self.status_envio == "enviado"
            else "✗" if self.status_envio == "falhado" else "⏳"
        )
        return f"{status_icon} {self.get_tipo_comunicacao_display()} → {destinatario}: {self.assunto}"


# =========================
# SISTEMA DE CURSOS DA PLATAFORMA
# =========================
class CursoPlataforma(models.Model):
    """Modelo para armazenar cursos da plataforma Aprender Formar"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_curso = models.CharField(max_length=50, unique=True, help_text="ID do curso na plataforma")
    categoria = models.CharField(max_length=200, help_text="Categoria do curso")
    nome_breve = models.CharField(max_length=200, help_text="Nome breve do curso")
    nome_limpo = models.CharField(max_length=200, blank=True, help_text="Nome processado pelo script de limpeza")
    ano = models.IntegerField(default=2025, help_text="Ano do curso")
    ativo = models.BooleanField(default=True)

    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Curso da Plataforma"
        verbose_name_plural = "Cursos da Plataforma"
        ordering = ['nome_breve']
        indexes = [
            models.Index(fields=['id_curso']),
            models.Index(fields=['categoria']),
            models.Index(fields=['ano', 'ativo']),
        ]

    def __str__(self):
        return f"{self.nome_breve} ({self.id_curso})"

    def get_link_curso(self):
        """Gera o link do curso na plataforma"""
        if self.id_curso:
            return f"https://aprenderformar.com.br/course/view.php?id={self.id_curso}"
        return ""


class ProjetoCursoLink(models.Model):
    """Vincula Projetos aos Cursos da Plataforma"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projeto = models.ForeignKey(
        'Projeto',
        on_delete=models.CASCADE,
        related_name='cursos_vinculados',
        help_text="Projeto do sistema"
    )
    curso_plataforma = models.ForeignKey(
        'CursoPlataforma',
        on_delete=models.CASCADE,
        help_text="Curso correspondente na plataforma"
    )

    # Campos de controle
    mapeamento_manual = models.BooleanField(
        default=False,
        help_text="Se o mapeamento foi feito manualmente ou automaticamente"
    )
    data_vinculacao = models.DateTimeField(auto_now_add=True)
    usuario_vinculacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Usuário que fez a vinculação"
    )

    class Meta:
        verbose_name = "Link Projeto-Curso"
        verbose_name_plural = "Links Projeto-Curso"
        unique_together = [('projeto', 'curso_plataforma')]
        ordering = ['projeto__nome', 'curso_plataforma__nome_breve']

    def __str__(self):
        manual_flag = " (Manual)" if self.mapeamento_manual else " (Auto)"
        return f"{self.projeto.nome} → {self.curso_plataforma.nome_breve}{manual_flag}"


class ImportacaoCursosCSV(models.Model):
    """Log das importações de CSV de cursos"""

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PROCESSANDO', 'Processando'),
        ('CONCLUIDA', 'Concluída'),
        ('ERRO', 'Erro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    arquivo_nome = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    total_linhas = models.IntegerField(default=0)
    cursos_importados = models.IntegerField(default=0)
    cursos_atualizados = models.IntegerField(default=0)
    vinculos_criados = models.IntegerField(default=0)

    # Logs
    log_processamento = models.TextField(blank=True)
    log_erros = models.TextField(blank=True)

    # Timestamps
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Importação CSV de Cursos"
        verbose_name_plural = "Importações CSV de Cursos"
        ordering = ['-data_inicio']

    def __str__(self):
        status_icon = {
            'PENDENTE': '⏳',
            'PROCESSANDO': '🔄',
            'CONCLUIDA': '✅',
            'ERRO': '❌'
        }.get(self.status, '❓')
        return f"{status_icon} {self.arquivo_nome} - {self.get_status_display()}"
