# core/views/importacao_views.py
"""
Views para funcionalidades de importação de cursos via CSV.
Funcionalidades migradas da branch feature/importacoes-planilhas
"""

import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, FormView

from core.models import CursoPlataforma, ImportacaoCursosCSV, ProjetoCursoLink, Projeto
from core.services.curso_csv_processor import CursoCSVProcessor


class CursosCSVUploadView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Interface para upload e processamento de CSV de cursos - acesso restrito ao grupo DAT"""
    template_name = 'core/cursos_csv_upload.html'

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estatísticas de importações anteriores
        context['total_cursos'] = CursoPlataforma.objects.count()
        context['importacoes_recentes'] = ImportacaoCursosCSV.objects.order_by('-data_inicio')[:5]

        return context


class CursosCSVProcessarView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Processa o arquivo CSV de cursos - acesso restrito ao grupo DAT"""

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def post(self, request):
        try:
            if 'csv_file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'Arquivo CSV não encontrado'
                })

            csv_file = request.FILES['csv_file']
            ano_filter = request.POST.get('ano_filter')

            # Validações básicas
            if not csv_file.name.endswith('.csv'):
                return JsonResponse({
                    'success': False,
                    'error': 'Arquivo deve ser do tipo CSV'
                })

            if csv_file.size > 10 * 1024 * 1024:  # 10MB
                return JsonResponse({
                    'success': False,
                    'error': 'Arquivo muito grande (máximo 10MB)'
                })

            # Ler conteúdo do arquivo com detecção automática de encoding
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
            csv_content = None

            for encoding in encodings:
                try:
                    csv_file.seek(0)  # Reset file pointer
                    csv_content = csv_file.read().decode(encoding)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if csv_content is None:
                return JsonResponse({
                    'success': False,
                    'error': 'Não foi possível decodificar o arquivo CSV. Formatos suportados: UTF-8, Latin1, CP1252.'
                })

            # Processar CSV
            processor = CursoCSVProcessor()
            ano_filter = int(ano_filter) if ano_filter and ano_filter.isdigit() else None

            resultado = processor.process_csv_content(csv_content, ano_filter)

            return JsonResponse({
                'success': True,
                'importacao_id': str(resultado.get('importacao_id', '')),
                'cursos_criados': resultado['cursos_criados'],
                'cursos_atualizados': resultado['cursos_atualizados'],
                'errors': resultado['errors'],
                'warnings': resultado['warnings']
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro no processamento: {str(e)}'
            })


class CursosCSVPreviewView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Visualização prévia do CSV antes da importação - acesso restrito ao grupo DAT"""

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def post(self, request):
        try:
            if 'csv_file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'Arquivo CSV não encontrado'
                })

            csv_file = request.FILES['csv_file']
            ano_filter = request.POST.get('ano_filter')

            # Validações básicas
            if not csv_file.name.endswith('.csv'):
                return JsonResponse({
                    'success': False,
                    'error': 'Arquivo deve ser do tipo CSV'
                })

            # Ler e processar apenas para preview (sem salvar)
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
            csv_content = None

            for encoding in encodings:
                try:
                    csv_file.seek(0)
                    csv_content = csv_file.read().decode(encoding)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if csv_content is None:
                return JsonResponse({
                    'success': False,
                    'error': 'Não foi possível decodificar o arquivo CSV'
                })

            # Preview: mostrar primeiras 10 linhas
            import csv
            import io

            csv_file_obj = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file_obj, delimiter=';')

            preview_data = []
            for i, row in enumerate(reader):
                if i >= 10:  # Limitar preview a 10 linhas
                    break
                preview_data.append(dict(row))

            return JsonResponse({
                'success': True,
                'headers': reader.fieldnames,
                'preview_data': preview_data,
                'total_estimated': len(csv_content.split('\n')) - 1  # Aproximado
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro no preview: {str(e)}'
            })


class VinculosProjetoCursoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Lista todos os vínculos Projeto-Curso"""
    model = ProjetoCursoLink
    template_name = 'core/vinculos_projeto_curso.html'
    context_object_name = 'vinculos'
    paginate_by = 50

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def get_queryset(self):
        return ProjetoCursoLink.objects.select_related('projeto', 'curso_plataforma').order_by(
            'projeto__nome', 'curso_plataforma__nome_breve'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_vinculos'] = ProjetoCursoLink.objects.count()
        context['vinculos_manuais'] = ProjetoCursoLink.objects.filter(mapeamento_manual=True).count()
        context['vinculos_automaticos'] = ProjetoCursoLink.objects.filter(mapeamento_manual=False).count()
        return context


class CursosSemVinculoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Lista cursos sem vínculo com projeto"""
    model = CursoPlataforma
    template_name = 'core/cursos_sem_vinculo.html'
    context_object_name = 'cursos'
    paginate_by = 50

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def get_queryset(self):
        # Cursos que não têm vínculo com projeto
        return CursoPlataforma.objects.filter(
            projetocursolink__isnull=True,
            ativo=True
        ).order_by('nome_breve')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sem_vinculo'] = self.get_queryset().count()
        context['projetos'] = Projeto.objects.filter(ativo=True).order_by('nome')
        return context


class VincularCursoProjetoView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vincula manualmente um curso a um projeto"""

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def post(self, request):
        try:
            curso_id = request.POST.get('curso_id')
            projeto_id = request.POST.get('projeto_id')

            if not curso_id or not projeto_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Curso e Projeto são obrigatórios'
                })

            curso = get_object_or_404(CursoPlataforma, id=curso_id)
            projeto = get_object_or_404(Projeto, id=projeto_id)

            # Verificar se já existe vínculo
            if ProjetoCursoLink.objects.filter(curso_plataforma=curso, projeto=projeto).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Vínculo já existe entre este curso e projeto'
                })

            # Criar vínculo manual
            vinculo = ProjetoCursoLink.objects.create(
                curso_plataforma=curso,
                projeto=projeto,
                mapeamento_manual=True,
                usuario_vinculacao=request.user
            )

            return JsonResponse({
                'success': True,
                'message': f'Vínculo criado: {curso.nome_breve} → {projeto.nome}',
                'vinculo_id': str(vinculo.id)
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao criar vínculo: {str(e)}'
            })


class DesvincularCursoView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Remove vínculo entre curso e projeto"""

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def post(self, request):
        try:
            vinculo_id = request.POST.get('vinculo_id')

            if not vinculo_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID do vínculo é obrigatório'
                })

            vinculo = get_object_or_404(ProjetoCursoLink, id=vinculo_id)

            curso_nome = vinculo.curso_plataforma.nome_breve
            projeto_nome = vinculo.projeto.nome

            vinculo.delete()

            return JsonResponse({
                'success': True,
                'message': f'Vínculo removido: {curso_nome} ↛ {projeto_nome}'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao remover vínculo: {str(e)}'
            })


class ReprocessarVinculacaoAutomaticaView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Reprocessa a vinculação automática para cursos sem vínculo"""

    def test_func(self):
        """Apenas usuários do grupo DAT podem acessar"""
        return self.request.user.groups.filter(name='dat').exists() or self.request.user.is_superuser

    def post(self, request):
        try:
            # Buscar cursos sem vínculo
            cursos_sem_vinculo = CursoPlataforma.objects.filter(
                projetocursolink__isnull=True,
                ativo=True
            )

            processor = CursoCSVProcessor()
            vinculos_criados = 0
            warnings = []

            for curso in cursos_sem_vinculo:
                # Tentar vincular automaticamente
                processor._try_link_projeto(curso)

                # Verificar se foi vinculado
                if ProjetoCursoLink.objects.filter(curso_plataforma=curso).exists():
                    vinculos_criados += 1

            warnings = processor.warnings

            return JsonResponse({
                'success': True,
                'vinculos_criados': vinculos_criados,
                'total_processados': cursos_sem_vinculo.count(),
                'warnings': warnings
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro no reprocessamento: {str(e)}'
            })