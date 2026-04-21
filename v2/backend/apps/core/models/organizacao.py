"""
AS v2 — Organizacao Models

Models organizacionais: Municipio, Gerencia, EquipeGerencia, ProjetoGeral, Projeto, TipoEvento, Produto.
SSOT: Substitui IMPORTRANGE de planilhas organizacionais.
Type-checked with Pyright (strict mode).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from apps.core.models.usuario import Usuario


class ProjetoGeral(models.Model):
    """
    Agrupa projetos relacionados e define regras de negócio para cálculo de códigos.

    Exemplo:
    - ProjetoGeral: "VIDA E LINGUAGEM"
      - Projetos específicos: VIDA E LINGUAGEM 6, 7, 8, 9
      - usa_avaliar: True (usa plataforma AVALIAR)
      - tipo_calculo: por_professor, multiplicador: 1.1

    Regras de cálculo de códigos FORMAR:
    - por_aluno: ceil(qtde_alunos / divisor_aluno)
    - por_professor: ceil(qtde_professores * multiplicador_professor)
    - nao_aplicavel: não gera códigos

    Ref: SPEC_DAT_REGISTROS.md seção 2.1
    """

    TIPO_CALCULO_CHOICES = [
        ("por_aluno", "Por Aluno (qtde_alunos / divisor)"),
        ("por_professor", "Por Professor (qtde_professores * multiplicador)"),
        ("nao_aplicavel", "Não Aplicável (não gera códigos)"),
    ]

    nome = models.CharField(
        max_length=100, unique=True, db_index=True, help_text="Ex: ACERTA MATEMÁTICA, VIDA E LINGUAGEM"
    )
    usa_avaliar = models.BooleanField(default=False, help_text="Se o projeto utiliza a plataforma AVALIAR")
    tipo_calculo_codigos = models.CharField(
        max_length=15,
        choices=TIPO_CALCULO_CHOICES,
        default="por_professor",
        help_text="Como calcular número de códigos FORMAR",
    )
    divisor_aluno = models.PositiveIntegerField(
        default=20, help_text="Divisor quando tipo = por_aluno (ex: 200 alunos / 20 = 10 códigos)"
    )
    multiplicador_professor = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("1.1"),
        help_text="Multiplicador quando tipo = por_professor (ex: 10 professores * 1.1 = 11 códigos)",
    )
    ativo = models.BooleanField(default=True)
    descricao = models.TextField(blank=True, help_text="Descrição adicional do projeto geral")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_projeto_geral"
        verbose_name = "Projeto Geral"
        verbose_name_plural = "Projetos Gerais"
        ordering = ["nome"]

    def __str__(self) -> str:
        avaliar = "✅" if self.usa_avaliar else "⭕"
        return f"{self.nome} {avaliar}"


class Municipio(models.Model):
    """SSOT: Substitui IMPORTRANGE de Municipios"""

    nome = models.CharField(max_length=100, db_index=True)
    uf = models.CharField(max_length=2)
    ibge_code = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name="Codigo IBGE",
        help_text="Codigo IBGE de 7 digitos do municipio",
    )
    ativo = models.BooleanField(default=True)

    # Coordenadas geograficas para visualizacao em mapa
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitude em graus decimais (-90 a 90)"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitude em graus decimais (-180 a 180)"
    )

    class Meta:  # type: ignore[misc]
        db_table = "core_municipio"
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["nome", "uf"], name="unique_municipio_nome_uf"),
            models.CheckConstraint(
                condition=models.Q(latitude__gte=-90, latitude__lte=90) | models.Q(latitude__isnull=True),
                name="latitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__gte=-180, longitude__lte=180) | models.Q(longitude__isnull=True),
                name="longitude_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nome}-{self.uf}"


class MunicipioReferencia(models.Model):
    """
    Lista de referência de municípios (fonte externa).

    Usado para métricas de cobertura nacional e validações de consistência.
    """

    codigo_externo = models.CharField(
        max_length=20,
        db_index=True,
        help_text="ID do município na fonte externa (não confundir com IBGE)",
    )
    nome = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    fonte = models.CharField(max_length=50, default="sistemasaprender", db_index=True)
    ativo = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_municipio_referencia"
        verbose_name = "Municipio Referencia"
        verbose_name_plural = "Municipios Referencia"
        ordering = ["uf", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["fonte", "codigo_externo"],
                name="unique_municipio_ref_codigo_fonte",
            ),
            models.UniqueConstraint(
                fields=["fonte", "nome", "uf"],
                name="unique_municipio_ref_nome_uf_fonte",
            ),
        ]
        indexes = [
            models.Index(fields=["nome", "uf"]),
        ]

    def __str__(self) -> str:
        return f"{self.nome}-{self.uf} ({self.fonte})"


class Gerencia(models.Model):
    """
    Gerencia organizacional (GERENCIA 2, GERENCIA 3, SUPERINTENDENCIA, etc.).

    Cada gerencia agrupa projetos relacionados e pode ter um gerente responsavel.

    Examples:
        - GERENCIA 2 -> Setor "Vidas" (VIDA E CIENCIAS, LINGUAGEM, MATEMATICA)
        - GERENCIA 3 -> Setor "Fluir" (FLUIR DAS EMOCOES)
        - GERENCIA 4 -> Setor "ACerta" (ACERTA MATEMATICA, PORTUGUES, ECS)
        - SUPERINTENDENCIA -> Setor "Super" (projetos SUPER que requerem aprovacao)
        - GERENCIA INDIVIDUAL -> Setor "Individual" (projetos com gerencia individual)

    Attributes:
        nome (str): Nome da gerencia (ex: GERENCIA 2, SUPERINTENDENCIA)
        nome_setor (str): Nome comercial/operacional do setor (ex: Vidas, ACerta, Fluir)
        gerente (FK Usuario): Gerente responsavel pela gerencia (nullable)
        ativo (bool): Se a gerencia esta ativa
        descricao (str): Descricao adicional
    """

    nome = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Nome da gerencia (ex: GERENCIA 2, SUPERINTENDENCIA)",
    )
    nome_setor = models.CharField(
        max_length=100,
        help_text="Nome comercial/operacional do setor (ex: Vidas, ACerta, Fluir)",
    )
    gerente = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gerencias_gerenciadas",
        help_text="Gerente responsavel pela gerencia",
    )
    ativo = models.BooleanField(default=True)
    descricao = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_gerencia"
        verbose_name = "Gerencia"
        verbose_name_plural = "Gerencias"
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.nome_setor})"


class EquipeGerencia(models.Model):
    """
    Hierarquia de equipe dentro de uma gerencia.

    Define a estrutura organizacional: quem pertence a qual setor e qual papel exerce.

    Hierarquia tipica:
    Gerente (1) -> Coordenador (N) -> Apoio de Coordenacao (N) -> Formadores (N)

    Example:
        GERENCIA 2 (Vidas):
        - Gerente: Joao Silva (papel=GERENTE)
        - Coordenador: Maria Santos (papel=COORDENADOR)
          - Apoio: Ana Costa (papel=APOIO, coordenador_supervisor=Maria)
        - Formadores: Carlos, Luiza, Rafael (papel=FORMADOR)

    Nota sobre Gerencias Individuais:
        Para projetos com gerencia individual (ex: A COR DA GENTE),
        a mesma pessoa pode ter multiplos registros com papeis diferentes
        (GERENTE + COORDENADOR + FORMADOR).
    """

    PAPEL_CHOICES = [
        ("GERENTE", "Gerente"),
        ("COORDENADOR", "Coordenador"),
        ("APOIO", "Apoio de Coordenacao"),
        ("FORMADOR", "Formador"),
    ]

    gerencia = models.ForeignKey(  # type: ignore[misc]
        Gerencia,
        on_delete=models.PROTECT,
        related_name="equipes",
        help_text="Gerencia/setor ao qual o usuario pertence",
    )
    usuario = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="equipes",
        help_text="Usuario membro da equipe",
    )
    papel = models.CharField(
        max_length=15,
        choices=PAPEL_CHOICES,
        help_text="Papel do usuario nesta gerencia",
    )
    coordenador_supervisor = models.ForeignKey(  # type: ignore[misc]
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apoios_supervisionados",
        help_text="Coordenador que este apoio auxilia (apenas para papel APOIO)",
    )
    ativo = models.BooleanField(
        default=True,
        help_text="Se esta atribuicao esta ativa",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_equipe_gerencia"
        verbose_name = "Equipe de Gerencia"
        verbose_name_plural = "Equipes de Gerencias"
        ordering = ["gerencia", "papel", "usuario"]
        constraints = [
            models.UniqueConstraint(
                fields=["gerencia", "usuario", "papel"],
                name="unique_equipe_gerencia_usuario_papel",
            ),
            models.CheckConstraint(
                condition=(~models.Q(papel="APOIO") | models.Q(coordenador_supervisor__isnull=False)),
                name="apoio_requires_supervisor",
                violation_error_message="Apoio de Coordenacao deve ter um coordenador supervisor",
            ),
        ]
        indexes = [
            # ASQ-004: hot path do grid mensal filtra por (gerencia, papel, ativo).
            # O UniqueConstraint em (gerencia, usuario, papel) cobre lookups
            # compostos mas não começa por (gerencia, papel) — este índice
            # evita o seq scan com centenas de membros.
            models.Index(
                fields=["gerencia", "papel", "ativo"],
                name="idx_equipe_ger_papel_ativo",
            ),
        ]

    def __str__(self) -> str:
        papel = self.get_papel_display()  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
        return f"{self.usuario.get_full_name() or self.usuario.username} - {papel} ({self.gerencia.nome_setor})"  # type: ignore[reportUnknownMemberType]


class Projeto(models.Model):
    """SSOT: Substitui IMPORTRANGE de Projetos"""

    FLUXO_CHOICES = [
        ("SUPER", "Superintendencia"),
        ("NAO_SUPER", "Nao-Superintendencia"),
    ]

    nome = models.CharField(max_length=200, unique=True, db_index=True)
    codigo = models.CharField(
        max_length=50,
        null=False,
        blank=True,
        default="",
        db_index=True,
        help_text="Codigo unico do projeto (ex: ACERTA, NLENDO). Unique apenas quando preenchido.",
    )
    fluxo = models.CharField(
        max_length=12,
        choices=FLUXO_CHOICES,
        default="NAO_SUPER",
        db_index=True,
        help_text="SUPER: requer aprovacao da Superintendencia. NAO_SUPER: auto-aprovado.",
    )
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    # Issue #145: Hierarquia organizacional
    gerencia = models.ForeignKey(  # type: ignore[misc]
        "core.Gerencia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="projetos",
        help_text="Gerencia a qual o projeto pertence (ex: GERENCIA 2 - Vidas)",
    )

    # DAT Registros: Agrupamento por projeto geral
    projeto_geral = models.ForeignKey(  # type: ignore[misc]
        "core.ProjetoGeral",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projetos_especificos",
        help_text="Projeto geral pai (ex: VIDA E LINGUAGEM para VIDA E LINGUAGEM 6)",
    )

    is_test = models.BooleanField(
        default=False,
        help_text="Marca projeto como teste (nao exibir em producao)",
    )

    class Meta:  # type: ignore[misc]
        db_table = "core_projeto"
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                condition=~models.Q(codigo=""),
                name="unique_projeto_codigo_nonempty",
            ),
            # Issue #136: Check constraint for fluxo choices
            models.CheckConstraint(
                condition=models.Q(fluxo__in=["SUPER", "NAO_SUPER"]),
                name="projeto_fluxo_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.nome


class TipoEvento(models.Model):
    """SSOT: Substitui IMPORTRANGE de Tipos de Evento"""

    nome = models.CharField(max_length=100, unique=True, db_index=True)
    descricao = models.TextField(blank=True)
    cor = models.CharField(max_length=7, blank=True, help_text="Cor hex (#RRGGBB)")

    class Meta:  # type: ignore[misc]
        db_table = "core_tipo_evento"
        verbose_name = "Tipo de Evento"
        verbose_name_plural = "Tipos de Evento"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Colecao(models.Model):
    """
    Colecao de produtos (ex: A COR DA GENTE 1, BRINCANDO E APRENDENDO 2).

    Uma colecao agrupa produtos de um mesmo projeto.
    Exemplo: Projeto "Novo Lendo" tem colecoes "Colecao 1", "Colecao 2", etc.
    """

    nome = models.CharField(max_length=200, help_text="Nome da colecao (ex: A COR DA GENTE 1)")
    projeto: models.ForeignKey[Projeto] = models.ForeignKey(  # type: ignore[assignment]
        "core.Projeto", on_delete=models.PROTECT, related_name="colecoes", help_text="Projeto vinculado"
    )
    descricao = models.TextField(blank=True, help_text="Descricao da colecao")
    ativo = models.BooleanField(default=True, help_text="Colecao ativa")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_colecao"
        verbose_name = "Colecao"
        verbose_name_plural = "Colecoes"
        ordering = ["projeto", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["nome", "projeto"], name="unique_colecao_nome_projeto"),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.projeto.nome})"


class Produto(models.Model):
    """
    SSOT: Produtos disponiveis (substitui produtos.xlsx).

    Fonte: produtos.xlsx (139 produtos)
    Cross-ref: Compras.xlsx (valida codigos)

    Relacionamentos:
        - Produto -> Projeto (many-to-one, obrigatorio)
        - Produto -> Colecao (many-to-one, opcional)
        - Compra -> Produto (many-to-one, obrigatorio apos migration)

    Exemplo:
        NL-C1 -> "Novo Lendo - Colecao 1" -> Projeto "Novo Lendo"
    """

    codigo = models.CharField(max_length=50, unique=True, db_index=True, help_text="Codigo unico (ex: NL-C1, GE-KB)")
    nome = models.CharField(max_length=200, help_text="Nome completo do produto")
    descricao = models.TextField(blank=True, help_text="Descricao detalhada")
    projeto: models.ForeignKey[Projeto] = models.ForeignKey(  # type: ignore[assignment]
        "core.Projeto", on_delete=models.PROTECT, related_name="produtos", help_text="Projeto vinculado"
    )
    colecao: models.ForeignKey["Colecao"] | None = models.ForeignKey(  # type: ignore[assignment]
        "core.Colecao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produtos",
        help_text="Colecao do produto",
    )
    ativo = models.BooleanField(default=True, help_text="Produto disponivel")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore[misc]
        db_table = "core_produto"
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["codigo"]
        indexes = [
            models.Index(fields=["codigo", "ativo"]),
            models.Index(fields=["projeto"]),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nome}"
