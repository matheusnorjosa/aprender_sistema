# aprender_sistema/core/views_calendar.py
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.views import View
from django.views.generic import TemplateView

# Import Group-based mixin for calendar access
from core.mixins import CanViewCalendarMixin, SuperintendenciaSetorRequiredMixin
from core.models import Formador
from core.services.calendar_codes import gerar_mapa_mensal_otimizado, marcador_do_dia


class MapaMensalView(LoginRequiredMixin, SuperintendenciaSetorRequiredMixin, View):
    def get(self, request):
        try:
            ano = int(request.GET.get("ano"))
            mes = int(request.GET.get("mes"))
        except (TypeError, ValueError):
            raise Http404("Parâmetros ano/mes inválidos")

        d0 = date(ano, mes, 1)
        d1 = date(ano + (mes // 12), ((mes % 12) + 1), 1)
        dias = []
        d = d0
        while d < d1:
            dias.append(d)
            d += timedelta(days=1)

        # Buscar formadores ativos filtrados por superintendência
        user = request.user
        user_setor = getattr(user, 'setor', None)
        
        if user.is_superuser:
            # Superuser vê todos os formadores
            formadores = list(Formador.objects.filter(ativo=True).order_by("nome"))
        elif user_setor and getattr(user_setor, 'vinculado_superintendencia', False):
            # Superintendência vê formadores vinculados:
            # 1. Formadores com email @planilha.super (importados da aba Super)
            # 2. Formadores com usuários vinculados à superintendência
            from django.db.models import Q
            formadores = list(Formador.objects.filter(
                Q(ativo=True) & (
                    Q(email__endswith='@planilha.super') |
                    Q(usuario__setor__vinculado_superintendencia=True)
                )
            ).order_by("nome"))
        else:
            # Outros setores veem apenas formadores do mesmo setor
            formadores = list(Formador.objects.filter(ativo=True, usuario__setor=user_setor).order_by("nome"))

        # Usar função otimizada para gerar todo o mapa de uma vez
        mapa_otimizado = gerar_mapa_mensal_otimizado(formadores, dias)

        linhas = []
        for f in formadores:
            linha = {
                "formador_id": str(f.id),
                "formador": f.nome,
                "celulas": mapa_otimizado.get(f.id, ["-"] * len(dias)),
            }
            linhas.append(linha)

        payload = {
            "ano": ano,
            "mes": mes,
            "dias": [x.day for x in dias],
            "linhas": linhas,
        }
        return JsonResponse(payload)


# --- Página HTML que consome o endpoint JSON ---
from django.views.generic import TemplateView


class MapaMensalPageView(LoginRequiredMixin, SuperintendenciaSetorRequiredMixin, TemplateView):
    template_name = "core/mapa_mensal.html"


class MapaMensalHTMLView(LoginRequiredMixin, CanViewCalendarMixin, TemplateView):
    """
    Página estática que consome a API /mapa-mensal/?ano=YYYY&mes=M
    e renderiza o grid no navegador (HTML+JS).
    """

    template_name = "core/mapa_mensal_view.html"


class FormadoresSuperintendenciaView(LoginRequiredMixin, SuperintendenciaSetorRequiredMixin, View):
    """
    API para buscar formadores filtrados por superintendência
    Usado pelo dropdown na página de disponibilidade
    """

    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"FormadoresSuperintendenciaView - User: {request.user}")
            user = request.user
            user_setor = getattr(user, 'setor', None)
            logger.info(f"User setor: {user_setor}")
            
            if user.is_superuser:
                # Superuser vê todos os formadores
                logger.info("User is superuser - loading all formadores")
                formadores = Formador.objects.filter(ativo=True).order_by("nome")
            elif user_setor and getattr(user_setor, 'vinculado_superintendencia', False):
                # Superintendência vê formadores vinculados:
                # 1. Formadores com email @planilha.super (importados da aba Super)
                # 2. Formadores com usuários vinculados à superintendência
                logger.info("User from superintendencia - loading superintendencia formadores")
                from django.db.models import Q
                formadores = Formador.objects.filter(
                    Q(ativo=True) & (
                        Q(email__endswith='@planilha.super') |
                        Q(usuario__setor__vinculado_superintendencia=True)
                    )
                ).order_by("nome")
            else:
                # Outros setores veem apenas formadores do mesmo setor
                logger.info("User from other sector - loading sector formadores")
                formadores = Formador.objects.filter(ativo=True, usuario__setor=user_setor).order_by("nome")
            
            logger.info(f"Found {formadores.count()} formadores")
            
            formadores_data = []
            for f in formadores:
                try:
                    # Garantir que todos os campos sejam serializáveis
                    setor_nome = 'Sem setor'
                    if f.usuario and hasattr(f.usuario, 'setor') and f.usuario.setor:
                        setor_nome = str(f.usuario.setor.nome) if hasattr(f.usuario.setor, 'nome') else 'Sem setor'
                    
                    formador_data = {
                        'id': str(f.id),
                        'nome': str(f.nome),
                        'email': str(f.email) if f.email else '',
                        'area': str(f.area_atuacao) if f.area_atuacao else '',
                        'status': 'Ativo' if f.ativo else 'Inativo',
                        'setor': setor_nome
                    }
                    formadores_data.append(formador_data)
                    logger.debug(f"Added formador: {f.nome}")
                except Exception as fe:
                    logger.error(f"Error processing formador {f.id} {f.nome}: {fe}")
                    import traceback
                    logger.error(f"Traceback for formador error: {traceback.format_exc()}")
                    continue
            
            logger.info(f"Returning {len(formadores_data)} formadores")
            return JsonResponse({
                'success': True,
                'formadores': formadores_data,
                'total': len(formadores_data)
            })
            
        except Exception as e:
            logger.error(f"FormadoresSuperintendenciaView error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
