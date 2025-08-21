# aprender_sistema/core/views_calendar.py
from datetime import date, timedelta
from django.http import JsonResponse, Http404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.models import Formador
from core.services.calendar_codes import marcador_do_dia, gerar_mapa_mensal_otimizado
from django.views.generic import TemplateView

# Import Group-based mixin for calendar access
from core.mixins import CanViewCalendarMixin

class MapaMensalView(LoginRequiredMixin, CanViewCalendarMixin, View):
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

        # Buscar formadores ativos
        formadores = list(Formador.objects.filter(ativo=True).order_by("nome"))
        
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
            "linhas": linhas
        }
        return JsonResponse(payload)
    
# --- Página HTML que consome o endpoint JSON ---
from django.views.generic import TemplateView

class MapaMensalPageView(LoginRequiredMixin, CanViewCalendarMixin, TemplateView):
    template_name = "core/mapa_mensal.html"


class MapaMensalHTMLView(LoginRequiredMixin, CanViewCalendarMixin, TemplateView):
    """
    Página estática que consome a API /mapa-mensal/?ano=YYYY&mes=M
    e renderiza o grid no navegador (HTML+JS).
    """
    template_name = "core/mapa_mensal_view.html"