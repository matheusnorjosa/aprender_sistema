"""
Views para sistema CRUD de Deslocamentos.
Interface similar ao Excel para gerenciamento de deslocamentos de formadores.
"""

import json
from datetime import datetime, date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models import Deslocamento, Formador, LogAuditoria


class DeslocamentoListView(LoginRequiredMixin, ListView):
    """
    Lista todos os deslocamentos com interface similar ao Excel.
    Permite filtros por período, formador, origem/destino.
    """
    model = Deslocamento
    template_name = 'core/deslocamentos/list.html'
    context_object_name = 'deslocamentos'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Deslocamento.objects.select_related().prefetch_related(
            'pessoa_1', 'pessoa_2', 'pessoa_3', 'pessoa_4', 'pessoa_5', 'pessoa_6'
        ).order_by('-data', 'origem')
        
        # Filtros opcionais
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        formador_id = self.request.GET.get('formador')
        origem = self.request.GET.get('origem')
        destino = self.request.GET.get('destino')
        tipo = self.request.GET.get('tipo')
        
        if data_inicio:
            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                queryset = queryset.filter(data__gte=data_inicio)
            except ValueError:
                pass
                
        if data_fim:
            try:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                queryset = queryset.filter(data__lte=data_fim)
            except ValueError:
                pass
                
        if formador_id:
            queryset = queryset.filter(
                models.Q(pessoa_1_id=formador_id) |
                models.Q(pessoa_2_id=formador_id) |
                models.Q(pessoa_3_id=formador_id) |
                models.Q(pessoa_4_id=formador_id) |
                models.Q(pessoa_5_id=formador_id) |
                models.Q(pessoa_6_id=formador_id)
            )
            
        if origem:
            queryset = queryset.filter(origem__icontains=origem)
            
        if destino:
            queryset = queryset.filter(destino__icontains=destino)
            
        if tipo:
            queryset = queryset.filter(tipo=tipo)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'formadores': Formador.objects.filter(ativo=True).order_by('nome'),
            'filtros_ativos': any([
                self.request.GET.get('data_inicio'),
                self.request.GET.get('data_fim'),
                self.request.GET.get('formador'),
                self.request.GET.get('origem'),
                self.request.GET.get('destino'),
                self.request.GET.get('tipo'),
            ])
        })
        return context


class DeslocamentoCreateView(LoginRequiredMixin, CreateView):
    """
    Criação de novos deslocamentos com interface Excel-like.
    Suporta múltiplos formadores (pessoa_1 até pessoa_6).
    """
    model = Deslocamento
    template_name = 'core/deslocamentos/form.html'
    fields = ['data', 'tipo', 'origem', 'destino', 
              'pessoa_1', 'pessoa_2', 'pessoa_3', 'pessoa_4', 'pessoa_5', 'pessoa_6']
    success_url = reverse_lazy('core:deslocamentos_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Novo Deslocamento',
            'formadores': Formador.objects.filter(ativo=True).order_by('nome'),
            'action': 'create'
        })
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log de auditoria
        LogAuditoria.objects.create(
            usuario=self.request.user,
            acao='CREATE',
            modelo='Deslocamento',
            objeto_id=str(self.object.id),
            detalhes=f'Criado deslocamento: {self.object.origem} → {self.object.destino} em {self.object.data}'
        )
        
        messages.success(self.request, f'Deslocamento criado com sucesso: {self.object}')
        return response


class DeslocamentoUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edição de deslocamentos existentes.
    """
    model = Deslocamento
    template_name = 'core/deslocamentos/form.html'
    fields = ['data', 'tipo', 'origem', 'destino', 
              'pessoa_1', 'pessoa_2', 'pessoa_3', 'pessoa_4', 'pessoa_5', 'pessoa_6']
    success_url = reverse_lazy('core:deslocamentos_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': f'Editar Deslocamento - {self.object}',
            'formadores': Formador.objects.filter(ativo=True).order_by('nome'),
            'action': 'update'
        })
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log de auditoria
        LogAuditoria.objects.create(
            usuario=self.request.user,
            acao='UPDATE',
            modelo='Deslocamento',
            objeto_id=str(self.object.id),
            detalhes=f'Atualizado deslocamento: {self.object}'
        )
        
        messages.success(self.request, f'Deslocamento atualizado: {self.object}')
        return response


class DeslocamentoDeleteView(LoginRequiredMixin, DeleteView):
    """
    Exclusão de deslocamentos com confirmação.
    """
    model = Deslocamento
    template_name = 'core/deslocamentos/delete.html'
    success_url = reverse_lazy('core:deslocamentos_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Log de auditoria antes da exclusão
        LogAuditoria.objects.create(
            usuario=request.user,
            acao='DELETE',
            modelo='Deslocamento',
            objeto_id=str(self.object.id),
            detalhes=f'Excluído deslocamento: {self.object}'
        )
        
        messages.success(request, f'Deslocamento excluído: {self.object}')
        return super().delete(request, *args, **kwargs)


class DeslocamentoAPI(LoginRequiredMixin, View):
    """
    API para operações AJAX com deslocamentos.
    Usado para carregamento dinâmico e validações.
    """
    
    def get(self, request):
        """
        Retorna deslocamentos em formato JSON para uso em interfaces dinâmicas.
        """
        try:
            # Parâmetros de filtro
            mes = request.GET.get('mes')
            ano = request.GET.get('ano')
            formador_id = request.GET.get('formador_id')
            
            queryset = Deslocamento.objects.all()
            
            if ano:
                queryset = queryset.filter(data__year=int(ano))
            if mes:
                queryset = queryset.filter(data__month=int(mes))
            if formador_id:
                queryset = queryset.filter(
                    models.Q(pessoa_1_id=formador_id) |
                    models.Q(pessoa_2_id=formador_id) |
                    models.Q(pessoa_3_id=formador_id) |
                    models.Q(pessoa_4_id=formador_id) |
                    models.Q(pessoa_5_id=formador_id) |
                    models.Q(pessoa_6_id=formador_id)
                )
            
            deslocamentos = []
            for desloc in queryset.select_related().prefetch_related(
                'pessoa_1', 'pessoa_2', 'pessoa_3', 'pessoa_4', 'pessoa_5', 'pessoa_6'
            ):
                deslocamentos.append({
                    'id': str(desloc.id),
                    'data': desloc.data.strftime('%Y-%m-%d'),
                    'data_display': desloc.data.strftime('%d/%m/%Y'),
                    'tipo': desloc.tipo,
                    'tipo_display': desloc.get_tipo_display(),
                    'origem': desloc.origem,
                    'destino': desloc.destino,
                    'pessoas': [getattr(p, 'nome_completo', p.nome if hasattr(p, 'nome') else str(p)) for p in desloc.pessoas],
                    'pessoas_count': len(desloc.pessoas),
                })
            
            return JsonResponse({
                'success': True,
                'deslocamentos': deslocamentos,
                'total': len(deslocamentos)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao buscar deslocamentos: {str(e)}'
            })
    
    def post(self, request):
        """
        Criação rápida de deslocamento via AJAX.
        """
        try:
            data = json.loads(request.body)
            
            # Validação básica
            required_fields = ['data', 'origem', 'destino']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'error': f'Campo obrigatório: {field}'
                    })
            
            # Criar deslocamento
            desloc = Deslocamento.objects.create(
                data=datetime.strptime(data['data'], '%Y-%m-%d').date(),
                tipo=data.get('tipo', 'deslocamento'),
                origem=data['origem'],
                destino=data['destino'],
                pessoa_1_id=data.get('pessoa_1'),
                pessoa_2_id=data.get('pessoa_2'),
                pessoa_3_id=data.get('pessoa_3'),
                pessoa_4_id=data.get('pessoa_4'),
                pessoa_5_id=data.get('pessoa_5'),
                pessoa_6_id=data.get('pessoa_6'),
            )
            
            # Log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                acao='CREATE_AJAX',
                modelo='Deslocamento',
                objeto_id=str(desloc.id),
                detalhes=f'Criado via AJAX: {desloc}'
            )
            
            return JsonResponse({
                'success': True,
                'deslocamento': {
                    'id': str(desloc.id),
                    'data': desloc.data.strftime('%d/%m/%Y'),
                    'tipo': desloc.get_tipo_display(),
                    'origem': desloc.origem,
                    'destino': desloc.destino,
                    'pessoas': [getattr(p, 'nome_completo', p.nome if hasattr(p, 'nome') else str(p)) for p in desloc.pessoas],
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao criar deslocamento: {str(e)}'
            })