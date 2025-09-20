# Padrões de Código Python - Sistema Aprender

## Introdução

Este documento define os padrões de código Python que devem ser seguidos no desenvolvimento do Sistema Aprender. Todos os contribuidores devem aderir a estas diretrizes para garantir consistência, manutenibilidade e qualidade do código.

## Padrões Gerais

### PEP 8 - Style Guide for Python Code

O código deve seguir rigorosamente a [PEP 8](https://peps.python.org/pep-0008/), incluindo:

#### Indentação
```python
# ✅ Correto
def funcao_exemplo():
    if condicao:
        return valor
    else:
        return outro_valor

# ❌ Incorreto
def funcao_exemplo():
  if condicao:
      return valor
  else:
      return outro_valor
```

#### Comprimento de linha
- **Máximo**: 88 caracteres (configuração Black)
- **Docstrings e comentários**: 72 caracteres

#### Nomeação
```python
# ✅ Variáveis e funções - snake_case
nome_usuario = "João"
def calcular_disponibilidade():
    pass

# ✅ Classes - PascalCase
class FormadorService:
    pass

# ✅ Constantes - SCREAMING_SNAKE_CASE
MAX_EVENTOS_POR_DIA = 8
STATUS_APROVADO = "APROVADO"

# ✅ Métodos privados - prefixo _
def _validar_dados_internos(self):
    pass
```

#### Imports
```python
# ✅ Ordem correta dos imports
# 1. Standard library
import datetime
import json
from typing import List, Optional

# 2. Third-party
import django
from django.db import models
from rest_framework import serializers

# 3. Local imports
from core.models import Formador, Solicitacao
from core.services.calendar_codes import GoogleCalendarService
```

## Type Hints

### Obrigatório em todas as funções públicas

```python
from typing import List, Dict, Optional, Union, Tuple
from datetime import datetime
from django.http import HttpResponse

# ✅ Função com type hints completos
def verificar_disponibilidade_formador(
    formador_id: int,
    data_inicio: datetime,
    data_fim: datetime,
    excluir_solicitacao: Optional[int] = None
) -> Dict[str, Union[bool, List[str]]]:
    """
    Verifica se formador está disponível no período especificado.

    Args:
        formador_id: ID do formador a verificar
        data_inicio: Data/hora de início do evento
        data_fim: Data/hora de fim do evento
        excluir_solicitacao: ID da solicitação a excluir da verificação

    Returns:
        Dicionário com 'disponivel' (bool) e 'conflitos' (list)

    Raises:
        Formador.DoesNotExist: Se formador não for encontrado
        ValueError: Se datas forem inválidas
    """
    conflitos = []

    try:
        formador = Formador.objects.get(id=formador_id)
    except Formador.DoesNotExist:
        raise Formador.DoesNotExist(f"Formador {formador_id} não encontrado")

    if data_inicio >= data_fim:
        raise ValueError("Data de início deve ser anterior à data de fim")

    # Lógica de verificação...

    return {
        'disponivel': len(conflitos) == 0,
        'conflitos': conflitos
    }

# ✅ Métodos de classe
class SolicitacaoService:
    def criar_solicitacao(
        self,
        dados: Dict[str, any],
        usuario: 'Usuario'
    ) -> Tuple[bool, 'Solicitacao']:
        pass

# ✅ Views Django
def dashboard_view(request: HttpRequest) -> HttpResponse:
    context = {'titulo': 'Dashboard'}
    return render(request, 'dashboard.html', context)
```

### Type Hints para Django Models

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet

class FormadorManager(models.Manager):
    def ativos(self) -> 'QuerySet[Formador]':
        return self.filter(ativo=True)

    def por_municipio(self, municipio_id: int) -> 'QuerySet[Formador]':
        return self.filter(usuario__municipio_id=municipio_id)

class Formador(models.Model):
    objects: FormadorManager = FormadorManager()

    def calcular_horas_mes(self, ano: int, mes: int) -> float:
        """Calcula total de horas trabalhadas no mês."""
        pass
```

## Docstrings

### Padrão Google Style

```python
def processar_importacao_planilha(
    arquivo_path: str,
    aba_nome: str,
    dry_run: bool = False
) -> Dict[str, Union[int, List[str]]]:
    """
    Processa importação de dados de planilha Google Sheets.

    Esta função lê uma planilha específica e importa os dados para o sistema,
    criando registros de formadores, projetos e solicitações conforme necessário.

    Args:
        arquivo_path: Caminho para o arquivo da planilha
        aba_nome: Nome da aba específica a processar
        dry_run: Se True, apenas simula a importação sem salvar dados

    Returns:
        Dicionário contendo:
            - 'importados': número de registros importados com sucesso
            - 'erros': lista de mensagens de erro encontradas
            - 'warnings': lista de avisos durante o processamento

    Raises:
        FileNotFoundError: Se arquivo não for encontrado
        ValueError: Se aba especificada não existir
        PermissionError: Se não houver permissão para ler arquivo

    Examples:
        >>> resultado = processar_importacao_planilha(
        ...     'dados/agenda_2025.xlsx',
        ...     'Super',
        ...     dry_run=True
        ... )
        >>> print(f"Seriam importados: {resultado['importados']} registros")
        Seriam importados: 152 registros

        >>> # Importação real
        >>> resultado = processar_importacao_planilha(
        ...     'dados/agenda_2025.xlsx',
        ...     'Super'
        ... )
        >>> if resultado['erros']:
        ...     print(f"Erros encontrados: {resultado['erros']}")

    Note:
        - A função preserva dados existentes, não sobrescreve
        - Logs detalhados são gerados durante o processamento
        - Em caso de erro crítico, rollback automático é executado
    """
    pass

class GoogleCalendarService:
    """
    Serviço para integração com Google Calendar API.

    Gerencia criação de eventos, links do Google Meet e sincronização
    bidirecional com o calendário institucional.

    Attributes:
        calendar_id: ID do calendário Google utilizado
        credentials: Credenciais OAuth2 para autenticação
        _service: Instância do serviço Google Calendar

    Example:
        >>> service = GoogleCalendarService()
        >>> evento_id = service.criar_evento(solicitacao)
        >>> meet_link = service.obter_meet_link(evento_id)
    """

    def __init__(self, calendar_id: str):
        """
        Inicializa o serviço com ID do calendário.

        Args:
            calendar_id: ID do calendário Google a ser utilizado

        Raises:
            AuthenticationError: Se credenciais OAuth2 forem inválidas
        """
        pass
```

### Docstrings para Modelos Django

```python
class Solicitacao(models.Model):
    """
    Representa uma solicitação de evento educacional.

    Uma solicitação é criada por coordenadores e passa por processo
    de verificação de conflitos e aprovação antes de se tornar um
    evento confirmado no Google Calendar.

    Attributes:
        solicitante: Usuário que criou a solicitação
        formadores: Formadores designados para o evento
        projeto: Projeto educacional associado
        tipo_evento: Classificação do tipo de evento
        municipio: Local onde o evento será realizado
        data_inicio: Data e hora de início do evento
        data_fim: Data e hora de término do evento
        status: Status atual da solicitação (PENDENTE, APROVADO, etc.)
        observacoes: Informações adicionais sobre o evento

    Meta:
        verbose_name: "Solicitação de Evento"
        verbose_name_plural: "Solicitações de Eventos"
        ordering: ['-data_criacao']
    """

    solicitante = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        help_text="Usuário responsável pela solicitação"
    )

    def tem_conflitos(self) -> bool:
        """
        Verifica se solicitação possui conflitos de agenda.

        Returns:
            True se há conflitos, False caso contrário

        Note:
            Considera bloqueios, sobreposições e buffers de deslocamento
        """
        pass

    def aprovar(self, aprovador: 'Usuario', observacoes: str = "") -> bool:
        """
        Aprova a solicitação e inicia processo de criação do evento.

        Args:
            aprovador: Usuário com permissão para aprovar
            observacoes: Justificativa da aprovação

        Returns:
            True se aprovação foi bem-sucedida

        Raises:
            PermissionError: Se usuário não tem permissão
            ConflictError: Se há conflitos não resolvidos
        """
        pass
```

## Padrões Específicos do Django

### Models

```python
class BaseModel(models.Model):
    """Modelo base com campos comuns."""

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        help_text="Data e hora de criação do registro"
    )
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        help_text="Data e hora da última atualização"
    )
    ativo = models.BooleanField(
        default=True,
        help_text="Indica se o registro está ativo no sistema"
    )

    class Meta:
        abstract = True

class Formador(BaseModel):
    """Instrutor responsável por ministrar eventos educacionais."""

    usuario = models.OneToOneField(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='formador',
        help_text="Usuário associado ao formador"
    )
    areas_atuacao = models.ManyToManyField(
        'TipoEvento',
        blank=True,
        help_text="Tipos de evento que o formador pode ministrar"
    )

    class Meta:
        verbose_name = "Formador"
        verbose_name_plural = "Formadores"
        indexes = [
            models.Index(fields=['ativo']),
            models.Index(fields=['usuario']),
        ]

    def __str__(self) -> str:
        return f"{self.usuario.get_full_name()} - {self.usuario.municipio}"

    def save(self, *args, **kwargs):
        """Override para validações customizadas."""
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validações de modelo."""
        if not self.usuario.eh_formador():
            raise ValidationError("Usuário deve ter papel de formador")
```

### Views

```python
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView
from typing import Dict, Any

# ✅ Function-based views
@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Exibe dashboard principal do sistema.

    Args:
        request: Objeto HttpRequest do Django

    Returns:
        HttpResponse renderizado com template dashboard.html
    """
    context = _construir_context_dashboard(request.user)
    return render(request, 'core/dashboard.html', context)

def _construir_context_dashboard(usuario: 'Usuario') -> Dict[str, Any]:
    """
    Constrói contexto para o dashboard baseado no perfil do usuário.

    Args:
        usuario: Usuário logado

    Returns:
        Dicionário com dados para o template
    """
    context = {
        'usuario': usuario,
        'estatisticas': {},
    }

    if usuario.eh_superintendencia():
        context['aprovacoes_pendentes'] = Solicitacao.objects.pendentes().count()
        context['conflitos_hoje'] = _calcular_conflitos_hoje()

    return context

# ✅ Class-based views
class SolicitacaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista solicitações do usuário atual."""

    model = Solicitacao
    template_name = 'core/solicitacao_list.html'
    context_object_name = 'solicitacoes'
    permission_required = 'core.view_solicitacao'
    paginate_by = 20

    def get_queryset(self) -> 'QuerySet[Solicitacao]':
        """Filtra solicitações baseado no perfil do usuário."""
        qs = super().get_queryset()

        if self.request.user.eh_coordenador():
            return qs.filter(solicitante=self.request.user)
        elif self.request.user.eh_superintendencia():
            return qs.all()

        return qs.none()

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Adiciona dados extras ao contexto."""
        context = super().get_context_data(**kwargs)
        context['total_solicitacoes'] = self.get_queryset().count()
        context['pode_criar'] = self.request.user.has_perm('core.add_solicitacao')
        return context
```

### Forms

```python
from django import forms
from django.core.exceptions import ValidationError

class SolicitacaoForm(forms.ModelForm):
    """Formulário para criação/edição de solicitações."""

    class Meta:
        model = Solicitacao
        fields = [
            'formadores', 'projeto', 'tipo_evento', 'municipio',
            'data_inicio', 'data_fim', 'observacoes'
        ]
        widgets = {
            'data_inicio': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'data_fim': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'observacoes': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
        }

    def __init__(self, usuario: 'Usuario', *args, **kwargs):
        """
        Inicializa formulário com filtros baseados no usuário.

        Args:
            usuario: Usuário que está criando a solicitação
        """
        super().__init__(*args, **kwargs)

        # Filtrar formadores do mesmo município
        self.fields['formadores'].queryset = Formador.objects.filter(
            usuario__municipio=usuario.municipio,
            ativo=True
        )

        # Adicionar classes CSS
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def clean(self) -> Dict[str, Any]:
        """Validações do formulário."""
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if data_inicio and data_fim:
            if data_inicio >= data_fim:
                raise ValidationError(
                    "Data de início deve ser anterior à data de fim"
                )

            # Verificar se não é data passada
            if data_inicio < timezone.now():
                raise ValidationError(
                    "Não é possível agendar eventos para datas passadas"
                )

        return cleaned_data

    def save(self, commit: bool = True) -> Solicitacao:
        """Salva solicitação com dados adicionais."""
        solicitacao = super().save(commit=False)

        if commit:
            solicitacao.save()
            self.save_m2m()

            # Log da criação
            LogAuditoria.objects.create(
                usuario=self.usuario,
                acao='CRIAR_SOLICITACAO',
                modelo_afetado='Solicitacao',
                objeto_id=solicitacao.id
            )

        return solicitacao
```

## Tratamento de Erros

### Exceções Customizadas

```python
class AprenderSystemError(Exception):
    """Exceção base do sistema Aprender."""
    pass

class ConflictError(AprenderSystemError):
    """Erro de conflito de agenda."""

    def __init__(self, message: str, conflitos: List[str]):
        super().__init__(message)
        self.conflitos = conflitos

class AuthenticationError(AprenderSystemError):
    """Erro de autenticação externa."""
    pass

class GoogleCalendarError(AprenderSystemError):
    """Erro na integração com Google Calendar."""

    def __init__(self, message: str, calendar_id: str = ""):
        super().__init__(message)
        self.calendar_id = calendar_id
```

### Tratamento Robusto

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def criar_evento_google_calendar(
    solicitacao: Solicitacao
) -> Optional[str]:
    """
    Cria evento no Google Calendar com tratamento robusto de erros.

    Args:
        solicitacao: Solicitação aprovada para criar evento

    Returns:
        ID do evento criado ou None se falhou

    Raises:
        GoogleCalendarError: Se erro crítico na API
    """
    try:
        service = GoogleCalendarService()
        evento_id = service.criar_evento(solicitacao)

        logger.info(
            "Evento criado no Google Calendar",
            extra={
                'solicitacao_id': solicitacao.id,
                'evento_id': evento_id,
                'formadores': [f.nome for f in solicitacao.formadores.all()]
            }
        )

        return evento_id

    except HttpError as e:
        if e.resp.status == 403:
            logger.warning(
                "Permissão negada para criar evento",
                extra={'solicitacao_id': solicitacao.id, 'error': str(e)}
            )
            # Tentar criar manualmente
            return _criar_evento_manual(solicitacao)

        logger.error(
            "Erro HTTP na API do Google Calendar",
            extra={'solicitacao_id': solicitacao.id, 'status': e.resp.status},
            exc_info=True
        )
        raise GoogleCalendarError(f"Erro API: {e}")

    except Exception as e:
        logger.error(
            "Erro inesperado ao criar evento",
            extra={'solicitacao_id': solicitacao.id},
            exc_info=True
        )
        # Não re-levantar para permitir fallback
        return None

def _criar_evento_manual(solicitacao: Solicitacao) -> str:
    """Fallback: cria evento manual quando API falha."""
    # Implementação de fallback
    pass
```

## Estrutura de Serviços

```python
# core/services/disponibilidade_service.py
from dataclasses import dataclass
from enum import Enum

class TipoConflito(Enum):
    SOBREPOSICAO = "E"
    MULTIPLOS_EVENTOS = "M"
    DESLOCAMENTO = "D"
    BLOQUEIO_PARCIAL = "P"
    BLOQUEIO_TOTAL = "T"
    CONFLITO_GERAL = "X"

@dataclass
class ConflictInfo:
    """Informações sobre um conflito de agenda."""
    tipo: TipoConflito
    descricao: str
    data_inicio: datetime
    data_fim: datetime
    formador_nome: str

class DisponibilidadeService:
    """Serviço para verificação de disponibilidade e conflitos."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def verificar_disponibilidade(
        self,
        formadores_ids: List[int],
        data_inicio: datetime,
        data_fim: datetime,
        excluir_solicitacao_id: Optional[int] = None
    ) -> Tuple[bool, List[ConflictInfo]]:
        """
        Verifica disponibilidade de múltiplos formadores.

        Args:
            formadores_ids: Lista de IDs dos formadores
            data_inicio: Data/hora de início
            data_fim: Data/hora de fim
            excluir_solicitacao_id: ID da solicitação a excluir

        Returns:
            Tupla (disponível, lista_de_conflitos)
        """
        conflitos = []

        for formador_id in formadores_ids:
            conflitos_formador = self._verificar_formador(
                formador_id, data_inicio, data_fim, excluir_solicitacao_id
            )
            conflitos.extend(conflitos_formador)

        return len(conflitos) == 0, conflitos

    def _verificar_formador(
        self,
        formador_id: int,
        data_inicio: datetime,
        data_fim: datetime,
        excluir_solicitacao_id: Optional[int]
    ) -> List[ConflictInfo]:
        """Verifica conflitos para um formador específico."""
        conflitos = []

        # RD-01: Verificar sobreposições
        conflitos.extend(self._verificar_sobreposicoes(
            formador_id, data_inicio, data_fim, excluir_solicitacao_id
        ))

        # RD-02 e RD-03: Verificar bloqueios
        conflitos.extend(self._verificar_bloqueios(
            formador_id, data_inicio, data_fim
        ))

        # RD-04: Verificar buffer de deslocamento
        conflitos.extend(self._verificar_deslocamento(
            formador_id, data_inicio, data_fim, excluir_solicitacao_id
        ))

        # RD-05: Verificar capacidade diária
        conflitos.extend(self._verificar_capacidade_diaria(
            formador_id, data_inicio, data_fim, excluir_solicitacao_id
        ))

        return conflitos
```

## Testes

### Estrutura de Testes

```python
# tests/test_disponibilidade_service.py
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from core.services.disponibilidade_service import DisponibilidadeService, TipoConflito
from core.tests.factories import FormadorFactory, SolicitacaoFactory

class DisponibilidadeServiceTest(TestCase):
    """Testes para o serviço de disponibilidade."""

    def setUp(self):
        """Configuração inicial dos testes."""
        self.service = DisponibilidadeService()
        self.formador = FormadorFactory()
        self.data_base = timezone.now().replace(
            hour=14, minute=0, second=0, microsecond=0
        )

    def test_sem_conflitos_periodo_livre(self):
        """Testa período livre sem conflitos."""
        # Arrange
        data_inicio = self.data_base
        data_fim = self.data_base + timedelta(hours=2)

        # Act
        disponivel, conflitos = self.service.verificar_disponibilidade(
            [self.formador.id], data_inicio, data_fim
        )

        # Assert
        self.assertTrue(disponivel)
        self.assertEqual(len(conflitos), 0)

    def test_conflito_sobreposicao_total(self):
        """Testa conflito por sobreposição total."""
        # Arrange
        data_inicio = self.data_base
        data_fim = self.data_base + timedelta(hours=2)

        # Criar solicitação existente
        SolicitacaoFactory(
            formadores=[self.formador],
            data_inicio=data_inicio,
            data_fim=data_fim,
            status='APROVADO'
        )

        # Act
        disponivel, conflitos = self.service.verificar_disponibilidade(
            [self.formador.id], data_inicio, data_fim
        )

        # Assert
        self.assertFalse(disponivel)
        self.assertEqual(len(conflitos), 1)
        self.assertEqual(conflitos[0].tipo, TipoConflito.SOBREPOSICAO)

    def test_sem_conflito_periodos_adjacentes(self):
        """Testa que períodos adjacentes não conflitam."""
        # Arrange
        evento_fim = self.data_base + timedelta(hours=2)
        novo_inicio = evento_fim  # Mesmo momento
        novo_fim = novo_inicio + timedelta(hours=1)

        SolicitacaoFactory(
            formadores=[self.formador],
            data_inicio=self.data_base,
            data_fim=evento_fim,
            status='APROVADO'
        )

        # Act
        disponivel, conflitos = self.service.verificar_disponibilidade(
            [self.formador.id], novo_inicio, novo_fim
        )

        # Assert
        self.assertTrue(disponivel, "Períodos adjacentes não devem conflitar")
        self.assertEqual(len(conflitos), 0)

class GoogleCalendarServiceTest(TestCase):
    """Testes para integração com Google Calendar."""

    @patch('core.services.calendar_codes.build')
    def test_criar_evento_sucesso(self, mock_build):
        """Testa criação bem-sucedida de evento."""
        # Arrange
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.events().insert().execute.return_value = {
            'id': 'evento_123',
            'hangoutLink': 'https://meet.google.com/abc-def-ghi'
        }

        solicitacao = SolicitacaoFactory(status='APROVADO')
        service = GoogleCalendarService()

        # Act
        evento_id = service.criar_evento(solicitacao)

        # Assert
        self.assertEqual(evento_id, 'evento_123')
        mock_service.events().insert.assert_called_once()
```

### Factories para Testes

```python
# tests/factories.py
import factory
from django.contrib.auth import get_user_model
from core.models import Formador, Solicitacao, Projeto, TipoEvento, Municipio

User = get_user_model()

class UsuarioFactory(factory.django.DjangoModelFactory):
    """Factory para criação de usuários em testes."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"usuario{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@exemplo.com")
    first_name = factory.Faker('first_name', locale='pt_BR')
    last_name = factory.Faker('last_name', locale='pt_BR')
    cpf = factory.Sequence(lambda n: f"{n:011d}")
    papel = 'COORDENADOR'

class FormadorFactory(factory.django.DjangoModelFactory):
    """Factory para criação de formadores em testes."""

    class Meta:
        model = Formador

    usuario = factory.SubFactory(UsuarioFactory, papel='FORMADOR')
    ativo = True

class SolicitacaoFactory(factory.django.DjangoModelFactory):
    """Factory para criação de solicitações em testes."""

    class Meta:
        model = Solicitacao

    solicitante = factory.SubFactory(UsuarioFactory)
    projeto = factory.SubFactory('tests.factories.ProjetoFactory')
    tipo_evento = factory.SubFactory('tests.factories.TipoEventoFactory')
    municipio = factory.SubFactory('tests.factories.MunicipioFactory')
    data_inicio = factory.Faker('future_datetime', end_date='+30d')
    data_fim = factory.LazyAttribute(
        lambda obj: obj.data_inicio + timedelta(hours=2)
    )
    status = 'PENDENTE'

    @factory.post_generation
    def formadores(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for formador in extracted:
                self.formadores.add(formador)
```

## Configurações e Ambientes

### Settings Structure

```python
# aprender_sistema/settings.py
import os
from pathlib import Path
from typing import List

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

# Security
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'dev-key-only-for-development-never-use-in-production'
)
DEBUG = ENVIRONMENT == 'development'

# Database configuration
DATABASES = {
    'default': _get_database_config()
}

def _get_database_config() -> dict:
    """Retorna configuração do banco baseada no ambiente."""
    if ENVIRONMENT == 'production':
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ['DB_USER'],
            'PASSWORD': os.environ['DB_PASSWORD'],
            'HOST': os.environ['DB_HOST'],
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }

    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'aprender_sistema_db'),
        'USER': os.environ.get('DB_USER', 'adm_aprender'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'aprender123456'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5433'),
    }

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/aprender.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'core': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
}
```

## Ferramentas de Qualidade de Código

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        args: [--line-length=88]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings, flake8-typing-imports]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [django-stubs]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, ., -x, tests]
```

### Makefile para Automação

```makefile
# Makefile
.PHONY: help install test lint format check clean

help:  ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Instala dependências
	pip install -r requirements.txt
	pre-commit install

test:  ## Executa todos os testes
	python manage.py test --parallel
	coverage report --show-missing

lint:  ## Verifica qualidade do código
	flake8 .
	mypy .
	bandit -r . -x tests

format:  ## Formata código automaticamente
	black .
	isort .

check: lint test  ## Verifica lint e testes

clean:  ## Remove arquivos temporários
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage
	rm -rf htmlcov/

migrate:  ## Aplica migrações
	python manage.py migrate

makemigrations:  ## Cria novas migrações
	python manage.py makemigrations

shell:  ## Abre shell Django
	python manage.py shell_plus

runserver:  ## Inicia servidor de desenvolvimento
	ENVIRONMENT=staging python manage.py runserver

docker-up:  ## Inicia containers Docker
	docker-compose up -d

docker-down:  ## Para containers Docker
	docker-compose down

docker-logs:  ## Mostra logs dos containers
	docker-compose logs -f
```

## Conclusão

Estes padrões devem ser seguidos rigorosamente por todos os desenvolvedores do Sistema Aprender. Eles garantem:

- **Consistência** no código base
- **Manutenibilidade** a longo prazo
- **Facilidade de debugging** e troubleshooting
- **Onboarding** mais rápido de novos desenvolvedores
- **Qualidade** e confiabilidade do sistema

Para dúvidas ou sugestões de melhorias nestes padrões, abra uma issue no repositório ou discuta com a equipe técnica.