"""
AS v2 — DAT Registro Model

Model principal para acompanhamento de turmas educacionais.
Integra dados das plataformas FORMAR e AVALIAR.

Ref: v2/docs/SPEC_DAT_REGISTROS.md
Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models.organizacao import Municipio, Projeto, ProjetoGeral
    from apps.core.models.usuario import Usuario


class DATRegistro(models.Model):
    """
    Registro de acompanhamento DAT por município/projeto.

    Seções:
    1. Dados Básicos: município, projeto, quantidades
    2. Plataforma FORMAR: turma, códigos, status de envio
    3. Plataforma AVALIAR: alunos recebidos/validados/importados

    Regras de negócio:
    - nr_codigos é calculado automaticamente baseado em projeto_geral
    - usa_avaliar é derivado de projeto_geral.usa_avaliar
    - Campos AVALIAR só são relevantes quando usa_avaliar=True

    Constraints:
    - Unique: (municipio, projeto_geral, projeto) - um registro por combinação
    - external_hash: para idempotência de importação ETL

    Ref: SPEC_DAT_REGISTROS.md seção 2.2
    """

    STATUS_CHOICES = [
        ('concluido', 'Concluído'),
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('nao_aplicavel', 'Não Aplicável'),
        ('erro', 'Erro'),
    ]

    TURMA_STATUS_CHOICES = [
        ('criada', 'Criada'),
        ('pendente', 'Pendente'),
        ('erro', 'Erro'),
    ]

    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO 1: DADOS BÁSICOS
    # ═══════════════════════════════════════════════════════════════

    municipio: models.ForeignKey[Municipio] = models.ForeignKey(  # type: ignore[assignment]
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="dat_registros",
        verbose_name="Município",
    )
    projeto_geral: models.ForeignKey[ProjetoGeral] = models.ForeignKey(  # type: ignore[assignment]
        "core.ProjetoGeral",
        on_delete=models.PROTECT,
        related_name="dat_registros",
        verbose_name="Projeto Geral",
        help_text="Ex: ACERTA MATEMÁTICA, VIDA E LINGUAGEM"
    )
    projeto: models.ForeignKey[Projeto] = models.ForeignKey(  # type: ignore[assignment]
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="dat_registros",
        verbose_name="Projeto Específico",
        help_text="Ex: VIDA E LINGUAGEM 6, ACERTA BRASIL MATEMATICA"
    )
    aluno_qtde = models.PositiveIntegerField(
        verbose_name="Quantidade de Alunos",
        help_text="Total de alunos na turma"
    )
    professor_qtde = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Quantidade de Professores",
        help_text="Total de professores (necessário para cálculo de códigos)"
    )

    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO 2: PLATAFORMA FORMAR
    # ═══════════════════════════════════════════════════════════════

    reuniao_dat = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Reunião DAT",
        help_text="Data da reunião de alinhamento DAT"
    )
    turma_formar_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="ID Turma FORMAR",
        help_text="ID do curso na plataforma FORMAR"
    )
    turma_formar_status = models.CharField(
        max_length=10,
        choices=TURMA_STATUS_CHOICES,
        default='pendente',
        verbose_name="Status Turma FORMAR"
    )

    # Calculado automaticamente baseado em projeto_geral
    nr_codigos = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Nº de Códigos",
        help_text="Calculado automaticamente baseado em projeto_geral"
    )

    # Status de envio FORMAR com datas
    chaves_inscricao_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Chaves de Inscrição"
    )
    chaves_inscricao_data = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Chaves Inscrição"
    )

    instrucoes_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Instruções"
    )
    instrucoes_data = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Instruções"
    )

    envio_codigos_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Envio de Códigos"
    )
    envio_codigos_data = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Envio Códigos"
    )

    obs_formar = models.TextField(
        blank=True,
        max_length=1000,
        verbose_name="Observações FORMAR"
    )

    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO 3: PLATAFORMA AVALIAR
    # ═══════════════════════════════════════════════════════════════

    # Derivado de projeto_geral.usa_avaliar (readonly no form)
    usa_avaliar = models.BooleanField(
        default=False,
        verbose_name="Usa AVALIAR",
        help_text="Preenchido automaticamente baseado no Projeto Geral"
    )

    alunos_recebidos_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='nao_aplicavel',
        verbose_name="Alunos Recebidos"
    )
    alunos_recebidos_datas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Datas Recebimento",
        help_text="Array de datas: ['2025-03-12', '2025-04-25']"
    )

    alunos_validados_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='nao_aplicavel',
        verbose_name="Alunos Validados"
    )
    alunos_validados_datas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Datas Validação"
    )

    alunos_importados_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='nao_aplicavel',
        verbose_name="Alunos Importados"
    )
    alunos_importados_datas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Datas Importação"
    )

    obs_avaliar = models.TextField(
        blank=True,
        max_length=1000,
        verbose_name="Observações AVALIAR"
    )

    # ═══════════════════════════════════════════════════════════════
    # AUDITORIA E ETL
    # ═══════════════════════════════════════════════════════════════

    external_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Hash Externo",
        help_text="Para idempotência de importação ETL"
    )
    created_by: models.ForeignKey[Usuario] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="dat_registros_criados",
        verbose_name="Criado por"
    )
    updated_by: models.ForeignKey[Usuario | None] = models.ForeignKey(  # type: ignore[assignment]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_registros_atualizados",
        verbose_name="Atualizado por"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_dat_registro"
        verbose_name = "Registro DAT"
        verbose_name_plural = "Registros DAT"
        ordering = ["-created_at", "municipio__nome"]
        indexes = [
            models.Index(fields=["municipio", "projeto_geral", "projeto"]),
            models.Index(fields=["projeto_geral", "usa_avaliar"]),
            models.Index(fields=["external_hash"]),
            models.Index(fields=["turma_formar_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "projeto_geral", "projeto"],
                name="unique_dat_registro_municipio_projeto"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.municipio.nome}-{self.municipio.uf} | {self.projeto.nome}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save para calcular campos automáticos."""
        # Sincronizar usa_avaliar com projeto_geral
        if self.projeto_geral_id:
            self.usa_avaliar = self.projeto_geral.usa_avaliar

        # Calcular nr_codigos
        self.nr_codigos = self._calcular_nr_codigos()

        # Atualizar status AVALIAR se não usa
        if not self.usa_avaliar:
            self.alunos_recebidos_status = 'nao_aplicavel'
            self.alunos_validados_status = 'nao_aplicavel'
            self.alunos_importados_status = 'nao_aplicavel'

        super().save(*args, **kwargs)

    def _calcular_nr_codigos(self) -> int | None:
        """
        Calcula número de códigos baseado nas regras do projeto_geral.

        Regras:
        - por_aluno: ceil(aluno_qtde / divisor)
        - por_professor: ceil(professor_qtde * multiplicador)
        - nao_aplicavel: None
        """
        if not self.projeto_geral_id:
            return None

        tipo = self.projeto_geral.tipo_calculo_codigos

        if tipo == 'nao_aplicavel':
            return None

        if tipo == 'por_aluno':
            if self.aluno_qtde and self.projeto_geral.divisor_aluno:
                return math.ceil(self.aluno_qtde / self.projeto_geral.divisor_aluno)
            return None

        if tipo == 'por_professor':
            if self.professor_qtde and self.projeto_geral.multiplicador_professor:
                mult = float(self.projeto_geral.multiplicador_professor)
                return math.ceil(self.professor_qtde * mult)
            return None

        return None

    @property
    def turma_formar_url(self) -> str | None:
        """Gera URL da turma na plataforma FORMAR."""
        if self.turma_formar_id:
            base_url = getattr(settings, 'FORMAR_PLATFORM_BASE_URL', 'https://www.aprenderformar.com.br/plataforma')
            return f"{base_url}/course/view.php?id={self.turma_formar_id}"
        return None

    @property
    def status_geral(self) -> str:
        """
        Calcula status geral do registro.

        Returns:
            - 'completo': Todos os campos obrigatórios concluídos
            - 'pendente_formar': Campos FORMAR pendentes
            - 'pendente_avaliar': Campos AVALIAR pendentes (se usa_avaliar)
        """
        # Verifica campos FORMAR obrigatórios
        formar_ok = all([
            self.chaves_inscricao_status == 'concluido',
            self.instrucoes_status == 'concluido',
            self.envio_codigos_status == 'concluido',
        ])

        if not formar_ok:
            return 'pendente_formar'

        # Se usa AVALIAR, verifica campos AVALIAR
        if self.usa_avaliar:
            avaliar_ok = all([
                self.alunos_recebidos_status == 'concluido',
                self.alunos_validados_status == 'concluido',
                self.alunos_importados_status == 'concluido',
            ])
            if not avaliar_ok:
                return 'pendente_avaliar'

        return 'completo'
