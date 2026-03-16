"""
AS v2 — Acoes e Notificacoes Internas (32 Passos)

Models de dominio para:
- template das acoes;
- ciclo por projeto/municipio/semestre/ano;
- execucao com ancora e conclusao;
- feriados locais para calculo de dias uteis;
- inbox de notificacoes internas.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.usuario import Usuario


class TipoAncoraChoices(models.TextChoices):
    EVENTO_EXTERNO = "EVENTO_EXTERNO", "Evento Externo"
    ACAO_ANTERIOR = "ACAO_ANTERIOR", "Acao Anterior"
    MARCO_CALENDARIO = "MARCO_CALENDARIO", "Marco de Calendario"


class SemestreChoices(models.TextChoices):
    PRIMEIRO = "1S", "1º Semestre"
    SEGUNDO = "2S", "2º Semestre"


class StatusCicloChoices(models.TextChoices):
    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    CONCLUIDO = "CONCLUIDO", "Concluido"
    CONCLUIDO_COM_ATRASO = "CONCLUIDO_COM_ATRASO", "Concluido com atraso"


class EstadoAcaoChoices(models.TextChoices):
    AGUARDANDO_ANCORA = "AGUARDANDO_ANCORA", "Aguardando ancora"
    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    CONCLUIDA = "CONCLUIDA", "Concluida"
    ATRASADA = "ATRASADA", "Atrasada"


class AbrangenciaFeriadoChoices(models.TextChoices):
    NACIONAL = "NACIONAL", "Nacional (Brasil)"
    ESTADUAL_CE = "ESTADUAL_CE", "Estadual (Ceara)"
    MUNICIPAL_FORTALEZA = "MUNICIPAL_FORTALEZA", "Municipal (Fortaleza)"


class TipoNotificacaoChoices(models.TextChoices):
    LEMBRETE = "LEMBRETE", "Lembrete"
    VENCIMENTO = "VENCIMENTO", "Vencimento"
    ATRASO = "ATRASO", "Atraso"
    ESCALONAMENTO = "ESCALONAMENTO", "Escalonamento"


class NivelNotificacaoChoices(models.TextChoices):
    RESPONSAVEL = "RESPONSAVEL", "Responsavel"
    COORDENADOR = "COORDENADOR", "Coordenador"
    GERENTE = "GERENTE", "Gerente"
    DAT = "DAT", "DAT"


class PrioridadeNotificacaoChoices(models.TextChoices):
    BAIXA = "BAIXA", "Baixa"
    MEDIA = "MEDIA", "Media"
    ALTA = "ALTA", "Alta"
    CRITICA = "CRITICA", "Critica"


class AcaoTemplate(models.Model):
    """
    Template da acao (1..32), com regra de prazo e ancora.
    """

    ordem = models.PositiveIntegerField(unique=True, db_index=True)
    nome = models.CharField(max_length=255)
    descricao_prazo = models.TextField(
        help_text="Descricao original da regra de prazo (texto de negocio).",
    )
    tipo_ancora = models.CharField(
        max_length=20,
        choices=TipoAncoraChoices.choices,
    )
    ref_acao_template = models.ForeignKey(  # type: ignore[misc]
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="acoes_dependentes",
    )
    ref_evento_externo = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Identificador de evento externo quando tipo_ancora != ACAO_ANTERIOR.",
    )
    dias_prazo_uteis = models.PositiveIntegerField(
        help_text="Prazo em dias uteis a partir da ancora.",
    )
    ativo = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_acao_template"
        verbose_name = "Acao Template"
        verbose_name_plural = "Acoes Template"
        ordering = ["ordem"]
        constraints = [
            models.CheckConstraint(check=models.Q(ordem__gt=0), name="acao_template_ordem_gt_zero"),
            models.CheckConstraint(
                check=models.Q(dias_prazo_uteis__gt=0),
                name="acao_template_prazo_gt_zero",
            ),
            models.CheckConstraint(
                check=(~models.Q(tipo_ancora=TipoAncoraChoices.ACAO_ANTERIOR))
                | models.Q(ref_acao_template__isnull=False),
                name="acao_template_ancora_acao_requer_ref",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(tipo_ancora__in=[TipoAncoraChoices.ACAO_ANTERIOR, TipoAncoraChoices.MARCO_CALENDARIO])
                    | ~models.Q(ref_evento_externo="")
                ),
                name="acao_template_ancora_evento_requer_ref",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ordem:02d} - {self.nome}"


class AcaoTemplateExecutor(models.Model):
    """
    Mapeamento editavel: qual grupo executor recebe cada acao.
    """

    acao_template = models.ForeignKey(  # type: ignore[misc]
        "core.AcaoTemplate",
        on_delete=models.CASCADE,
        related_name="executores",
    )
    group = models.ForeignKey(  # type: ignore[misc]
        Group,
        on_delete=models.CASCADE,
        related_name="acoes_template",
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_acao_template_executor"
        verbose_name = "Executor de Acao Template"
        verbose_name_plural = "Executores de Acoes Template"
        ordering = ["acao_template__ordem", "group__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["acao_template", "group"],
                name="unique_acao_template_executor_group",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.acao_template} -> {self.group.name}"  # type: ignore[attr-defined]


class CicloAcoes(models.Model):
    """
    Instancia operacional das 32 acoes para um contexto de negocio.
    """

    projeto = models.ForeignKey(  # type: ignore[misc]
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="ciclos_acoes",
    )
    municipio = models.ForeignKey(  # type: ignore[misc]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="ciclos_acoes",
    )
    semestre = models.CharField(max_length=2, choices=SemestreChoices.choices)
    ano = models.PositiveIntegerField(db_index=True)
    status = models.CharField(
        max_length=25,
        choices=StatusCicloChoices.choices,
        default=StatusCicloChoices.EM_ANDAMENTO,
    )
    created_by = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ciclos_acoes_criados",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_ciclo_acoes"
        verbose_name = "Ciclo de Acoes"
        verbose_name_plural = "Ciclos de Acoes"
        ordering = ["-ano", "semestre", "projeto__nome", "municipio__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["projeto", "municipio", "semestre", "ano"],
                name="unique_ciclo_acoes_contexto",
            ),
            models.CheckConstraint(check=models.Q(ano__gte=2020), name="ciclo_acoes_ano_min_2020"),
        ]

    def __str__(self) -> str:
        return f"{self.projeto.nome} | {self.municipio.nome} | {self.semestre}/{self.ano}"  # type: ignore[attr-defined]


class AcaoInstancia(models.Model):
    """
    Estado operacional de cada acao dentro de um ciclo.
    """

    ciclo = models.ForeignKey(  # type: ignore[misc]
        "core.CicloAcoes",
        on_delete=models.CASCADE,
        related_name="acoes",
    )
    template = models.ForeignKey(  # type: ignore[misc]
        "core.AcaoTemplate",
        on_delete=models.PROTECT,
        related_name="instancias",
    )
    ordem = models.PositiveIntegerField(db_index=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoAcaoChoices.choices,
        default=EstadoAcaoChoices.AGUARDANDO_ANCORA,
    )

    data_ancora = models.DateField(null=True, blank=True)
    data_vencimento = models.DateField(null=True, blank=True)
    data_realizacao = models.DateField(null=True, blank=True)

    observacao_conclusao = models.TextField(blank=True, default="")
    concluida_por = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acoes_instancia_concluidas",
    )
    concluida_em = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_acao_instancia"
        verbose_name = "Acao Instancia"
        verbose_name_plural = "Acoes Instancia"
        ordering = ["ciclo", "ordem"]
        constraints = [
            models.UniqueConstraint(
                fields=["ciclo", "ordem"],
                name="unique_acao_instancia_ciclo_ordem",
            ),
            models.UniqueConstraint(
                fields=["ciclo", "template"],
                name="unique_acao_instancia_ciclo_template",
            ),
            models.CheckConstraint(check=models.Q(ordem__gt=0), name="acao_instancia_ordem_gt_zero"),
            models.CheckConstraint(
                check=(~models.Q(estado=EstadoAcaoChoices.CONCLUIDA)) | models.Q(data_realizacao__isnull=False),
                name="acao_instancia_concluida_requer_data_realizacao",
            ),
            models.CheckConstraint(
                check=(~models.Q(estado=EstadoAcaoChoices.CONCLUIDA)) | (~models.Q(observacao_conclusao="")),
                name="acao_instancia_concluida_requer_observacao",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ciclo} | {self.ordem:02d} | {self.estado}"  # type: ignore[attr-defined]

    def clean(self) -> None:
        super().clean()
        if self.template and self.ordem != self.template.ordem:  # pyright: ignore[reportUnknownMemberType]
            raise ValidationError({"ordem": "Ordem da instancia deve ser igual a ordem do template."})

    def registrar_ancora(
        self,
        *,
        data_ancora: date,
        usuario: "Usuario",
        observacao: str = "",
    ) -> "RegistroAncora":
        if self.estado == EstadoAcaoChoices.CONCLUIDA:
            raise ValidationError("Nao e permitido alterar ancora de acao concluida.")

        from apps.core.services.prazo_engine_service import PrazoEngineService

        with transaction.atomic():
            PrazoEngineService.recalculate_action(
                self,
                explicit_anchor_date=data_ancora,
                save=True,
            )

            return RegistroAncora.objects.create(
                acao_instancia=self,
                data_ancora=data_ancora,
                observacao=observacao,
                registrado_por=usuario,
            )

    def concluir(
        self,
        *,
        data_realizacao: date,
        observacao: str,
        usuario: "Usuario",
    ) -> "RegistroConclusaoAcao":
        if self.estado == EstadoAcaoChoices.CONCLUIDA:
            raise ValidationError("Acao ja concluida. Reabertura nao permitida no MVP.")

        obs = observacao.strip()
        if not obs:
            raise ValidationError({"observacao": "Observacao e obrigatoria para concluir a acao."})

        with transaction.atomic():
            from apps.core.services.prazo_engine_service import PrazoEngineService

            self.estado = EstadoAcaoChoices.CONCLUIDA
            self.data_realizacao = data_realizacao
            self.observacao_conclusao = obs
            self.concluida_por = usuario
            self.concluida_em = timezone.now()
            self.save(
                update_fields=[
                    "estado",
                    "data_realizacao",
                    "observacao_conclusao",
                    "concluida_por",
                    "concluida_em",
                    "updated_at",
                ]
            )

            if RegistroConclusaoAcao.objects.filter(acao_instancia=self).exists():
                raise ValidationError("Registro de conclusao ja existe para esta acao.")

            registro = RegistroConclusaoAcao.objects.create(
                acao_instancia=self,
                data_realizacao=data_realizacao,
                observacao=obs,
                registrado_por=usuario,
            )
            PrazoEngineService.recalculate_dependents(self)
            return registro


class RegistroAncora(models.Model):
    """
    Historico de registros/alteracoes de ancora por acao.
    """

    acao_instancia = models.ForeignKey(  # type: ignore[misc]
        "core.AcaoInstancia",
        on_delete=models.CASCADE,
        related_name="registros_ancora",
    )
    data_ancora = models.DateField()
    observacao = models.TextField(blank=True, default="")
    registrado_por = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_ancora",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_registro_ancora"
        verbose_name = "Registro de Ancora"
        verbose_name_plural = "Registros de Ancora"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["acao_instancia", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.acao_instancia} | ancora={self.data_ancora}"  # type: ignore[attr-defined]


class RegistroConclusaoAcao(models.Model):
    """
    Registro de conclusao da acao (nao reabrivel no MVP).
    """

    acao_instancia = models.OneToOneField(  # type: ignore[misc]
        "core.AcaoInstancia",
        on_delete=models.CASCADE,
        related_name="registro_conclusao",
    )
    data_realizacao = models.DateField()
    observacao = models.TextField()
    registrado_por = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_conclusao_acao",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_registro_conclusao_acao"
        verbose_name = "Registro de Conclusao da Acao"
        verbose_name_plural = "Registros de Conclusao da Acao"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.acao_instancia} | realizado={self.data_realizacao}"  # type: ignore[attr-defined]


class FeriadoLocal(models.Model):
    """
    Feriado configuravel para calendario util do modulo.
    """

    data = models.DateField(db_index=True)
    nome = models.CharField(max_length=150)
    abrangencia = models.CharField(max_length=25, choices=AbrangenciaFeriadoChoices.choices)
    ativo = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_feriado_local"
        verbose_name = "Feriado Local"
        verbose_name_plural = "Feriados Locais"
        ordering = ["data", "abrangencia", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["data", "abrangencia", "nome"],
                name="unique_feriado_local_data_abrangencia_nome",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.data} | {self.abrangencia} | {self.nome}"


class NotificacaoInterna(models.Model):
    """
    Inbox de notificacoes internas para usuario logado.
    """

    destinatario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.CASCADE,
        related_name="notificacoes_internas",
    )
    acao_instancia = models.ForeignKey(  # type: ignore[misc]
        "core.AcaoInstancia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes",
    )

    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=20, choices=TipoNotificacaoChoices.choices)
    nivel = models.CharField(max_length=15, choices=NivelNotificacaoChoices.choices)
    prioridade = models.CharField(
        max_length=10,
        choices=PrioridadeNotificacaoChoices.choices,
        default=PrioridadeNotificacaoChoices.MEDIA,
    )

    fase_disparo = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Exemplo: D-7, D0, D+1, D+3.",
    )
    referencia_data = models.DateField(default=timezone.localdate, db_index=True)

    lida = models.BooleanField(default=False, db_index=True)
    lida_em = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_notificacao_interna"
        verbose_name = "Notificacao Interna"
        verbose_name_plural = "Notificacoes Internas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["destinatario", "lida", "created_at"]),
            models.Index(fields=["acao_instancia", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["destinatario", "acao_instancia", "fase_disparo", "referencia_data"],
                name="unique_notificacao_interna_escopo_disparo",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.destinatario.username} | {self.titulo}"  # type: ignore[attr-defined]

    def marcar_lida(self) -> None:
        if self.lida:
            return

        self.lida = True
        self.lida_em = timezone.now()
        self.save(update_fields=["lida", "lida_em", "updated_at"])
