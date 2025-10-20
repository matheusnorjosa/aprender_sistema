"""
Modelos de Staging para Ingestão de CSVs ETL (DAT-P01 a P04)

App: dat_ingest
Stack: Python 3.13 | Django 5.2 | PostgreSQL 15
Timezone: America/Fortaleza

Propósito: Data Lake staging para armazenar dados brutos dos CSVs
sem relacionamento com modelos existentes (core.Usuario, core.Municipio etc.)

Idempotência garantida por chaves únicas (external_hash, row_hash).
"""

from django.db import models


class StgEvento(models.Model):
    """
    Staging de eventos da planilha Agenda (events.csv do DAT-P01).

    Chave primária: external_hash (SHA1 da linha original).
    Upsert via update_or_create(external_hash=...).
    """

    external_hash = models.CharField(
        max_length=40,
        primary_key=True,
        db_index=True,
        help_text="SHA1 hash da linha original (chave única)",
    )

    # Metadados da planilha
    planilha = models.CharField(max_length=200, blank=True, default="")
    aba = models.CharField(max_length=100, blank=True, default="")
    fluxo = models.CharField(max_length=50, blank=True, default="")

    # Aprovação
    aprovacao = models.CharField(max_length=100, blank=True, default="")
    aprovado_futuro = models.CharField(max_length=10, blank=True, default="")
    criado_na_agenda = models.CharField(max_length=10, blank=True, default="")

    # Localização e identificação
    municipio = models.CharField(max_length=200, blank=True, default="", db_index=True)
    encontro = models.CharField(max_length=50, blank=True, default="")
    tipo = models.CharField(max_length=200, blank=True, default="")

    # Data e horário
    data = models.DateField(null=True, blank=True, db_index=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)

    # Projeto e segmento
    projeto = models.CharField(max_length=200, blank=True, default="")
    segmento = models.CharField(max_length=200, blank=True, default="")

    # Coordenação
    coord_acompanha = models.CharField(max_length=200, blank=True, default="")
    coordenador = models.CharField(max_length=200, blank=True, default="")

    # Participantes (concatenados com |)
    formadores = models.TextField(blank=True, default="")
    convidados = models.TextField(blank=True, default="")

    # Status
    cancelado_info = models.CharField(max_length=50, blank=True, default="")
    solicitante = models.CharField(max_length=200, blank=True, default="")
    status_temporal = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text="passado, futuro, indefinido",
    )
    tempo_alerta = models.CharField(max_length=200, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stg_evento"
        verbose_name = "Staging Evento"
        verbose_name_plural = "Staging Eventos"
        ordering = ["-data", "-hora_inicio"]
        indexes = [
            models.Index(fields=["municipio", "data"]),
            models.Index(fields=["status_temporal"]),
            models.Index(fields=["fluxo", "aprovado_futuro"]),
        ]

    def __str__(self):
        return f"{self.municipio} - {self.data} {self.hora_inicio} ({self.external_hash[:8]})"


class StgEventoPessoa(models.Model):
    """
    Staging de pessoas por evento (event_people.csv do DAT-P01).

    Chave primária: row_hash (SHA1 de event_external_hash|role|name).
    Relacionamento: FK para StgEvento via external_hash.
    """

    ROLE_CHOICES = [
        ("COORDENADOR", "Coordenador"),
        ("FORMADOR", "Formador"),
    ]

    row_hash = models.CharField(
        max_length=40,
        primary_key=True,
        db_index=True,
        help_text="SHA1(event_external_hash|role|name)",
    )

    event_external_hash = models.ForeignKey(
        StgEvento,
        on_delete=models.CASCADE,
        to_field="external_hash",
        db_column="event_external_hash",
        related_name="pessoas",
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    name = models.CharField(max_length=200)
    matched = models.BooleanField(default=False)
    email = models.EmailField(max_length=200, blank=True, default="")
    cargo = models.CharField(max_length=200, blank=True, default="")
    gerencia = models.CharField(max_length=200, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stg_evento_pessoa"
        verbose_name = "Staging Pessoa por Evento"
        verbose_name_plural = "Staging Pessoas por Evento"
        ordering = ["event_external_hash", "role", "name"]

    def __str__(self):
        return f"{self.name} ({self.role}) - {self.event_external_hash_id[:8]}"


class StgDispBloqueio(models.Model):
    """
    Staging de bloqueios de disponibilidade (disp_blocks.csv do DAT-P02).

    Chave primária: row_hash (SHA1 de data_inicial|data_final|tipo|responsavel).
    """

    row_hash = models.CharField(
        max_length=40,
        primary_key=True,
        db_index=True,
        help_text="SHA1(data_inicial|data_final|tipo|responsavel)",
    )

    data_inicial = models.DateField(null=True, blank=True)
    data_final = models.DateField(null=True, blank=True)
    tipo = models.CharField(max_length=100, blank=True, default="")
    responsavel = models.CharField(max_length=200, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stg_disp_bloqueio"
        verbose_name = "Staging Bloqueio Disponibilidade"
        verbose_name_plural = "Staging Bloqueios Disponibilidade"
        ordering = ["-data_inicial", "responsavel"]

    def __str__(self):
        return f"{self.responsavel} - {self.data_inicial} a {self.data_final} ({self.tipo})"


class StgDispDeslocamento(models.Model):
    """
    Staging de deslocamentos (disp_travels.csv do DAT-P02).

    Chave primária: row_hash (SHA1 de origem|data|destino|responsavel).
    """

    row_hash = models.CharField(
        max_length=40,
        primary_key=True,
        db_index=True,
        help_text="SHA1(origem|data|destino|responsavel)",
    )

    origem = models.CharField(max_length=200, blank=True, default="")
    data = models.DateField(null=True, blank=True)
    destino = models.CharField(max_length=200, blank=True, default="")
    responsavel = models.CharField(max_length=200, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stg_disp_deslocamento"
        verbose_name = "Staging Deslocamento"
        verbose_name_plural = "Staging Deslocamentos"
        ordering = ["-data", "responsavel"]

    def __str__(self):
        return f"{self.responsavel} - {self.origem} → {self.destino} ({self.data})"


class StgControleUnificado(models.Model):
    """
    Staging do controle unificado (controle_unificado.csv do DAT-P03).

    Chave primária: row_hash (SHA1 de municipio|projeto|uf|gerencia).
    Opcional: só cria se CSV fornecido.
    """

    row_hash = models.CharField(
        max_length=40,
        primary_key=True,
        db_index=True,
        help_text="SHA1(municipio|projeto|uf|gerencia)",
    )

    municipio = models.CharField(max_length=200, blank=True, default="")
    projeto = models.CharField(max_length=200, blank=True, default="")
    uf = models.CharField(max_length=2, blank=True, default="")
    gerencia = models.CharField(max_length=200, blank=True, default="")

    # Agregações de compras
    qtd_compras = models.IntegerField(default=0)
    soma_quant = models.IntegerField(default=0)

    # Datas agregadas
    primeira_data_compra = models.DateField(null=True, blank=True)
    data_entrega = models.DateField(null=True, blank=True)
    data_carta = models.DateField(null=True, blank=True)
    data_reuniao_alinhamento = models.DateField(null=True, blank=True)

    # Textos agregados
    contato_inicial = models.TextField(blank=True, default="")
    observacao_concat = models.TextField(blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stg_controle_unificado"
        verbose_name = "Staging Controle Unificado"
        verbose_name_plural = "Staging Controle Unificado"
        ordering = ["municipio", "projeto"]

    def __str__(self):
        return f"{self.municipio} - {self.projeto} ({self.uf})"
