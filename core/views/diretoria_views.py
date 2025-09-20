"""
Views relacionadas ao perfil de Diretoria (visão executiva e relatórios).
ATUALIZADO: Usa Services centralizados e imports unificados
"""

# IMPORT ÚNICO - Single Source of Truth
from .base import *


class DiretoriaExecutiveDashboardView(
    LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    permission_required = "core.view_relatorios"
    template_name = "core/diretoria/dashboard_working_original.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agora = timezone.now()

        # Filtros selecionados (utilizamos IDs para evitar ambiguidades)
        municipio_id = self.request.GET.get("municipio_id")
        municipio_nome_param = self.request.GET.get("municipio", "")
        uf_param = self.request.GET.get("uf", "")
        regiao_param = self.request.GET.get("regiao", "")

        try:
            periodo_filtro = int(self.request.GET.get("periodo", 12))
        except (TypeError, ValueError):
            periodo_filtro = 12

        municipio_obj = None
        if municipio_id:
            municipio_obj = Municipio.objects.filter(id=municipio_id).first()
        elif municipio_nome_param:
            municipio_obj = (
                Municipio.objects.filter(nome__iexact=municipio_nome_param).order_by("uf").first()
            )

        municipios_queryset = (
            Municipio.objects.filter(ativo=True)
            .values("id", "nome", "uf")
            .order_by("nome", "uf")
        )

        context.update(
            {
                "ano_atual": agora.year,
                "trimestre_atual": f"Q{((agora.month - 1) // 3) + 1}",
                "periodo_selecionado": periodo_filtro,
                "municipio_id_selecionado": str(municipio_obj.id) if municipio_obj else "",
                "municipio_nome_selecionado": municipio_obj.nome if municipio_obj else municipio_nome_param,
                "uf_selecionada": uf_param or (municipio_obj.uf if municipio_obj else ""),
                "regiao_selecionada": regiao_param,
                "municipios_opcoes": [
                    {
                        "id": str(item["id"]),
                        "nome": item["nome"],
                        "uf": item["uf"],
                    }
                    for item in municipios_queryset
                ],
            }
        )
        return context


class DiretoriaRelatoriosView(
    LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    permission_required = "core.view_relatorios"
    template_name = "core/diretoria/relatorios.html"


class DiretoriaIntegratedDashboardView(
    LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    """Dashboard integrado com Streamlit"""
    permission_required = "core.view_relatorios"
    template_name = "core/diretoria/dashboard_integrated.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Usar Services centralizados - elimina queries ad-hoc
        stats_gerais = DashboardService.get_estatisticas_gerais()

        context.update({
            "total_solicitacoes_ano": stats_gerais['solicitacoes_ano'],
            "solicitacoes_aprovadas_ano": stats_gerais['solicitacoes_aprovadas_ano'],
            "taxa_aprovacao_ano": stats_gerais['taxa_aprovacao_ano'],
            "formadores_ativos": stats_gerais['formadores_ativos'],
            "municipios_total": stats_gerais['municipios_ativos'],
            "projetos_ativos": stats_gerais['projetos_ativos'],
            "ano_atual": timezone.now().year,
        })
        return context


class DiretoriaDebugView(LoginRequiredMixin, TemplateView):
    """View de debug temporária para testar gráficos"""
    template_name = "core/diretoria/debug_dashboard.html"


class DashboardStatsAPIView(LoginRequiredMixin, PermissionRequiredMixin, BaseAPIView):
    permission_required = "core.view_relatorios"

    def get(self, request):
        """Estatísticas básicas usando Services unificados"""
        try:
            # Usar Services centralizados - fonte única de verdade
            stats_gerais = DashboardService.get_estatisticas_gerais()

            # Query otimizada para eventos de hoje
            hoje = timezone.now().date()
            eventos_hoje = get_optimized_solicitacao_queryset().filter(
                data_inicio__date=hoje,
                status=SolicitacaoStatus.APROVADO,
            ).count()

            stats = {
                "total_solicitacoes": stats_gerais['solicitacoes_ano'],
                "formadores_ativos": stats_gerais['formadores_ativos'],
                "eventos_hoje": eventos_hoje,
                "coordenadores_total": stats_gerais['coordenadores_total'],
                "municipios_ativos": stats_gerais['municipios_ativos'],
                "taxa_aprovacao": stats_gerais['taxa_aprovacao_ano']
            }

            return self.get_success_response(stats)

        except Exception as e:
            return self.get_error_response(f"Erro ao buscar estatísticas: {str(e)}")


class DiretoriaAPIMetricsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "core.view_relatorios"

    def get(self, request):
        agora = timezone.now()
        data_limite = agora - timedelta(days=30)

        metrics = {
            "solicitacoes_mes": Solicitacao.objects.filter(
                data_inicio__gte=data_limite
            ).count(),
            "aprovacoes_mes": Solicitacao.objects.filter(
                data_inicio__gte=data_limite, status=SolicitacaoStatus.APROVADO
            ).count(),
        }
        return JsonResponse(metrics)


class DashboardChartsAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """API para dados de gráficos do dashboard executivo"""
    permission_required = "core.view_relatorios"

    def get(self, request):
        chart_type = request.GET.get('chart', 'monthly_evolution')
        
        if chart_type == 'monthly_evolution':
            return self.get_monthly_evolution()
        elif chart_type == 'top_formadores':
            return self.get_top_formadores()
        elif chart_type == 'distribuicao_setores':
            return self.get_distribuicao_setores()
        elif chart_type == 'municipios_atendidos':
            return self.get_municipios_atendidos()
        elif chart_type == 'tipos_evento':
            return self.get_tipos_evento()
        elif chart_type == 'projetos_stats':
            return self.get_projetos_stats()
        
        return JsonResponse({'error': 'Chart type not found'}, status=400)
    
    def get_monthly_evolution(self):
        """Evolução mensal de eventos"""
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        
        # Tentar buscar do cache primeiro
        cache_key = 'monthly_evolution_data'
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({'data': cached_data})
        
        agora = timezone.now()
        inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        eventos_por_mes = (
            Solicitacao.objects
            .filter(data_inicio__gte=inicio_ano)
            .annotate(mes=TruncMonth('data_inicio'))
            .values('mes')
            .annotate(
                total=Count('id'),
                aprovados=Count('id', filter=Q(status=SolicitacaoStatus.APROVADO)),
                pendentes=Count('id', filter=Q(status=SolicitacaoStatus.PENDENTE))
            )
            .order_by('mes')
        )
        
        data = []
        for item in eventos_por_mes:
            data.append({
                'mes': item['mes'].strftime('%b %Y'),
                'total': item['total'],
                'aprovados': item['aprovados'],
                'pendentes': item['pendentes']
            })
        
        # Salvar no cache por 5 minutos
        cache.set(cache_key, data, 300)
        return JsonResponse({'data': data})
    
    def get_top_formadores(self):
        """Top 10 formadores por eventos realizados - OTIMIZADO"""

        # Cache por 5 minutos
        cache_key = 'top_formadores_data'
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({'data': cached_data})

        agora = timezone.now()
        tres_meses_atras = agora - timedelta(days=90)

        # Query otimizada com Services - evita duplicação de lógica
        formadores = (
            FormadoresSolicitacao.objects
            .select_related('usuario', 'usuario__area_atuacao', 'solicitacao')
            .filter(
                solicitacao__data_inicio__gte=tres_meses_atras,
                solicitacao__status=SolicitacaoStatus.APROVADO
            )
            .values('usuario__first_name', 'usuario__last_name', 'usuario__area_atuacao__name')
            .annotate(eventos=Count('id'))
            .order_by('-eventos')[:10]
        )

        data = []
        for formador in formadores:
            # Combinar first_name e last_name para nome completo
            nome_completo = f"{formador['usuario__first_name']} {formador['usuario__last_name']}".strip()
            data.append({
                'nome': nome_completo,
                'area': formador.get('usuario__area_atuacao__name', 'Formação'),
                'eventos': formador['eventos']
            })

        cache.set(cache_key, data, 300)
        return JsonResponse({'data': data})
    
    def get_distribuicao_setores(self):
        """Distribuição de eventos por setor - OTIMIZADO"""

        agora = timezone.now()
        inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Query otimizada usando queryset base
        setores = (
            get_optimized_solicitacao_queryset()
            .filter(
                data_inicio__gte=inicio_ano,
                status=SolicitacaoStatus.APROVADO
            )
            .values('projeto__setor__nome', 'projeto__setor__sigla')
            .annotate(eventos=Count('id'))
            .order_by('-eventos')
        )

        data = []
        for setor in setores:
            data.append({
                'nome': setor['projeto__setor__nome'] or 'Sem setor',
                'sigla': setor['projeto__setor__sigla'] or 'N/A',
                'eventos': setor['eventos']
            })

        return JsonResponse({'data': data})
    
    def get_municipios_atendidos(self):
        """Top municípios atendidos - OTIMIZADO"""

        agora = timezone.now()
        tres_meses_atras = agora - timedelta(days=90)

        # Query otimizada usando queryset base
        municipios = (
            get_optimized_solicitacao_queryset()
            .filter(
                data_inicio__gte=tres_meses_atras,
                status=SolicitacaoStatus.APROVADO
            )
            .values('municipio__nome', 'municipio__uf')
            .annotate(eventos=Count('id'))
            .order_by('-eventos')[:10]
        )

        data = []
        for municipio in municipios:
            data.append({
                'nome': municipio['municipio__nome'],
                'uf': municipio['municipio__uf'],
                'eventos': municipio['eventos']
            })

        return JsonResponse({'data': data})
    
    def get_tipos_evento(self):
        """Distribuição por tipos de evento - OTIMIZADO"""

        agora = timezone.now()
        inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Query otimizada usando queryset base
        tipos = (
            get_optimized_solicitacao_queryset()
            .filter(
                data_inicio__gte=inicio_ano,
                status=SolicitacaoStatus.APROVADO
            )
            .values('tipo_evento__nome')
            .annotate(quantidade=Count('id'))
            .order_by('-quantidade')
        )

        data = []
        for tipo in tipos:
            data.append({
                'tipo': tipo['tipo_evento__nome'],
                'quantidade': tipo['quantidade']
            })

        return JsonResponse({'data': data})
    
    def get_projetos_stats(self):
        """Estatísticas de projetos mais ativos - OTIMIZADO"""

        agora = timezone.now()
        tres_meses_atras = agora - timedelta(days=90)

        # Query otimizada usando queryset base
        projetos = (
            get_optimized_solicitacao_queryset()
            .filter(
                data_inicio__gte=tres_meses_atras,
                status=SolicitacaoStatus.APROVADO
            )
            .values('projeto__nome')
            .annotate(eventos=Count('id'))
            .order_by('-eventos')[:8]
        )

        data = []
        for projeto in projetos:
            data.append({
                'nome': projeto['projeto__nome'],
                'eventos': projeto['eventos']
            })

        return JsonResponse({'data': data})


class ChartJSServeView(View):
    """Serve Chart.js file directly"""
    
    def get(self, request):
        chart_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'js', 'chart.min.js')
        
        try:
            with open(chart_path, 'rb') as f:  # Modo binário
                content = f.read()
            
            response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
            response['Cache-Control'] = 'max-age=3600'  # Cache por 1 hora
            return response
        except FileNotFoundError:
            return HttpResponse('Chart.js not found', status=404)


class TestMapView(TemplateView):
    """View para testar o carregamento do mapa do Brasil"""
    template_name = "core/test_map.html"

class TestMapSimpleView(TemplateView):
    """View para testar o carregamento do mapa do Brasil com GeoJSON simples"""
    template_name = "core/test_map_simple.html"

class TestMapFinalView(TemplateView):
    """View para testar o carregamento do mapa do Brasil com GeoJSON real"""
    template_name = "core/test_map_final.html"

class TestMapAdvancedView(TemplateView):
    """View para o mapa avançado com dados de projetos e animações"""
    template_name = "core/test_map_advanced.html"

class DashboardCursosAPIView(BaseAPIView):
    """API para dados de cursos do dashboard executivo - OTIMIZADA"""

    def get(self, request):
        try:
            # Usar query otimizada do base.py
            tipos_evento = (
                get_optimized_solicitacao_queryset()
                .values('projeto__nome')
                .annotate(eventos=Count('id'))
                .order_by('-eventos')
            )

            series_data = [
                {
                    'label': item['projeto__nome'] or 'Sem projeto',
                    'value': item['eventos']
                }
                for item in tipos_evento
            ]

            dados = {
                'series': series_data,
                'total_eventos': sum(item['eventos'] for item in tipos_evento)
            }

            return self.get_success_response(dados)

        except Exception as e:
            return self.get_error_response(f"Erro ao buscar dados de cursos: {str(e)}")

class DashboardCoordenadoresAPIView(BaseAPIView):
    """API para dados de coordenadores - UNIFICADA com Services"""

    def get(self, request):
        """Retorna dados dos coordenadores usando DashboardService (fonte única)"""

        try:
            # Usar Service centralizado - elimina duplicação de código
            dados = DashboardService.get_coordenadores_por_municipio()

            # Adicionar metadados padronizados
            dados['meta'] = {
                'fonte_dados': 'dashboard_service_unificado',
                'observacao': 'Dados processados via Service Layer - Single Source of Truth',
                'data_atualizacao': timezone.now().isoformat(),
                'arquitetura': 'Usuario fonte única + Services centralizados',
                'performance': 'Otimizado com cache e select_related'
            }

            return self.get_success_response(dados)

        except Exception as e:
            return self.get_error_response(f"Erro ao buscar dados de coordenadores: {str(e)}")