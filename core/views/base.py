"""
Imports e configurações base para todas as views.
Centraliza dependências comuns para evitar repetição.
"""

# Imports padrão Python
from datetime import time, timedelta

from django.conf import settings

# Imports Django
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, FormView, ListView, TemplateView

# Imports da aplicação
from core.forms import AprovacaoDecisionForm, BloqueioAgendaForm, SolicitacaoForm
from core.models import (
    Aprovacao,
    AprovacaoStatus,
    EventoGoogleCalendar,
    Formador,
    FormadoresSolicitacao,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)

# Note: Import specific mixins in individual modules as needed
# from core.mixins import ...
