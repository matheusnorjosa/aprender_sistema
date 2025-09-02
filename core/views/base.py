"""
Imports e configurações base para todas as views.
Centraliza dependências comuns para evitar repetição.
"""

# Imports padrão Python
from datetime import timedelta, time

# Imports Django
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, ListView, FormView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.http import JsonResponse
from django.views import View

# Imports da aplicação
from core.forms import SolicitacaoForm, AprovacaoDecisionForm, BloqueioAgendaForm
from core.models import (
    Solicitacao, SolicitacaoStatus, Aprovacao, AprovacaoStatus, LogAuditoria, Formador,
    EventoGoogleCalendar, Municipio, Projeto, TipoEvento, FormadoresSolicitacao
)
# Note: Import specific mixins in individual modules as needed
# from core.mixins import ...