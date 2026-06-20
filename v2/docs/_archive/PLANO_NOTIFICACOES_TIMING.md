# Plano de Implementação: Sistema de Notificações de Timing

**Data**: 2025-12-19
**Versão**: 1.0
**Status**: Aprovado para Implementação
**Estimativa**: 8 PRs (estrutura modular)

---

## Sumário Executivo

Este plano detalha a implementação de um sistema de notificações para alertar formadores, coordenadores e gerentes sobre o cumprimento de prazos ideais para aplicação de formações. O sistema utiliza notificação em cascata hierárquica e se integra com a infraestrutura existente (Celery, Redis, Django).

### Princípios de Design

- **SSOT (Single Source of Truth)**: Toda configuração de prazos no modelo `EtapaProjeto`
- **Separação de Responsabilidades**: Models, Services, Tasks, Views isolados
- **Idempotência**: Tasks podem ser re-executadas sem efeitos colaterais
- **Observabilidade**: Logs estruturados para debugging e métricas
- **Conformidade**: Segue CP-01 a CP-06 e padrões do projeto

---

## Fase 1: Modelagem de Dados

### PR #1: Models Core de Notificações

**Branch**: `feat/notificacoes-models-core`

**Objetivo**: Criar os modelos fundamentais para o sistema de notificações.

#### 1.1 Criar arquivo `apps/core/models/notificacao.py`

```python
"""
Models para o sistema de notificações de timing.

Este módulo implementa:
- EtapaProjeto: Configuração de prazos ideais por projeto
- CicloFormacao: Rastreamento de ciclo projeto+município
- EtapaRealizada: Histórico de etapas concluídas
- Notification: Notificações geradas pelo sistema
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models import QuerySet


class EtapaProjeto(models.Model):
    """
    Define as etapas e prazos ideais para cada projeto/coleção.

    Exemplo de uso:
        TEMA tem 4 encontros:
        - Etapa 0 (Contato): dia 0
        - Etapa 1 (1º Encontro): até dia 15
        - Etapa 2 (2º Encontro): até dia 45
        - Etapa 3 (3º Encontro): até dia 75
        - Etapa 4 (4º Encontro): até dia 90
    """

    projeto = models.ForeignKey(
        "core.Projeto",
        on_delete=models.CASCADE,
        related_name="etapas_timing",
        help_text="Projeto ao qual esta etapa pertence",
    )
    ordem = models.PositiveIntegerField(
        help_text="Ordem da etapa (0=Contato, 1=1ºEncontro, etc.)",
    )
    nome = models.CharField(
        max_length=100,
        help_text="Nome descritivo da etapa (ex: '1º Encontro')",
    )

    # Timing - Dias a partir do Contato (Dia 0)
    dias_limite_apos_contato = models.PositiveIntegerField(
        help_text="Prazo máximo em dias após o Contato com Município",
    )
    dias_alerta_antes = models.PositiveIntegerField(
        default=7,
        help_text="Dias antes do prazo para iniciar alertas",
    )

    # Escalação em cascata
    dias_escalar_coordenador = models.PositiveIntegerField(
        default=3,
        help_text="Dias de atraso para escalar ao coordenador",
    )
    dias_escalar_gerente = models.PositiveIntegerField(
        default=5,
        help_text="Dias de atraso para escalar ao gerente",
    )

    # Metadados
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_etapa_projeto"
        ordering = ["projeto", "ordem"]
        unique_together = ["projeto", "ordem"]
        verbose_name = "Etapa de Projeto"
        verbose_name_plural = "Etapas de Projeto"

    def __str__(self) -> str:
        return f"{self.projeto.nome} - {self.nome} (até dia {self.dias_limite_apos_contato})"

    def calcular_data_limite(self, data_contato: date) -> date:
        """Calcula a data limite baseada na data do contato."""
        return data_contato + timedelta(days=self.dias_limite_apos_contato)

    def calcular_data_alerta(self, data_contato: date) -> date:
        """Calcula a data para iniciar alertas."""
        data_limite = self.calcular_data_limite(data_contato)
        return data_limite - timedelta(days=self.dias_alerta_antes)


class CicloFormacao(models.Model):
    """
    Rastreia um ciclo completo de formação de um projeto em um município.

    Um ciclo inicia com o Contato com Município (Dia 0) e termina quando
    todas as etapas são concluídas ou o ciclo é cancelado.
    """

    STATUS_CHOICES = [
        ("EM_ANDAMENTO", "Em andamento"),
        ("CONCLUIDO", "Concluído no prazo"),
        ("CONCLUIDO_ATRASO", "Concluído com atraso"),
        ("CANCELADO", "Cancelado"),
    ]

    projeto = models.ForeignKey(
        "core.Projeto",
        on_delete=models.CASCADE,
        related_name="ciclos_formacao",
    )
    municipio = models.ForeignKey(
        "core.Municipio",
        on_delete=models.CASCADE,
        related_name="ciclos_formacao",
    )
    ano = models.PositiveIntegerField(
        help_text="Ano do ciclo (permite múltiplos ciclos por ano)",
    )

    # Responsáveis
    formador_principal = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ciclos_como_formador",
    )
    coordenador = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ciclos_como_coordenador",
    )

    # PONTO ZERO - Base para todos os cálculos
    data_contato_municipio = models.DateField(
        help_text="Dia 0 - Data do primeiro contato com o município",
    )

    # Status atual
    etapa_atual = models.ForeignKey(
        EtapaProjeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="EM_ANDAMENTO",
    )

    # Datas de conclusão
    data_conclusao = models.DateField(null=True, blank=True)
    duracao_total_dias = models.PositiveIntegerField(null=True, blank=True)

    # Métricas calculadas
    dias_atraso_acumulado = models.IntegerField(
        default=0,
        help_text="Soma dos dias de atraso de todas as etapas",
    )
    percentual_conclusao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentual de etapas concluídas",
    )

    # Vínculo com DATAcao (se existir)
    dat_acao = models.ForeignKey(
        "core.DATAcao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ciclo_formacao",
        help_text="Ação DAT que originou este ciclo",
    )

    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_ciclo_formacao"
        unique_together = ["projeto", "municipio", "ano"]
        ordering = ["-ano", "projeto__nome", "municipio__nome"]
        verbose_name = "Ciclo de Formação"
        verbose_name_plural = "Ciclos de Formação"

    def __str__(self) -> str:
        return f"{self.projeto.nome} | {self.municipio.nome} ({self.ano})"

    @property
    def dias_desde_contato(self) -> int:
        """Retorna dias desde o contato até hoje."""
        return (date.today() - self.data_contato_municipio).days

    @property
    def esta_atrasado(self) -> bool:
        """Verifica se o ciclo está atrasado baseado na etapa atual."""
        if not self.etapa_atual:
            return False
        data_limite = self.etapa_atual.calcular_data_limite(self.data_contato_municipio)
        return date.today() > data_limite

    def atualizar_metricas(self) -> None:
        """Atualiza métricas calculadas do ciclo."""
        etapas_realizadas = self.etapas_realizadas.all()
        total_etapas = self.projeto.etapas_timing.filter(ativo=True).count()

        if total_etapas > 0:
            concluidas = etapas_realizadas.filter(status="REALIZADA").count()
            self.percentual_conclusao = Decimal(concluidas / total_etapas * 100)

        self.dias_atraso_acumulado = sum(
            max(0, er.dias_atraso) for er in etapas_realizadas
        )
        self.save(update_fields=["percentual_conclusao", "dias_atraso_acumulado", "updated_at"])


class EtapaRealizada(models.Model):
    """
    Registro histórico de cada etapa realizada em um ciclo.

    Permite comparar prazo ideal vs realizado e calcular métricas.
    """

    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("AGENDADA", "Agendada"),
        ("REALIZADA", "Realizada"),
        ("ATRASADA", "Atrasada (não realizada)"),
    ]

    ciclo = models.ForeignKey(
        CicloFormacao,
        on_delete=models.CASCADE,
        related_name="etapas_realizadas",
    )
    etapa = models.ForeignKey(
        EtapaProjeto,
        on_delete=models.CASCADE,
        related_name="realizacoes",
    )

    # Vínculo com Solicitacao (se existir)
    solicitacao = models.ForeignKey(
        "core.Solicitacao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="etapa_realizada",
    )

    # Datas
    data_prevista = models.DateField(
        help_text="Data limite calculada (contato + dias_limite)",
    )
    data_realizada = models.DateField(
        null=True,
        blank=True,
        help_text="Data em que a etapa foi efetivamente realizada",
    )

    # Métricas
    dias_desde_contato = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Dias entre o contato e a realização",
    )
    dias_atraso = models.IntegerField(
        default=0,
        help_text="Positivo=atraso, Negativo=antecipado, Zero=no prazo",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDENTE",
    )

    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_etapa_realizada"
        unique_together = ["ciclo", "etapa"]
        ordering = ["ciclo", "etapa__ordem"]
        verbose_name = "Etapa Realizada"
        verbose_name_plural = "Etapas Realizadas"

    def __str__(self) -> str:
        status = "✓" if self.status == "REALIZADA" else "○"
        return f"{status} {self.etapa.nome} ({self.ciclo})"

    def calcular_metricas(self) -> None:
        """Calcula métricas de atraso quando a etapa é realizada."""
        if self.data_realizada:
            self.dias_desde_contato = (
                self.data_realizada - self.ciclo.data_contato_municipio
            ).days
            self.dias_atraso = (self.data_realizada - self.data_prevista).days
            self.status = "REALIZADA"
        self.save(update_fields=["dias_desde_contato", "dias_atraso", "status", "updated_at"])


class Notification(models.Model):
    """
    Notificações geradas pelo sistema para alertar sobre prazos.

    Implementa notificação em cascata:
    1. FORMADOR: Alerta inicial
    2. COORDENADOR: Escalação após N dias
    3. GERENTE: Escalação final após M dias
    """

    TIPO_CHOICES = [
        ("ETAPA_PROXIMA", "Próxima etapa se aproximando"),
        ("ETAPA_ATRASADA", "Etapa atrasada"),
        ("ESCALACAO_COORDENADOR", "Escalado para coordenador"),
        ("ESCALACAO_GERENTE", "Escalado para gerente"),
        ("CICLO_CONCLUIDO", "Ciclo de formações concluído"),
        ("LEMBRETE_DOCUMENTACAO", "Lembrete de documentação pendente"),
    ]

    NIVEL_CHOICES = [
        ("FORMADOR", "Formador"),
        ("COORDENADOR", "Coordenador"),
        ("GERENTE", "Gerente"),
    ]

    PRIORIDADE_CHOICES = [
        ("BAIXA", "Baixa"),
        ("MEDIA", "Média"),
        ("ALTA", "Alta"),
        ("URGENTE", "Urgente"),
    ]

    # Destinatário
    usuario = models.ForeignKey(
        "core.Usuario",
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )

    # Tipo e nível
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    nivel_cascata = models.CharField(max_length=20, choices=NIVEL_CHOICES)
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default="MEDIA",
    )

    # Conteúdo
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()

    # Referências (para navegação)
    ciclo = models.ForeignKey(
        CicloFormacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes",
    )
    etapa = models.ForeignKey(
        EtapaProjeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes",
    )

    # Status de leitura
    lida = models.BooleanField(default=False)
    lida_em = models.DateTimeField(null=True, blank=True)

    # Ação tomada
    acao_tomada = models.BooleanField(
        default=False,
        help_text="Se o usuário criou solicitação em resposta",
    )
    acao_tomada_em = models.DateTimeField(null=True, blank=True)

    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "lida"]),
            models.Index(fields=["usuario", "created_at"]),
            models.Index(fields=["ciclo", "etapa", "nivel_cascata"]),
        ]
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"

    def __str__(self) -> str:
        status = "●" if not self.lida else "○"
        return f"{status} {self.titulo}"

    def marcar_como_lida(self) -> None:
        """Marca a notificação como lida."""
        if not self.lida:
            self.lida = True
            self.lida_em = timezone.now()
            self.save(update_fields=["lida", "lida_em"])

    def marcar_acao_tomada(self) -> None:
        """Marca que uma ação foi tomada em resposta à notificação."""
        if not self.acao_tomada:
            self.acao_tomada = True
            self.acao_tomada_em = timezone.now()
            self.save(update_fields=["acao_tomada", "acao_tomada_em"])

    @classmethod
    def nao_lidas_do_usuario(cls, usuario_id: int) -> QuerySet[Notification]:
        """Retorna notificações não lidas de um usuário."""
        return cls.objects.filter(usuario_id=usuario_id, lida=False)

    @classmethod
    def contar_nao_lidas(cls, usuario_id: int) -> int:
        """Conta notificações não lidas de um usuário."""
        return cls.nao_lidas_do_usuario(usuario_id).count()
```

#### 1.2 Atualizar `apps/core/models/__init__.py`

Adicionar exports dos novos modelos.

#### 1.3 Criar migrations

```bash
docker compose exec web python manage.py makemigrations core --name notificacoes_models
```

#### 1.4 Testes unitários

**Arquivo**: `apps/core/tests/test_notificacao_models.py`

```python
"""
Testes para os modelos de notificação.

Cobertura:
- EtapaProjeto: cálculo de datas
- CicloFormacao: métricas e status
- EtapaRealizada: cálculo de atraso
- Notification: CRUD e queries
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from apps.core.models import (
    EtapaProjeto,
    CicloFormacao,
    EtapaRealizada,
    Notification,
    Projeto,
    Municipio,
    Usuario,
)


@pytest.fixture
def projeto(db):
    return Projeto.objects.create(nome="TEMA", codigo="TEMA", fluxo="NAO_SUPER")


@pytest.fixture
def municipio(db):
    return Municipio.objects.create(nome="Fortaleza", uf="CE")


@pytest.fixture
def usuario(db):
    return Usuario.objects.create_user(username="formador1", password="test123")


@pytest.fixture
def etapa_projeto(db, projeto):
    return EtapaProjeto.objects.create(
        projeto=projeto,
        ordem=1,
        nome="1º Encontro",
        dias_limite_apos_contato=15,
        dias_alerta_antes=7,
    )


class TestEtapaProjeto:
    def test_calcular_data_limite(self, etapa_projeto):
        data_contato = date(2025, 1, 1)
        data_limite = etapa_projeto.calcular_data_limite(data_contato)
        assert data_limite == date(2025, 1, 16)

    def test_calcular_data_alerta(self, etapa_projeto):
        data_contato = date(2025, 1, 1)
        data_alerta = etapa_projeto.calcular_data_alerta(data_contato)
        # 15 dias limite - 7 dias antes = dia 8
        assert data_alerta == date(2025, 1, 9)


class TestCicloFormacao:
    def test_dias_desde_contato(self, projeto, municipio):
        ciclo = CicloFormacao.objects.create(
            projeto=projeto,
            municipio=municipio,
            ano=2025,
            data_contato_municipio=date.today() - timedelta(days=10),
        )
        assert ciclo.dias_desde_contato == 10

    def test_esta_atrasado_sem_etapa(self, projeto, municipio):
        ciclo = CicloFormacao.objects.create(
            projeto=projeto,
            municipio=municipio,
            ano=2025,
            data_contato_municipio=date.today(),
        )
        assert ciclo.esta_atrasado is False


class TestNotification:
    def test_marcar_como_lida(self, usuario):
        notif = Notification.objects.create(
            usuario=usuario,
            tipo="ETAPA_PROXIMA",
            nivel_cascata="FORMADOR",
            titulo="Teste",
            mensagem="Mensagem de teste",
        )
        assert notif.lida is False

        notif.marcar_como_lida()

        notif.refresh_from_db()
        assert notif.lida is True
        assert notif.lida_em is not None

    def test_contar_nao_lidas(self, usuario):
        # Criar 3 notificações, 1 lida
        for i in range(3):
            Notification.objects.create(
                usuario=usuario,
                tipo="ETAPA_PROXIMA",
                nivel_cascata="FORMADOR",
                titulo=f"Teste {i}",
                mensagem="Mensagem",
                lida=(i == 0),
            )

        assert Notification.contar_nao_lidas(usuario.id) == 2
```

#### 1.5 Checklist PR #1

- [ ] Models criados com type hints (PEP 695)
- [ ] Docstrings em todos os models e métodos
- [ ] Migration gerada e testada
- [ ] 10+ testes unitários passando
- [ ] Pyright sem erros
- [ ] `python manage.py check` sem warnings

---

## Fase 2: Services Layer

### PR #2: Services de Timing e Notificação

**Branch**: `feat/notificacoes-services`

**Objetivo**: Implementar a lógica de negócio para cálculo de prazos e geração de notificações.

#### 2.1 Criar `apps/core/services/timing_service.py`

```python
"""
Service para cálculo e verificação de prazos de timing.

Responsabilidades:
- Calcular status de prazo para etapas
- Determinar próxima etapa pendente
- Verificar se ciclo está em alerta ou atrasado
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from django.db.models import QuerySet

if TYPE_CHECKING:
    from apps.core.models import CicloFormacao, EtapaProjeto, EtapaRealizada


class StatusTiming(Enum):
    """Status possíveis para o timing de uma etapa."""

    OK = "ok"  # Dentro do prazo, sem alerta
    ALERTA = "alerta"  # Próximo do prazo (dentro da janela de alerta)
    ATRASADO = "atrasado"  # Passou do prazo
    REALIZADO = "realizado"  # Etapa já realizada


@dataclass
class TimingResult:
    """Resultado da verificação de timing de uma etapa."""

    status: StatusTiming
    etapa_nome: str
    data_prevista: date
    data_realizada: date | None
    dias_para_prazo: int  # Positivo = falta, Negativo = passou
    dias_atraso: int  # Só relevante se atrasado


@dataclass
class CicloTimingResult:
    """Resultado da verificação de timing de um ciclo completo."""

    ciclo_id: int
    projeto_nome: str
    municipio_nome: str
    status_geral: StatusTiming
    proxima_etapa: TimingResult | None
    etapas_atrasadas: list[TimingResult]
    percentual_conclusao: float


def verificar_timing_etapa(
    ciclo: CicloFormacao,
    etapa: EtapaProjeto,
    etapa_realizada: EtapaRealizada | None = None,
) -> TimingResult:
    """
    Verifica o status de timing de uma etapa específica.

    Args:
        ciclo: Ciclo de formação
        etapa: Configuração da etapa
        etapa_realizada: Registro de realização (se existir)

    Returns:
        TimingResult com status e métricas
    """
    data_prevista = etapa.calcular_data_limite(ciclo.data_contato_municipio)
    data_alerta = etapa.calcular_data_alerta(ciclo.data_contato_municipio)
    hoje = date.today()

    # Se já foi realizada
    if etapa_realizada and etapa_realizada.status == "REALIZADA":
        return TimingResult(
            status=StatusTiming.REALIZADO,
            etapa_nome=etapa.nome,
            data_prevista=data_prevista,
            data_realizada=etapa_realizada.data_realizada,
            dias_para_prazo=0,
            dias_atraso=etapa_realizada.dias_atraso,
        )

    dias_para_prazo = (data_prevista - hoje).days

    # Determinar status
    if dias_para_prazo < 0:
        status = StatusTiming.ATRASADO
    elif hoje >= data_alerta:
        status = StatusTiming.ALERTA
    else:
        status = StatusTiming.OK

    return TimingResult(
        status=status,
        etapa_nome=etapa.nome,
        data_prevista=data_prevista,
        data_realizada=None,
        dias_para_prazo=dias_para_prazo,
        dias_atraso=abs(dias_para_prazo) if dias_para_prazo < 0 else 0,
    )


def verificar_timing_ciclo(ciclo: CicloFormacao) -> CicloTimingResult:
    """
    Verifica o status de timing de todas as etapas de um ciclo.

    Args:
        ciclo: Ciclo de formação a verificar

    Returns:
        CicloTimingResult com status geral e detalhes
    """
    from apps.core.models import EtapaProjeto, EtapaRealizada

    etapas = EtapaProjeto.objects.filter(
        projeto=ciclo.projeto,
        ativo=True,
    ).order_by("ordem")

    etapas_realizadas = {
        er.etapa_id: er
        for er in EtapaRealizada.objects.filter(ciclo=ciclo)
    }

    resultados: list[TimingResult] = []
    etapas_atrasadas: list[TimingResult] = []
    proxima_etapa: TimingResult | None = None

    for etapa in etapas:
        er = etapas_realizadas.get(etapa.id)
        resultado = verificar_timing_etapa(ciclo, etapa, er)
        resultados.append(resultado)

        if resultado.status == StatusTiming.ATRASADO:
            etapas_atrasadas.append(resultado)

        # Próxima etapa é a primeira não realizada
        if proxima_etapa is None and resultado.status != StatusTiming.REALIZADO:
            proxima_etapa = resultado

    # Status geral do ciclo
    if etapas_atrasadas:
        status_geral = StatusTiming.ATRASADO
    elif proxima_etapa and proxima_etapa.status == StatusTiming.ALERTA:
        status_geral = StatusTiming.ALERTA
    elif all(r.status == StatusTiming.REALIZADO for r in resultados):
        status_geral = StatusTiming.REALIZADO
    else:
        status_geral = StatusTiming.OK

    return CicloTimingResult(
        ciclo_id=ciclo.id,
        projeto_nome=ciclo.projeto.nome,
        municipio_nome=ciclo.municipio.nome,
        status_geral=status_geral,
        proxima_etapa=proxima_etapa,
        etapas_atrasadas=etapas_atrasadas,
        percentual_conclusao=float(ciclo.percentual_conclusao),
    )


def obter_ciclos_para_verificacao() -> QuerySet[CicloFormacao]:
    """
    Retorna ciclos que precisam ser verificados.

    Critérios:
    - Status EM_ANDAMENTO
    - Tem etapas configuradas
    """
    from apps.core.models import CicloFormacao

    return CicloFormacao.objects.filter(
        status="EM_ANDAMENTO",
        projeto__etapas_timing__ativo=True,
    ).select_related(
        "projeto",
        "municipio",
        "formador_principal",
        "coordenador",
    ).distinct()
```

#### 2.2 Criar `apps/core/services/notification_service.py`

```python
"""
Service para criação e gestão de notificações.

Responsabilidades:
- Criar notificações baseadas em timing
- Implementar lógica de cascata
- Evitar duplicatas
- Identificar destinatários
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from apps.core.models import (
        CicloFormacao,
        EtapaProjeto,
        Notification,
        Usuario,
    )

from apps.core.services.timing_service import (
    StatusTiming,
    TimingResult,
    CicloTimingResult,
)

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuração para criação de notificação."""

    tipo: str
    nivel: str
    prioridade: str
    titulo: str
    mensagem: str


def determinar_nivel_cascata(
    etapa: EtapaProjeto,
    dias_atraso: int,
) -> str | None:
    """
    Determina o nível de cascata baseado no atraso.

    Args:
        etapa: Configuração da etapa
        dias_atraso: Dias de atraso (0 = no prazo, >0 = atrasado)

    Returns:
        Nível ('FORMADOR', 'COORDENADOR', 'GERENTE') ou None se não notificar
    """
    if dias_atraso < 0:
        # Ainda não chegou no prazo, mas está na janela de alerta
        return "FORMADOR"
    elif dias_atraso == 0:
        # No dia do prazo
        return "FORMADOR"
    elif dias_atraso <= etapa.dias_escalar_coordenador:
        # Atrasado, mas ainda na janela do formador
        return "FORMADOR"
    elif dias_atraso <= etapa.dias_escalar_gerente:
        # Passou janela do formador, escalar
        return "COORDENADOR"
    else:
        # Passou todas as janelas
        return "GERENTE"


def determinar_prioridade(status: StatusTiming, dias_atraso: int) -> str:
    """Determina a prioridade da notificação."""
    if status == StatusTiming.ATRASADO:
        if dias_atraso > 7:
            return "URGENTE"
        elif dias_atraso > 3:
            return "ALTA"
        else:
            return "MEDIA"
    elif status == StatusTiming.ALERTA:
        return "MEDIA"
    else:
        return "BAIXA"


def criar_config_notificacao(
    timing_result: TimingResult,
    nivel: str,
    ciclo: CicloFormacao,
) -> NotificationConfig:
    """
    Cria a configuração de uma notificação baseada no timing.

    Args:
        timing_result: Resultado da verificação de timing
        nivel: Nível de cascata
        ciclo: Ciclo de formação

    Returns:
        NotificationConfig com todos os dados
    """
    projeto = ciclo.projeto.nome
    municipio = ciclo.municipio.nome

    if timing_result.status == StatusTiming.ALERTA:
        tipo = "ETAPA_PROXIMA"
        titulo = f"Prazo se aproximando: {timing_result.etapa_nome}"
        mensagem = (
            f"O prazo para '{timing_result.etapa_nome}' do projeto {projeto} "
            f"em {municipio} vence em {timing_result.dias_para_prazo} dias "
            f"({timing_result.data_prevista.strftime('%d/%m/%Y')})."
        )
    else:  # ATRASADO
        if nivel == "FORMADOR":
            tipo = "ETAPA_ATRASADA"
        elif nivel == "COORDENADOR":
            tipo = "ESCALACAO_COORDENADOR"
        else:
            tipo = "ESCALACAO_GERENTE"

        titulo = f"Etapa atrasada: {timing_result.etapa_nome}"
        mensagem = (
            f"A etapa '{timing_result.etapa_nome}' do projeto {projeto} "
            f"em {municipio} está atrasada há {timing_result.dias_atraso} dias. "
            f"Prazo era {timing_result.data_prevista.strftime('%d/%m/%Y')}."
        )

    prioridade = determinar_prioridade(timing_result.status, timing_result.dias_atraso)

    return NotificationConfig(
        tipo=tipo,
        nivel=nivel,
        prioridade=prioridade,
        titulo=titulo,
        mensagem=mensagem,
    )


def obter_destinatario(
    ciclo: CicloFormacao,
    nivel: str,
) -> Usuario | None:
    """
    Obtém o destinatário da notificação baseado no nível.

    Args:
        ciclo: Ciclo de formação
        nivel: Nível de cascata

    Returns:
        Usuario ou None se não encontrar
    """
    if nivel == "FORMADOR":
        return ciclo.formador_principal
    elif nivel == "COORDENADOR":
        return ciclo.coordenador
    elif nivel == "GERENTE":
        # Buscar gerente da gerência do projeto
        gerencia = ciclo.projeto.gerencia
        if gerencia:
            return gerencia.gerente
    return None


def notificacao_ja_existe(
    ciclo: CicloFormacao,
    etapa: EtapaProjeto,
    nivel: str,
    data: date,
) -> bool:
    """
    Verifica se já existe notificação para evitar duplicatas.

    Regra: 1 notificação por ciclo/etapa/nível/dia
    """
    from apps.core.models import Notification

    return Notification.objects.filter(
        ciclo=ciclo,
        etapa=etapa,
        nivel_cascata=nivel,
        created_at__date=data,
    ).exists()


def ja_existe_solicitacao_pendente(
    ciclo: CicloFormacao,
    etapa: EtapaProjeto,
) -> bool:
    """
    Verifica se já existe solicitação pendente/aprovada para a etapa.

    Se existir, não precisa notificar (ação já foi tomada).
    """
    from apps.core.models import Solicitacao

    return Solicitacao.objects.filter(
        projeto=ciclo.projeto,
        municipio=ciclo.municipio,
        encontro=str(etapa.ordem),
        status__in=["pendente", "aprovado"],
    ).exists()


@transaction.atomic
def criar_notificacao_timing(
    ciclo: CicloFormacao,
    timing_result: TimingResult,
    etapa: EtapaProjeto,
) -> Notification | None:
    """
    Cria notificação de timing se necessário.

    Verifica:
    - Se já existe solicitação (ação tomada)
    - Se já existe notificação hoje (evitar duplicata)
    - Se tem destinatário válido

    Args:
        ciclo: Ciclo de formação
        timing_result: Resultado do timing
        etapa: Etapa do projeto

    Returns:
        Notification criada ou None se não criou
    """
    from apps.core.models import Notification

    # Só notificar se ALERTA ou ATRASADO
    if timing_result.status not in (StatusTiming.ALERTA, StatusTiming.ATRASADO):
        return None

    # Verificar se já tem solicitação
    if ja_existe_solicitacao_pendente(ciclo, etapa):
        logger.debug(
            f"Solicitação já existe para {ciclo} etapa {etapa.nome}, "
            "não criando notificação"
        )
        return None

    # Determinar nível de cascata
    nivel = determinar_nivel_cascata(etapa, timing_result.dias_atraso)
    if not nivel:
        return None

    # Verificar duplicata
    hoje = date.today()
    if notificacao_ja_existe(ciclo, etapa, nivel, hoje):
        logger.debug(
            f"Notificação já existe hoje para {ciclo} etapa {etapa.nome} "
            f"nível {nivel}"
        )
        return None

    # Obter destinatário
    destinatario = obter_destinatario(ciclo, nivel)
    if not destinatario:
        logger.warning(
            f"Nenhum destinatário encontrado para {ciclo} nível {nivel}"
        )
        return None

    # Criar configuração e notificação
    config = criar_config_notificacao(timing_result, nivel, ciclo)

    notif = Notification.objects.create(
        usuario=destinatario,
        tipo=config.tipo,
        nivel_cascata=config.nivel,
        prioridade=config.prioridade,
        titulo=config.titulo,
        mensagem=config.mensagem,
        ciclo=ciclo,
        etapa=etapa,
    )

    logger.info(
        f"Notificação criada: {notif.titulo} para {destinatario.username} "
        f"(nível {nivel})"
    )

    return notif


def processar_ciclo_para_notificacoes(
    ciclo_timing: CicloTimingResult,
    ciclo: CicloFormacao,
) -> list[Notification]:
    """
    Processa um ciclo e cria todas as notificações necessárias.

    Args:
        ciclo_timing: Resultado da verificação de timing
        ciclo: Ciclo de formação

    Returns:
        Lista de notificações criadas
    """
    from apps.core.models import EtapaProjeto

    notificacoes_criadas: list[Notification] = []

    # Processar próxima etapa se em alerta
    if ciclo_timing.proxima_etapa and ciclo_timing.proxima_etapa.status == StatusTiming.ALERTA:
        etapa = EtapaProjeto.objects.get(
            projeto=ciclo.projeto,
            nome=ciclo_timing.proxima_etapa.etapa_nome,
        )
        notif = criar_notificacao_timing(ciclo, ciclo_timing.proxima_etapa, etapa)
        if notif:
            notificacoes_criadas.append(notif)

    # Processar etapas atrasadas
    for etapa_atrasada in ciclo_timing.etapas_atrasadas:
        etapa = EtapaProjeto.objects.get(
            projeto=ciclo.projeto,
            nome=etapa_atrasada.etapa_nome,
        )
        notif = criar_notificacao_timing(ciclo, etapa_atrasada, etapa)
        if notif:
            notificacoes_criadas.append(notif)

    return notificacoes_criadas
```

#### 2.3 Testes para services

**Arquivo**: `apps/core/tests/test_notification_services.py`

```python
"""
Testes para os services de timing e notificação.

Cobertura:
- timing_service: cálculo de status
- notification_service: criação e cascata
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch

from apps.core.models import (
    EtapaProjeto,
    CicloFormacao,
    Notification,
    Projeto,
    Municipio,
    Usuario,
)
from apps.core.services.timing_service import (
    StatusTiming,
    verificar_timing_etapa,
    verificar_timing_ciclo,
)
from apps.core.services.notification_service import (
    determinar_nivel_cascata,
    criar_notificacao_timing,
)


@pytest.fixture
def setup_completo(db):
    """Setup completo para testes."""
    projeto = Projeto.objects.create(nome="TEMA", codigo="TEMA", fluxo="NAO_SUPER")
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
    formador = Usuario.objects.create_user(username="formador", password="test")
    coordenador = Usuario.objects.create_user(username="coordenador", password="test")

    etapa = EtapaProjeto.objects.create(
        projeto=projeto,
        ordem=1,
        nome="1º Encontro",
        dias_limite_apos_contato=15,
        dias_alerta_antes=7,
        dias_escalar_coordenador=3,
        dias_escalar_gerente=5,
    )

    ciclo = CicloFormacao.objects.create(
        projeto=projeto,
        municipio=municipio,
        ano=2025,
        data_contato_municipio=date.today() - timedelta(days=10),
        formador_principal=formador,
        coordenador=coordenador,
    )

    return {
        "projeto": projeto,
        "municipio": municipio,
        "formador": formador,
        "coordenador": coordenador,
        "etapa": etapa,
        "ciclo": ciclo,
    }


class TestTimingService:
    def test_status_ok_longe_do_prazo(self, setup_completo):
        """Testa que status é OK quando longe do prazo."""
        ciclo = setup_completo["ciclo"]
        etapa = setup_completo["etapa"]

        # Contato há 5 dias, prazo em 15 = faltam 10 dias (fora da janela de 7)
        ciclo.data_contato_municipio = date.today() - timedelta(days=5)
        ciclo.save()

        resultado = verificar_timing_etapa(ciclo, etapa)

        assert resultado.status == StatusTiming.OK
        assert resultado.dias_para_prazo == 10

    def test_status_alerta_dentro_da_janela(self, setup_completo):
        """Testa que status é ALERTA dentro da janela."""
        ciclo = setup_completo["ciclo"]
        etapa = setup_completo["etapa"]

        # Contato há 10 dias, prazo em 15 = faltam 5 dias (dentro da janela de 7)
        ciclo.data_contato_municipio = date.today() - timedelta(days=10)
        ciclo.save()

        resultado = verificar_timing_etapa(ciclo, etapa)

        assert resultado.status == StatusTiming.ALERTA
        assert resultado.dias_para_prazo == 5

    def test_status_atrasado(self, setup_completo):
        """Testa que status é ATRASADO quando passou o prazo."""
        ciclo = setup_completo["ciclo"]
        etapa = setup_completo["etapa"]

        # Contato há 20 dias, prazo em 15 = atrasado 5 dias
        ciclo.data_contato_municipio = date.today() - timedelta(days=20)
        ciclo.save()

        resultado = verificar_timing_etapa(ciclo, etapa)

        assert resultado.status == StatusTiming.ATRASADO
        assert resultado.dias_atraso == 5


class TestNotificationService:
    def test_nivel_formador_no_alerta(self, setup_completo):
        """Formador é notificado primeiro no alerta."""
        etapa = setup_completo["etapa"]

        nivel = determinar_nivel_cascata(etapa, dias_atraso=-3)

        assert nivel == "FORMADOR"

    def test_nivel_coordenador_apos_3_dias(self, setup_completo):
        """Coordenador é notificado após 3 dias de atraso."""
        etapa = setup_completo["etapa"]

        nivel = determinar_nivel_cascata(etapa, dias_atraso=4)

        assert nivel == "COORDENADOR"

    def test_nivel_gerente_apos_5_dias(self, setup_completo):
        """Gerente é notificado após 5 dias de atraso."""
        etapa = setup_completo["etapa"]

        nivel = determinar_nivel_cascata(etapa, dias_atraso=6)

        assert nivel == "GERENTE"

    def test_cria_notificacao_para_formador(self, setup_completo):
        """Testa criação de notificação para formador."""
        ciclo = setup_completo["ciclo"]
        etapa = setup_completo["etapa"]

        # Configurar para alerta
        ciclo.data_contato_municipio = date.today() - timedelta(days=10)
        ciclo.save()

        resultado = verificar_timing_etapa(ciclo, etapa)
        notif = criar_notificacao_timing(ciclo, resultado, etapa)

        assert notif is not None
        assert notif.usuario == setup_completo["formador"]
        assert notif.nivel_cascata == "FORMADOR"
        assert notif.tipo == "ETAPA_PROXIMA"

    def test_nao_duplica_notificacao_mesmo_dia(self, setup_completo):
        """Testa que não cria notificação duplicada no mesmo dia."""
        ciclo = setup_completo["ciclo"]
        etapa = setup_completo["etapa"]

        ciclo.data_contato_municipio = date.today() - timedelta(days=10)
        ciclo.save()

        resultado = verificar_timing_etapa(ciclo, etapa)

        # Primeira notificação
        notif1 = criar_notificacao_timing(ciclo, resultado, etapa)
        assert notif1 is not None

        # Segunda tentativa no mesmo dia
        notif2 = criar_notificacao_timing(ciclo, resultado, etapa)
        assert notif2 is None
```

#### 2.4 Checklist PR #2

- [ ] Services com type hints completos
- [ ] Docstrings detalhadas
- [ ] Logging estruturado
- [ ] 15+ testes passando
- [ ] Cobertura > 90% nos services
- [ ] Pyright sem erros

---

## Fase 3: Celery Tasks

### PR #3: Tasks de Verificação de Prazos

**Branch**: `feat/notificacoes-tasks`

**Objetivo**: Implementar tasks Celery para verificação periódica de prazos.

#### 3.1 Atualizar `apps/core/tasks.py`

```python
# Adicionar ao arquivo existente

from celery import shared_task
import logging
from datetime import date

from apps.core.services.timing_service import (
    obter_ciclos_para_verificacao,
    verificar_timing_ciclo,
)
from apps.core.services.notification_service import (
    processar_ciclo_para_notificacoes,
)

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.core.tasks.task_verificar_prazos_diario",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def task_verificar_prazos_diario(self):
    """
    Task executada diariamente para verificar prazos e criar notificações.

    Execução: Celery Beat às 8h (America/Fortaleza)

    Fluxo:
    1. Obtém todos os ciclos em andamento
    2. Para cada ciclo, verifica timing de todas as etapas
    3. Cria notificações para etapas em alerta ou atrasadas
    4. Aplica lógica de cascata (Formador → Coordenador → Gerente)
    """
    logger.info("Iniciando verificação diária de prazos de timing")

    ciclos = obter_ciclos_para_verificacao()
    total_ciclos = ciclos.count()

    logger.info(f"Verificando {total_ciclos} ciclos em andamento")

    stats = {
        "ciclos_verificados": 0,
        "ciclos_em_alerta": 0,
        "ciclos_atrasados": 0,
        "notificacoes_criadas": 0,
        "erros": 0,
    }

    for ciclo in ciclos:
        try:
            # Verificar timing do ciclo
            timing_result = verificar_timing_ciclo(ciclo)

            stats["ciclos_verificados"] += 1

            if timing_result.etapas_atrasadas:
                stats["ciclos_atrasados"] += 1
            elif timing_result.proxima_etapa and timing_result.proxima_etapa.status.value == "alerta":
                stats["ciclos_em_alerta"] += 1

            # Criar notificações
            notificacoes = processar_ciclo_para_notificacoes(timing_result, ciclo)
            stats["notificacoes_criadas"] += len(notificacoes)

        except Exception as e:
            stats["erros"] += 1
            logger.error(
                f"Erro ao verificar ciclo {ciclo.id}: {e}",
                extra={"ciclo_id": ciclo.id},
                exc_info=True,
            )

    logger.info(
        "Verificação diária concluída",
        extra={
            "stats": stats,
            "data": date.today().isoformat(),
        },
    )

    return stats


@shared_task(
    name="apps.core.tasks.task_atualizar_metricas_ciclos",
    bind=True,
)
def task_atualizar_metricas_ciclos(self):
    """
    Task para atualizar métricas calculadas dos ciclos.

    Execução: Após task_verificar_prazos_diario ou sob demanda
    """
    from apps.core.models import CicloFormacao

    logger.info("Atualizando métricas de ciclos")

    ciclos = CicloFormacao.objects.filter(status="EM_ANDAMENTO")
    atualizados = 0

    for ciclo in ciclos:
        try:
            ciclo.atualizar_metricas()
            atualizados += 1
        except Exception as e:
            logger.error(f"Erro ao atualizar métricas do ciclo {ciclo.id}: {e}")

    logger.info(f"Métricas atualizadas para {atualizados} ciclos")

    return {"ciclos_atualizados": atualizados}
```

#### 3.2 Atualizar `config/settings.py` - Celery Beat

```python
# Adicionar ao CELERY_BEAT_SCHEDULE existente

CELERY_BEAT_SCHEDULE = {
    # ... schedules existentes ...

    "verificar-prazos-timing-8h": {
        "task": "apps.core.tasks.task_verificar_prazos_diario",
        "schedule": crontab(hour=8, minute=0),  # 8h America/Fortaleza
        "options": {"queue": "default"},
    },
    "atualizar-metricas-ciclos-8h30": {
        "task": "apps.core.tasks.task_atualizar_metricas_ciclos",
        "schedule": crontab(hour=8, minute=30),
        "options": {"queue": "default"},
    },
}
```

#### 3.3 Testes para tasks

**Arquivo**: `apps/core/tests/test_notification_tasks.py`

```python
"""
Testes para as tasks de notificação.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from apps.core.tasks import (
    task_verificar_prazos_diario,
    task_atualizar_metricas_ciclos,
)
from apps.core.models import (
    CicloFormacao,
    EtapaProjeto,
    Notification,
    Projeto,
    Municipio,
    Usuario,
)


@pytest.fixture
def setup_ciclo_em_alerta(db):
    """Setup de ciclo em estado de alerta."""
    projeto = Projeto.objects.create(nome="TEMA", codigo="TEMA", fluxo="NAO_SUPER")
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
    formador = Usuario.objects.create_user(username="formador", password="test")

    EtapaProjeto.objects.create(
        projeto=projeto,
        ordem=1,
        nome="1º Encontro",
        dias_limite_apos_contato=15,
        dias_alerta_antes=7,
    )

    ciclo = CicloFormacao.objects.create(
        projeto=projeto,
        municipio=municipio,
        ano=2025,
        data_contato_municipio=date.today() - timedelta(days=10),  # 5 dias para prazo
        formador_principal=formador,
        status="EM_ANDAMENTO",
    )

    return ciclo


class TestTaskVerificarPrazos:
    def test_cria_notificacao_para_ciclo_em_alerta(self, setup_ciclo_em_alerta):
        """Testa que task cria notificação para ciclo em alerta."""
        # Executar task
        result = task_verificar_prazos_diario()

        assert result["ciclos_verificados"] == 1
        assert result["notificacoes_criadas"] == 1

        # Verificar notificação criada
        notif = Notification.objects.first()
        assert notif is not None
        assert notif.tipo == "ETAPA_PROXIMA"

    def test_nao_duplica_em_execucoes_seguidas(self, setup_ciclo_em_alerta):
        """Testa idempotência da task."""
        # Primeira execução
        result1 = task_verificar_prazos_diario()
        assert result1["notificacoes_criadas"] == 1

        # Segunda execução no mesmo dia
        result2 = task_verificar_prazos_diario()
        assert result2["notificacoes_criadas"] == 0

        # Apenas 1 notificação no banco
        assert Notification.objects.count() == 1


class TestTaskAtualizarMetricas:
    def test_atualiza_metricas_ciclos(self, setup_ciclo_em_alerta):
        """Testa atualização de métricas."""
        result = task_atualizar_metricas_ciclos()

        assert result["ciclos_atualizados"] == 1
```

#### 3.4 Checklist PR #3

- [ ] Tasks com retry e error handling
- [ ] Logging estruturado com métricas
- [ ] Idempotência garantida
- [ ] Celery Beat configurado
- [ ] 8+ testes passando
- [ ] Documentação de execução

---

## Fase 4: API Endpoints

### PR #4: APIs de Notificações

**Branch**: `feat/notificacoes-api`

**Objetivo**: Criar endpoints REST para gestão de notificações.

#### 4.1 Criar `apps/core/serializers/notification.py`

```python
"""
Serializers para o módulo de notificações.
"""

from rest_framework import serializers

from apps.core.models import (
    Notification,
    CicloFormacao,
    EtapaProjeto,
    EtapaRealizada,
)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para Notification."""

    projeto_nome = serializers.CharField(
        source="ciclo.projeto.nome",
        read_only=True,
        allow_null=True,
    )
    municipio_nome = serializers.CharField(
        source="ciclo.municipio.nome",
        read_only=True,
        allow_null=True,
    )
    etapa_nome = serializers.CharField(
        source="etapa.nome",
        read_only=True,
        allow_null=True,
    )
    tempo_relativo = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "tipo",
            "nivel_cascata",
            "prioridade",
            "titulo",
            "mensagem",
            "projeto_nome",
            "municipio_nome",
            "etapa_nome",
            "lida",
            "lida_em",
            "acao_tomada",
            "created_at",
            "tempo_relativo",
        ]
        read_only_fields = fields

    def get_tempo_relativo(self, obj) -> str:
        """Retorna tempo relativo humanizado."""
        from django.utils import timezone
        from django.utils.timesince import timesince

        return timesince(obj.created_at, timezone.now())


class NotificationUnreadCountSerializer(serializers.Serializer):
    """Serializer para contagem de não lidas."""

    count = serializers.IntegerField()


class CicloFormacaoListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem de ciclos."""

    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    formador_nome = serializers.CharField(
        source="formador_principal.get_full_name",
        read_only=True,
        allow_null=True,
    )
    coordenador_nome = serializers.CharField(
        source="coordenador.get_full_name",
        read_only=True,
        allow_null=True,
    )
    dias_desde_contato = serializers.IntegerField(read_only=True)
    esta_atrasado = serializers.BooleanField(read_only=True)

    class Meta:
        model = CicloFormacao
        fields = [
            "id",
            "projeto_nome",
            "municipio_nome",
            "ano",
            "formador_nome",
            "coordenador_nome",
            "data_contato_municipio",
            "status",
            "percentual_conclusao",
            "dias_atraso_acumulado",
            "dias_desde_contato",
            "esta_atrasado",
        ]


class EtapaRealizadaSerializer(serializers.ModelSerializer):
    """Serializer para etapas realizadas."""

    etapa_nome = serializers.CharField(source="etapa.nome", read_only=True)
    etapa_ordem = serializers.IntegerField(source="etapa.ordem", read_only=True)

    class Meta:
        model = EtapaRealizada
        fields = [
            "id",
            "etapa_nome",
            "etapa_ordem",
            "data_prevista",
            "data_realizada",
            "dias_desde_contato",
            "dias_atraso",
            "status",
        ]


class CicloFormacaoDetailSerializer(CicloFormacaoListSerializer):
    """Serializer detalhado para ciclos."""

    etapas_realizadas = EtapaRealizadaSerializer(many=True, read_only=True)

    class Meta(CicloFormacaoListSerializer.Meta):
        fields = CicloFormacaoListSerializer.Meta.fields + [
            "etapas_realizadas",
            "data_conclusao",
            "duracao_total_dias",
            "created_at",
            "updated_at",
        ]
```

#### 4.2 Criar `apps/core/views/notifications.py`

```python
"""
Views para o módulo de notificações.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.core.models import Notification, CicloFormacao
from apps.core.serializers.notification import (
    NotificationSerializer,
    NotificationUnreadCountSerializer,
    CicloFormacaoListSerializer,
    CicloFormacaoDetailSerializer,
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para gerenciamento de notificações do usuário.

    Endpoints:
    - GET /api/notifications/ - Lista notificações
    - GET /api/notifications/{id}/ - Detalhe
    - GET /api/notifications/unread-count/ - Contador
    - POST /api/notifications/{id}/mark-read/ - Marcar como lida
    - POST /api/notifications/mark-all-read/ - Marcar todas
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retorna apenas notificações do usuário logado."""
        return Notification.objects.filter(
            usuario=self.request.user
        ).select_related(
            "ciclo__projeto",
            "ciclo__municipio",
            "etapa",
        ).order_by("-created_at")

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Retorna contagem de notificações não lidas."""
        count = Notification.contar_nao_lidas(request.user.id)
        serializer = NotificationUnreadCountSerializer({"count": count})
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Marca notificação como lida."""
        notification = self.get_object()
        notification.marcar_como_lida()
        return Response({"status": "ok"})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Marca todas as notificações como lidas."""
        updated = Notification.objects.filter(
            usuario=request.user,
            lida=False,
        ).update(lida=True, lida_em=timezone.now())
        return Response({"updated": updated})


class CicloFormacaoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualização de ciclos de formação.

    Endpoints:
    - GET /api/ciclos/ - Lista ciclos
    - GET /api/ciclos/{id}/ - Detalhe com etapas
    - GET /api/ciclos/dashboard/ - Métricas agregadas
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CicloFormacaoDetailSerializer
        return CicloFormacaoListSerializer

    def get_queryset(self):
        """Filtra ciclos por permissão do usuário."""
        user = self.request.user
        qs = CicloFormacao.objects.select_related(
            "projeto",
            "municipio",
            "formador_principal",
            "coordenador",
        )

        # Superuser vê todos
        if user.is_superuser:
            return qs

        # Filtra por ciclos onde é formador ou coordenador
        return qs.filter(
            models.Q(formador_principal=user) |
            models.Q(coordenador=user)
        )

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Retorna métricas agregadas dos ciclos."""
        from django.db.models import Count, Avg, Q

        qs = self.get_queryset()

        stats = qs.aggregate(
            total=Count("id"),
            em_andamento=Count("id", filter=Q(status="EM_ANDAMENTO")),
            concluidos=Count("id", filter=Q(status__startswith="CONCLUIDO")),
            atrasados=Count("id", filter=Q(dias_atraso_acumulado__gt=0)),
            atraso_medio=Avg("dias_atraso_acumulado"),
        )

        # Por projeto
        por_projeto = qs.values("projeto__nome").annotate(
            total=Count("id"),
            atrasados=Count("id", filter=Q(dias_atraso_acumulado__gt=0)),
        ).order_by("-total")[:10]

        return Response({
            "stats": stats,
            "por_projeto": list(por_projeto),
        })
```

#### 4.3 Atualizar `apps/core/urls.py`

```python
# Adicionar aos routers existentes

from apps.core.views.notifications import NotificationViewSet, CicloFormacaoViewSet

router.register("notifications", NotificationViewSet, basename="notification")
router.register("ciclos", CicloFormacaoViewSet, basename="ciclo")
```

#### 4.4 Checklist PR #4

- [ ] Serializers com validação
- [ ] ViewSets com permissões
- [ ] Documentação de endpoints
- [ ] Testes de API (15+)
- [ ] Throttling configurado
- [ ] OpenAPI spec atualizada

---

## Fase 5: Frontend - Componentes Base

### PR #5: Componentes de Notificação

**Branch**: `feat/notificacoes-frontend-base`

**Objetivo**: Criar componentes React para exibição de notificações.

#### 5.1 Criar `src/api/notifications.js`

```javascript
/**
 * API de Notificações
 */

import api from './client';

export const getNotifications = async (params = {}) => {
  const response = await api.get('/api/notifications/', { params });
  return response.data;
};

export const getUnreadCount = async () => {
  const response = await api.get('/api/notifications/unread-count/');
  return response.data;
};

export const markAsRead = async (id) => {
  const response = await api.post(`/api/notifications/${id}/mark-read/`);
  return response.data;
};

export const markAllAsRead = async () => {
  const response = await api.post('/api/notifications/mark-all-read/');
  return response.data;
};

export const getCiclos = async (params = {}) => {
  const response = await api.get('/api/ciclos/', { params });
  return response.data;
};

export const getCicloDetail = async (id) => {
  const response = await api.get(`/api/ciclos/${id}/`);
  return response.data;
};

export const getCiclosDashboard = async () => {
  const response = await api.get('/api/ciclos/dashboard/');
  return response.data;
};
```

#### 5.2 Criar `src/components/NotificationBell.jsx`

```jsx
/**
 * NotificationBell - Ícone de notificações no header
 *
 * Exibe badge com contagem de não lidas e abre drawer ao clicar.
 */

import { useState, useEffect, useCallback } from 'react';
import { Badge, Button, Tooltip } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import { getUnreadCount } from '../api/notifications';
import NotificationDrawer from './NotificationDrawer';

const POLL_INTERVAL = 60000; // 1 minuto

export default function NotificationBell() {
  const [count, setCount] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const fetchCount = useCallback(async () => {
    try {
      const data = await getUnreadCount();
      setCount(data.count);
    } catch (error) {
      console.error('Erro ao buscar contagem:', error);
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchCount]);

  const handleDrawerClose = () => {
    setDrawerOpen(false);
    fetchCount(); // Atualiza contagem ao fechar
  };

  return (
    <>
      <Tooltip title="Notificações">
        <Badge count={count} size="small" offset={[-2, 2]}>
          <Button
            type="text"
            icon={<BellOutlined style={{ fontSize: 18 }} />}
            onClick={() => setDrawerOpen(true)}
          />
        </Badge>
      </Tooltip>

      <NotificationDrawer
        open={drawerOpen}
        onClose={handleDrawerClose}
        onRefresh={fetchCount}
      />
    </>
  );
}
```

#### 5.3 Criar `src/components/NotificationDrawer.jsx`

```jsx
/**
 * NotificationDrawer - Drawer lateral com lista de notificações
 */

import { useState, useEffect } from 'react';
import {
  Drawer,
  List,
  Typography,
  Button,
  Space,
  Empty,
  Spin,
  Tag,
  Divider,
} from 'antd';
import {
  CheckOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { getNotifications, markAsRead, markAllAsRead } from '../api/notifications';
import NotificationItem from './NotificationItem';

const { Title, Text } = Typography;

export default function NotificationDrawer({ open, onClose, onRefresh }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const data = await getNotifications({ page_size: 50 });
      setNotifications(data.results || data || []);
    } catch (error) {
      console.error('Erro ao buscar notificações:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchNotifications();
    }
  }, [open]);

  const handleMarkRead = async (id) => {
    await markAsRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, lida: true } : n))
    );
    onRefresh?.();
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, lida: true })));
    onRefresh?.();
  };

  const unreadCount = notifications.filter((n) => !n.lida).length;

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Title level={5} style={{ margin: 0 }}>Notificações</Title>
            {unreadCount > 0 && (
              <Tag color="red">{unreadCount} não lidas</Tag>
            )}
          </Space>
          {unreadCount > 0 && (
            <Button type="link" size="small" onClick={handleMarkAllRead}>
              Marcar todas como lidas
            </Button>
          )}
        </div>
      }
      placement="right"
      width={420}
      open={open}
      onClose={onClose}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="Carregando..." />
        </div>
      ) : notifications.length === 0 ? (
        <Empty
          description="Nenhuma notificação"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          dataSource={notifications}
          renderItem={(item) => (
            <NotificationItem
              key={item.id}
              notification={item}
              onMarkRead={handleMarkRead}
            />
          )}
        />
      )}
    </Drawer>
  );
}
```

#### 5.4 Criar `src/components/NotificationItem.jsx`

```jsx
/**
 * NotificationItem - Item individual de notificação
 */

import { Card, Typography, Space, Tag, Button, Tooltip } from 'antd';
import {
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text, Paragraph } = Typography;

// Configuração visual por tipo/nível
const CONFIG = {
  nivel: {
    FORMADOR: { color: 'blue', icon: <ClockCircleOutlined /> },
    COORDENADOR: { color: 'orange', icon: <WarningOutlined /> },
    GERENTE: { color: 'red', icon: <ExclamationCircleOutlined /> },
  },
  prioridade: {
    BAIXA: { color: 'default' },
    MEDIA: { color: 'blue' },
    ALTA: { color: 'orange' },
    URGENTE: { color: 'red' },
  },
};

export default function NotificationItem({ notification, onMarkRead }) {
  const navigate = useNavigate();
  const nivelConfig = CONFIG.nivel[notification.nivel_cascata] || {};
  const prioridadeConfig = CONFIG.prioridade[notification.prioridade] || {};

  const handleClick = () => {
    if (!notification.lida) {
      onMarkRead(notification.id);
    }
  };

  const handleAction = () => {
    // Navegar para criar solicitação com contexto
    if (notification.ciclo) {
      navigate(`/solicitacoes/nova?ciclo=${notification.ciclo}`);
    }
  };

  return (
    <Card
      size="small"
      style={{
        marginBottom: 8,
        borderLeft: `3px solid ${notification.lida ? '#d9d9d9' : nivelConfig.color || '#1890ff'}`,
        opacity: notification.lida ? 0.7 : 1,
        cursor: 'pointer',
      }}
      onClick={handleClick}
    >
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Space size={4}>
            {nivelConfig.icon}
            <Text strong style={{ fontSize: 13 }}>
              {notification.titulo}
            </Text>
          </Space>
          <Tag color={prioridadeConfig.color} style={{ fontSize: 10 }}>
            {notification.prioridade}
          </Tag>
        </div>

        {/* Contexto */}
        {(notification.projeto_nome || notification.municipio_nome) && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {notification.projeto_nome} • {notification.municipio_nome}
          </Text>
        )}

        {/* Mensagem */}
        <Paragraph
          ellipsis={{ rows: 2 }}
          style={{ margin: 0, fontSize: 12, color: '#666' }}
        >
          {notification.mensagem}
        </Paragraph>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text type="secondary" style={{ fontSize: 10 }}>
            {notification.tempo_relativo}
          </Text>

          {!notification.acao_tomada && (
            <Tooltip title="Criar solicitação">
              <Button
                type="link"
                size="small"
                icon={<RightOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleAction();
                }}
              >
                Agendar
              </Button>
            </Tooltip>
          )}

          {notification.acao_tomada && (
            <Tag icon={<CheckCircleOutlined />} color="success" style={{ fontSize: 10 }}>
              Ação tomada
            </Tag>
          )}
        </div>
      </Space>
    </Card>
  );
}
```

#### 5.5 Atualizar `src/App.jsx`

Adicionar `NotificationBell` no header.

```jsx
// No header, após o toggle de tema
import NotificationBell from './components/NotificationBell';

// ...

<div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
  <NotificationBell />
  {/* Toggle de tema */}
  {/* Info do usuário */}
  {/* Botão sair */}
</div>
```

#### 5.6 Checklist PR #5

- [ ] Componentes com PropTypes ou TypeScript
- [ ] Estados de loading, empty, error
- [ ] Polling configurável
- [ ] Navegação contextual
- [ ] Visual consistente com Ant Design
- [ ] Responsividade mobile

---

## Fase 6: Integração com Páginas Existentes

### PR #6: Integração com DATAcao e Solicitações

**Branch**: `feat/notificacoes-integracao`

**Objetivo**: Criar ciclos automaticamente e vincular com fluxos existentes.

#### 6.1 Criar signal para DATAcao

**Arquivo**: `apps/core/signals/notificacao_signals.py`

```python
"""
Signals para integração do sistema de notificações.

Responsabilidades:
- Criar CicloFormacao quando DATAcao tem data_contato preenchida
- Atualizar EtapaRealizada quando Solicitacao é aprovada
- Marcar notificações como "ação tomada" quando solicitação é criada
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.core.models import (
    DATAcao,
    Solicitacao,
    CicloFormacao,
    EtapaRealizada,
    EtapaProjeto,
    Notification,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DATAcao)
def criar_ciclo_formacao_de_acao(sender, instance, created, **kwargs):
    """
    Cria CicloFormacao quando DATAcao tem data_contato preenchida.

    Trigger: DATAcao.save() com data_contato não nulo
    """
    if not instance.data_contato:
        return

    # Verificar se já existe ciclo
    ciclo_existente = CicloFormacao.objects.filter(
        projeto=instance.projeto,
        municipio=instance.municipio,
        ano=instance.data_contato.year,
    ).first()

    if ciclo_existente:
        # Atualizar vínculo se não existir
        if not ciclo_existente.dat_acao:
            ciclo_existente.dat_acao = instance
            ciclo_existente.save(update_fields=["dat_acao"])
        return

    # Criar novo ciclo
    ciclo = CicloFormacao.objects.create(
        projeto=instance.projeto,
        municipio=instance.municipio,
        ano=instance.data_contato.year,
        data_contato_municipio=instance.data_contato,
        coordenador=instance.coordenador,
        dat_acao=instance,
        status="EM_ANDAMENTO",
    )

    # Criar EtapasRealizadas para todas as etapas do projeto
    etapas = EtapaProjeto.objects.filter(projeto=instance.projeto, ativo=True)
    for etapa in etapas:
        EtapaRealizada.objects.create(
            ciclo=ciclo,
            etapa=etapa,
            data_prevista=etapa.calcular_data_limite(instance.data_contato),
            status="PENDENTE",
        )

    logger.info(
        f"CicloFormacao criado: {ciclo}",
        extra={"ciclo_id": ciclo.id, "acao_id": instance.id},
    )


@receiver(post_save, sender=Solicitacao)
def atualizar_etapa_realizada_de_solicitacao(sender, instance, **kwargs):
    """
    Atualiza EtapaRealizada quando Solicitacao é aprovada.

    Trigger: Solicitacao.save() com status='aprovado'
    """
    if instance.status != "aprovado":
        return

    if not instance.encontro:
        return

    # Buscar ciclo correspondente
    ciclo = CicloFormacao.objects.filter(
        projeto=instance.projeto,
        municipio=instance.municipio,
        status="EM_ANDAMENTO",
    ).first()

    if not ciclo:
        logger.debug(
            f"Nenhum ciclo encontrado para solicitação {instance.id}"
        )
        return

    # Buscar etapa correspondente ao encontro
    try:
        ordem = int(float(instance.encontro))
    except (ValueError, TypeError):
        return

    etapa_realizada = EtapaRealizada.objects.filter(
        ciclo=ciclo,
        etapa__ordem=ordem,
    ).first()

    if not etapa_realizada:
        return

    # Atualizar etapa
    if etapa_realizada.status != "REALIZADA":
        etapa_realizada.solicitacao = instance
        etapa_realizada.data_realizada = instance.inicio.date()
        etapa_realizada.calcular_metricas()

        logger.info(
            f"EtapaRealizada atualizada: {etapa_realizada}",
            extra={
                "etapa_id": etapa_realizada.id,
                "solicitacao_id": instance.id,
            },
        )

    # Marcar notificações como "ação tomada"
    Notification.objects.filter(
        ciclo=ciclo,
        etapa=etapa_realizada.etapa,
        acao_tomada=False,
    ).update(acao_tomada=True)

    # Atualizar métricas do ciclo
    ciclo.atualizar_metricas()

    # Verificar se ciclo foi concluído
    _verificar_conclusao_ciclo(ciclo)


def _verificar_conclusao_ciclo(ciclo: CicloFormacao):
    """Verifica se todas as etapas foram realizadas."""
    etapas_pendentes = ciclo.etapas_realizadas.exclude(status="REALIZADA").count()

    if etapas_pendentes == 0:
        # Todas etapas concluídas
        from datetime import date

        ciclo.status = (
            "CONCLUIDO" if ciclo.dias_atraso_acumulado == 0
            else "CONCLUIDO_ATRASO"
        )
        ciclo.data_conclusao = date.today()
        ciclo.duracao_total_dias = ciclo.dias_desde_contato
        ciclo.save()

        logger.info(f"Ciclo concluído: {ciclo}")
```

#### 6.2 Registrar signals

**Arquivo**: `apps/core/apps.py`

```python
def ready(self):
    # Importar signals
    import apps.core.signals.notificacao_signals  # noqa
```

#### 6.3 Checklist PR #6

- [ ] Signals com logging
- [ ] Testes de integração (10+)
- [ ] Transações atômicas
- [ ] Documentação de fluxo
- [ ] Compatibilidade com dados existentes

---

## Fase 7: Admin e Configuração

### PR #7: Interface Admin para Configuração

**Branch**: `feat/notificacoes-admin`

**Objetivo**: Criar interface para configurar etapas e prazos por projeto.

#### 7.1 Criar página de configuração de etapas

**Arquivo**: `src/pages/AdminDAT/EtapasProjetoPage.jsx`

Interface para:
- Listar projetos com suas etapas
- Adicionar/editar/remover etapas
- Definir prazos ideais
- Definir tempos de escalação

#### 7.2 Criar admin Django

**Arquivo**: `apps/core/admin.py`

```python
# Adicionar

from apps.core.models import (
    EtapaProjeto,
    CicloFormacao,
    EtapaRealizada,
    Notification,
)

@admin.register(EtapaProjeto)
class EtapaProjetoAdmin(admin.ModelAdmin):
    list_display = ["projeto", "ordem", "nome", "dias_limite_apos_contato", "ativo"]
    list_filter = ["projeto", "ativo"]
    ordering = ["projeto", "ordem"]

@admin.register(CicloFormacao)
class CicloFormacaoAdmin(admin.ModelAdmin):
    list_display = ["projeto", "municipio", "ano", "status", "percentual_conclusao"]
    list_filter = ["status", "ano", "projeto"]
    search_fields = ["municipio__nome", "projeto__nome"]
    readonly_fields = ["percentual_conclusao", "dias_atraso_acumulado"]

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["titulo", "usuario", "tipo", "nivel_cascata", "lida", "created_at"]
    list_filter = ["tipo", "nivel_cascata", "lida"]
    search_fields = ["titulo", "usuario__username"]
    readonly_fields = ["created_at"]
```

#### 7.3 Checklist PR #7

- [ ] Página de configuração funcional
- [ ] Admin Django configurado
- [ ] Validações de formulário
- [ ] Documentação de uso

---

## Fase 8: Testes E2E e Documentação

### PR #8: Testes E2E e Documentação Final

**Branch**: `feat/notificacoes-docs-e2e`

**Objetivo**: Garantir qualidade com testes E2E e documentar completamente.

#### 8.1 Testes E2E com Playwright

**Arquivo**: `v2/frontend/e2e/notifications.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Sistema de Notificações', () => {
  test.beforeEach(async ({ page }) => {
    // Login como formador
    await page.goto('/');
    await page.fill('[data-testid="username"]', 'formador');
    await page.fill('[data-testid="password"]', 'test123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('/home');
  });

  test('exibe badge com contagem de notificações', async ({ page }) => {
    const badge = page.locator('[data-testid="notification-badge"]');
    await expect(badge).toBeVisible();
  });

  test('abre drawer ao clicar no sino', async ({ page }) => {
    await page.click('[data-testid="notification-bell"]');
    const drawer = page.locator('[data-testid="notification-drawer"]');
    await expect(drawer).toBeVisible();
  });

  test('marca notificação como lida ao clicar', async ({ page }) => {
    await page.click('[data-testid="notification-bell"]');
    const item = page.locator('[data-testid="notification-item"]').first();
    await item.click();
    await expect(item).toHaveAttribute('data-read', 'true');
  });

  test('navega para criar solicitação ao clicar em ação', async ({ page }) => {
    await page.click('[data-testid="notification-bell"]');
    await page.click('[data-testid="notification-action-button"]');
    await expect(page).toHaveURL(/\/solicitacoes\/nova/);
  });
});
```

#### 8.2 Documentação

Criar/atualizar:
- `v2/docs/NOTIFICACOES.md` - Guia completo do sistema
- `v2/docs/api/NOTIFICATIONS_API.md` - Documentação da API
- `.claude/CLAUDE.md` - Atualizar com novas regras

#### 8.3 Checklist PR #8

- [ ] 10+ testes E2E passando
- [ ] Documentação completa
- [ ] README atualizado
- [ ] CLAUDE.md atualizado
- [ ] Screenshots/GIFs de demonstração

---

## Cronograma de PRs

| PR | Branch | Dependência | Escopo |
|----|--------|-------------|--------|
| #1 | `feat/notificacoes-models-core` | - | Models |
| #2 | `feat/notificacoes-services` | PR #1 | Services |
| #3 | `feat/notificacoes-tasks` | PR #2 | Celery Tasks |
| #4 | `feat/notificacoes-api` | PR #1, #2 | API REST |
| #5 | `feat/notificacoes-frontend-base` | PR #4 | Componentes React |
| #6 | `feat/notificacoes-integracao` | PR #1, #2, #3 | Signals e integração |
| #7 | `feat/notificacoes-admin` | PR #1, #4 | Admin e config |
| #8 | `feat/notificacoes-docs-e2e` | Todos | Testes E2E e docs |

---

## Métricas de Sucesso

| Métrica | Target |
|---------|--------|
| Cobertura de testes (backend) | > 90% |
| Cobertura de testes (frontend) | > 80% |
| Testes E2E passando | 100% |
| Pyright erros | 0 |
| ESLint warnings | 0 |
| Documentação | Completa |
| Performance (API) | < 200ms p95 |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Dados de prazos não fornecidos | Média | Alto | Criar com valores default, UI para configuração |
| Hierarquia não preenchida | Alta | Médio | Fallback para coordenador do ciclo |
| Performance com muitos ciclos | Baixa | Médio | Índices, paginação, cache |
| Duplicação de notificações | Média | Baixo | Controle de idempotência por dia |

---

## Dependências Externas

| Item | Status | Responsável |
|------|--------|-------------|
| Dados de prazos por projeto | ⏳ Aguardando | Usuário |
| Hierarquia de equipes | ⏳ Aguardando | Usuário |
| Aprovação do plano | ⏳ Aguardando | Usuário |

---

**Autor**: Claude Code
**Revisão**: -
**Aprovação**: Pendente
