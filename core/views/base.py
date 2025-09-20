"""
IMPORTS CENTRALIZADOS - Single Source of Truth
Todas as views devem importar apenas deste arquivo
ELIMINA imports duplicados e inconsistências
"""

# ===============================
# IMPORTS PADRÃO PYTHON
# ===============================
import json
import os
from datetime import time, timedelta, datetime
from typing import Dict, List, Optional, Any, Union

# ===============================
# IMPORTS DJANGO CORE
# ===============================
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Count, Q, Prefetch, F, Max, Min, Sum, Avg
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (
    CreateView,
    FormView,
    ListView,
    TemplateView,
    DetailView,
    UpdateView,
    DeleteView
)

# ===============================
# IMPORTS DA APLICAÇÃO - MODELS
# ===============================
from core.models import (
    # Estrutura Organizacional
    Setor,
    Usuario,

    # Cadastros de Referência (FONTE ÚNICA)
    Municipio,
    Projeto,
    TipoEvento,

    # Fluxo Operacional
    Solicitacao,
    SolicitacaoStatus,
    FormadoresSolicitacao,

    # Aprovações e Controle
    Aprovacao,
    AprovacaoStatus,
    EventoGoogleCalendar,

    # Disponibilidades e Logs
    DisponibilidadeFormadores,
    LogAuditoria,
    Deslocamento,

    # COMPATIBILIDADE TEMPORÁRIA
    Formador,  # SERÁ REMOVIDO após migração completa
)

# ===============================
# IMPORTS DA APLICAÇÃO - FORMS
# ===============================
from core.forms import (
    AprovacaoDecisionForm,
    BloqueioAgendaForm,
    SolicitacaoForm,
    FormadorForm,
    MunicipioForm,
    ProjetoForm,
    TipoEventoForm,
)

# ===============================
# IMPORTS DA APLICAÇÃO - SERVICES
# ===============================
from core.services import (
    UsuarioService,
    FormadorService,
    CoordinatorService,
    DashboardService,
    MunicipioService,
)

# ===============================
# CONFIGURAÇÕES E CONSTANTES
# ===============================
User = get_user_model()  # Alias para Usuario

# Cache timeouts padronizados
CACHE_TIMEOUT_SHORT = 300      # 5 minutos
CACHE_TIMEOUT_MEDIUM = 1800    # 30 minutos
CACHE_TIMEOUT_LONG = 3600      # 1 hora

# Query optimizations padrão
USUARIO_SELECT_RELATED = ['setor', 'municipio', 'area_atuacao']
SOLICITACAO_SELECT_RELATED = ['projeto', 'municipio', 'tipo_evento', 'usuario_solicitante', 'usuario_aprovador']
SOLICITACAO_PREFETCH_RELATED = ['formadores']

# ===============================
# MIXINS E CLASSES BASE
# ===============================

class OptimizedQueryMixin:
    """
    Mixin para otimização automática de queries
    Aplica select_related/prefetch_related padrão
    """

    select_related_fields = None
    prefetch_related_fields = None

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)

        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)

        return queryset


class CachedViewMixin:
    """
    Mixin para cache automático de views
    """

    cache_timeout = CACHE_TIMEOUT_MEDIUM
    cache_key_prefix = None

    def get_cache_key(self, *args, **kwargs):
        """Gera chave de cache única"""
        prefix = self.cache_key_prefix or self.__class__.__name__
        key_parts = [str(arg) for arg in args] + [f"{k}={v}" for k, v in kwargs.items()]
        return f"{prefix}:{':'.join(key_parts)}"

    def get_cached_data(self, cache_key, data_function, *args, **kwargs):
        """Busca dados do cache ou executa função"""
        data = cache.get(cache_key)
        if data is None:
            data = data_function(*args, **kwargs)
            cache.set(cache_key, data, self.cache_timeout)
        return data


class ServiceBasedViewMixin:
    """
    Mixin para views que usam Services
    Força uso dos Services ao invés de queries diretas
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Adicionar services no contexto para uso nos templates
        context.update({
            'usuario_service': UsuarioService,
            'formador_service': FormadorService,
            'coordinator_service': CoordinatorService,
            'dashboard_service': DashboardService,
            'municipio_service': MunicipioService,
        })

        return context


# ===============================
# CLASSES BASE PARA VIEWS
# ===============================

class BaseListView(OptimizedQueryMixin, CachedViewMixin, ServiceBasedViewMixin, ListView):
    """Classe base otimizada para ListView"""
    paginate_by = 25


class BaseDetailView(OptimizedQueryMixin, ServiceBasedViewMixin, DetailView):
    """Classe base otimizada para DetailView"""
    pass


class BaseCreateView(ServiceBasedViewMixin, CreateView):
    """Classe base para CreateView"""

    def form_valid(self, form):
        response = super().form_valid(form)
        # Limpar cache relacionado
        cache.clear()
        return response


class BaseUpdateView(ServiceBasedViewMixin, UpdateView):
    """Classe base para UpdateView"""

    def form_valid(self, form):
        response = super().form_valid(form)
        # Limpar cache relacionado
        cache.clear()
        return response


class BaseTemplateView(CachedViewMixin, ServiceBasedViewMixin, TemplateView):
    """Classe base para TemplateView"""
    pass


class BaseAPIView(View):
    """
    Classe base para APIs JSON
    Padroniza respostas e tratamento de erros
    """

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)

    def get_success_response(self, data, message="Success"):
        """Resposta JSON padrão de sucesso"""
        return JsonResponse({
            'success': True,
            'message': message,
            'data': data,
            'timestamp': timezone.now().isoformat()
        })

    def get_error_response(self, message, status=400):
        """Resposta JSON padrão de erro"""
        return JsonResponse({
            'success': False,
            'error': message,
            'timestamp': timezone.now().isoformat()
        }, status=status)


# ===============================
# FUNÇÕES UTILITÁRIAS
# ===============================

def get_optimized_usuario_queryset():
    """QuerySet otimizado padrão para Usuario"""
    return Usuario.objects.select_related(*USUARIO_SELECT_RELATED)


def get_optimized_solicitacao_queryset():
    """QuerySet otimizado padrão para Solicitacao"""
    return Solicitacao.objects.select_related(*SOLICITACAO_SELECT_RELATED).prefetch_related(*SOLICITACAO_PREFETCH_RELATED)


def clear_all_caches():
    """Limpa todos os caches do sistema"""
    cache.clear()


# ===============================
# COMPATIBILIDADE E DEPRECATION
# ===============================

# AVISO: Imports diretos dos models nas views são DESENCORAJADOS
# Use os Services sempre que possível
#
# ❌ EVITAR:   Formador.objects.filter(ativo=True)
# ✅ USAR:     FormadorService.todos_formadores()
#
# ❌ EVITAR:   Usuario.objects.filter(cargo='coordenador')
# ✅ USAR:     CoordinatorService.todos_coordenadores()

# Note: Import specific mixins in individual modules as needed
# from core.mixins import ...
