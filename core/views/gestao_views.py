"""
Views para gestão administrativa da plataforma.
Páginas customizadas para CRUD de entidades principais.
ATUALIZADO: Usa Services centralizados e imports unificados
"""

# IMPORT ÚNICO - Single Source of Truth
from .base import *


class GestaoBaseMixin(LoginRequiredMixin):
    """Mixin base para todas as views de gestão"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Acesso negado. Apenas administradores podem acessar esta seção.')
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)


class GestaoDashboardView(GestaoBaseMixin, TemplateView):
    """Dashboard principal da gestão administrativa"""
    template_name = 'core/gestao/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estatísticas gerais usando Services centralizados
        stats = DashboardService.get_estatisticas_gerais()

        context.update({
            'total_formadores': len(FormadorService.todos_formadores()) + Usuario.objects.filter(formador_ativo=False).count(),
            'formadores_ativos': stats['formadores_ativos'],
            'total_municipios': MunicipioService.ativos().count() + Municipio.objects.filter(ativo=False).count(),
            'municipios_ativos': stats['municipios_ativos'],
            'total_projetos': Projeto.objects.count(),
            'projetos_ativos': stats['projetos_ativos'],
            'total_tipos_evento': TipoEvento.objects.count(),
            'tipos_evento_ativos': TipoEvento.objects.filter(ativo=True).count(),
        })

        return context


# ====== GESTÃO DE FORMADORES ======

class FormadorListView(GestaoBaseMixin, BaseListView):
    """Lista de formadores com busca e filtros - FONTE ÚNICA Usuario"""
    model = Usuario
    template_name = 'core/gestao/formadores/list.html'
    context_object_name = 'formadores'
    paginate_by = 25
    select_related_fields = ['setor', 'municipio', 'area_atuacao']

    def get_queryset(self):
        # Usar Service centralizado - inclui formadores ativos e inativos
        queryset = UsuarioService.get_optimized_queryset().filter(
            Q(formador_ativo=True) | Q(groups__name='formador')
        ).distinct()

        # Busca por nome ou email
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        # Filtro por área de atuação
        area = self.request.GET.get('area')
        if area:
            queryset = queryset.filter(area_atuacao_id=area)

        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(formador_ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(formador_ativo=False)

        return queryset.order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['areas_atuacao'] = Group.objects.all()
        context['search'] = self.request.GET.get('search', '')
        context['area_filter'] = self.request.GET.get('area', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class FormadorCreateView(GestaoBaseMixin, BaseCreateView):
    """Criar novo formador - FONTE ÚNICA Usuario"""
    model = Usuario
    form_class = FormadorForm
    template_name = 'core/gestao/formadores/form.html'
    success_url = reverse_lazy('core:gestao_formadores')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Garantir que o usuário seja marcado como formador
        self.object.formador_ativo = True
        self.object.save()
        # Adicionar ao grupo formador
        formador_group, _ = Group.objects.get_or_create(name='formador')
        self.object.groups.add(formador_group)
        messages.success(self.request, 'Formador criado com sucesso!')
        return response


class FormadorUpdateView(GestaoBaseMixin, BaseUpdateView):
    """Editar formador existente - FONTE ÚNICA Usuario"""
    model = Usuario
    form_class = FormadorForm
    template_name = 'core/gestao/formadores/form.html'
    success_url = reverse_lazy('core:gestao_formadores')

    def get_queryset(self):
        # Apenas usuários que são formadores
        return UsuarioService.get_optimized_queryset().filter(
            Q(formador_ativo=True) | Q(groups__name='formador')
        ).distinct()

    def form_valid(self, form):
        messages.success(self.request, 'Formador atualizado com sucesso!')
        return super().form_valid(form)


class FormadorDeleteView(GestaoBaseMixin, DeleteView):
    """Excluir formador - FONTE ÚNICA Usuario"""
    model = Usuario
    template_name = 'core/gestao/formadores/delete.html'
    success_url = reverse_lazy('core:gestao_formadores')

    def get_queryset(self):
        # Apenas usuários que são formadores
        return UsuarioService.get_optimized_queryset().filter(
            Q(formador_ativo=True) | Q(groups__name='formador')
        ).distinct()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete - apenas desativa o formador
        self.object.formador_ativo = False
        self.object.save()
        # Remover do grupo formador
        formador_group = Group.objects.filter(name='formador').first()
        if formador_group:
            self.object.groups.remove(formador_group)
        messages.success(request, 'Formador desativado com sucesso!')
        return redirect(self.success_url)


# ====== GESTÃO DE MUNICÍPIOS ======

class MunicipioListView(GestaoBaseMixin, BaseListView):
    """Lista de municípios com busca e filtros - OTIMIZADA"""
    model = Municipio
    template_name = 'core/gestao/municipios/list.html'
    context_object_name = 'municipios'
    paginate_by = 50

    def get_queryset(self):
        # Usar Service centralizado como base
        base_qs = MunicipioService.ativos()

        # Incluir inativos também
        queryset = Municipio.objects.all()

        # Busca por nome ou UF
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) | Q(uf__icontains=search)
            )

        # Filtro por UF
        uf = self.request.GET.get('uf')
        if uf:
            queryset = queryset.filter(uf=uf)

        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)

        return queryset.order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ufs'] = Municipio.objects.values_list('uf', flat=True).distinct().order_by('uf')
        context['search'] = self.request.GET.get('search', '')
        context['uf_filter'] = self.request.GET.get('uf', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class MunicipioCreateView(GestaoBaseMixin, BaseCreateView):
    """Criar novo município"""
    model = Municipio
    form_class = MunicipioForm
    template_name = 'core/gestao/municipios/form.html'
    success_url = reverse_lazy('core:gestao_municipios')

    def form_valid(self, form):
        messages.success(self.request, 'Município criado com sucesso!')
        return super().form_valid(form)


class MunicipioUpdateView(GestaoBaseMixin, BaseUpdateView):
    """Editar município existente"""
    model = Municipio
    form_class = MunicipioForm
    template_name = 'core/gestao/municipios/form.html'
    success_url = reverse_lazy('core:gestao_municipios')

    def form_valid(self, form):
        messages.success(self.request, 'Município atualizado com sucesso!')
        return super().form_valid(form)


class MunicipioDeleteView(GestaoBaseMixin, DeleteView):
    """Excluir município"""
    model = Municipio
    template_name = 'core/gestao/municipios/delete.html'
    success_url = reverse_lazy('core:gestao_municipios')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(request, 'Município desativado com sucesso!')
        return redirect(self.success_url)


# ====== GESTÃO DE PROJETOS ======

class ProjetoListView(GestaoBaseMixin, BaseListView):
    """Lista de projetos com busca e filtros - OTIMIZADA"""
    model = Projeto
    template_name = 'core/gestao/projetos/list.html'
    context_object_name = 'projetos'
    paginate_by = 25
    select_related_fields = ['setor']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Busca por nome
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(nome__icontains=search)

        # Filtro por setor
        setor = self.request.GET.get('setor')
        if setor:
            queryset = queryset.filter(setor_id=setor)

        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)

        return queryset.order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setores'] = Setor.objects.all()
        context['search'] = self.request.GET.get('search', '')
        context['setor_filter'] = self.request.GET.get('setor', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class ProjetoCreateView(GestaoBaseMixin, BaseCreateView):
    """Criar novo projeto"""
    model = Projeto
    form_class = ProjetoForm
    template_name = 'core/gestao/projetos/form.html'
    success_url = reverse_lazy('core:gestao_projetos')

    def form_valid(self, form):
        messages.success(self.request, 'Projeto criado com sucesso!')
        return super().form_valid(form)


class ProjetoUpdateView(GestaoBaseMixin, BaseUpdateView):
    """Editar projeto existente"""
    model = Projeto
    form_class = ProjetoForm
    template_name = 'core/gestao/projetos/form.html'
    success_url = reverse_lazy('core:gestao_projetos')

    def form_valid(self, form):
        messages.success(self.request, 'Projeto atualizado com sucesso!')
        return super().form_valid(form)


class ProjetoDeleteView(GestaoBaseMixin, DeleteView):
    """Excluir projeto"""
    model = Projeto
    template_name = 'core/gestao/projetos/delete.html'
    success_url = reverse_lazy('core:gestao_projetos')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(request, 'Projeto desativado com sucesso!')
        return redirect(self.success_url)


# ====== GESTÃO DE TIPOS DE EVENTO ======

class TipoEventoListView(GestaoBaseMixin, BaseListView):
    """Lista de tipos de evento com busca e filtros - OTIMIZADA"""
    model = TipoEvento
    template_name = 'core/gestao/tipos_evento/list.html'
    context_object_name = 'tipos_evento'
    paginate_by = 25

    def get_queryset(self):
        queryset = TipoEvento.objects.all()

        # Busca por nome
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(nome__icontains=search)

        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)

        return queryset.order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class TipoEventoCreateView(GestaoBaseMixin, BaseCreateView):
    """Criar novo tipo de evento"""
    model = TipoEvento
    form_class = TipoEventoForm
    template_name = 'core/gestao/tipos_evento/form.html'
    success_url = reverse_lazy('core:gestao_tipos_evento')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de evento criado com sucesso!')
        return super().form_valid(form)


class TipoEventoUpdateView(GestaoBaseMixin, BaseUpdateView):
    """Editar tipo de evento existente"""
    model = TipoEvento
    form_class = TipoEventoForm
    template_name = 'core/gestao/tipos_evento/form.html'
    success_url = reverse_lazy('core:gestao_tipos_evento')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de evento atualizado com sucesso!')
        return super().form_valid(form)


class TipoEventoDeleteView(GestaoBaseMixin, DeleteView):
    """Excluir tipo de evento"""
    model = TipoEvento
    template_name = 'core/gestao/tipos_evento/delete.html'
    success_url = reverse_lazy('core:gestao_tipos_evento')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(request, 'Tipo de evento desativado com sucesso!')
        return redirect(self.success_url)