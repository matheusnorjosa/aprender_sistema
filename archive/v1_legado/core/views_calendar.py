# aprender_sistema/core/views_calendar.py
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.views import View
from django.views.generic import TemplateView

# Import Group-based mixin for calendar access
from core.mixins import CanViewCalendarMixin, SuperintendenciaSetorRequiredMixin
from core.services import FormadorService, get_pessoas_super_qs
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

        # Buscar pessoas (formadores + coordenadores) da superintendência
        # HOTFIX 06/10: Usa serviço unificado com fallback temporário
        # Mostra todos enquanto completa backfill de setores
        formadores = list(
            get_pessoas_super_qs(strict_super=True).order_by("first_name", "last_name")
        )

        # Usar função otimizada para gerar todo o mapa de uma vez
        mapa_otimizado = gerar_mapa_mensal_otimizado(formadores, dias)

        linhas = []
        for f in formadores:
            linha = {
                "formador_id": str(f.id),
                "formador": f.nome_completo,
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


class MapaMensalPageView(
    LoginRequiredMixin, SuperintendenciaSetorRequiredMixin, TemplateView
):
    template_name = "core/mapa_mensal.html"


class MapaMensalHTMLView(LoginRequiredMixin, CanViewCalendarMixin, TemplateView):
    """
    Página estática que consome a API /mapa-mensal/?ano=YYYY&mes=M
    e renderiza o grid no navegador (HTML+JS).
    """

    template_name = "core/mapa_mensal_view.html"


class FormadoresSuperintendenciaView(
    LoginRequiredMixin, SuperintendenciaSetorRequiredMixin, View
):
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
            user_setor = getattr(user, "setor", None)
            logger.info(f"User setor: {user_setor}")

            # HOTFIX 06/10: Pessoas da superintendência (formadores + coordenadores)
            # Usa serviço unificado com fallback temporário
            logger.info("Loading superintendencia pessoas (formadores + coordenadores)")
            formadores = (
                get_pessoas_super_qs(strict_super=True)
                .select_related("setor", "area_atuacao")
                .order_by("first_name", "last_name")
            )

            logger.info(f"Found {formadores.count()} formadores")

            formadores_data = []
            for f in formadores:
                try:
                    # Garantir que todos os campos sejam serializáveis
                    setor_nome = f.setor.nome if f.setor else "Sem setor"

                    formador_data = {
                        "id": str(f.id),
                        "nome": f.nome_completo,
                        "email": f.email if f.email else "",
                        "area": str(f.area_atuacao) if f.area_atuacao else "",
                        "status": "Ativo" if f.is_active else "Inativo",
                        "setor": setor_nome,
                    }
                    formadores_data.append(formador_data)
                    logger.debug(f"Added formador: {f.nome_completo}")
                except Exception as fe:
                    logger.error(f"Error processing formador {f.id}: {fe}")
                    import traceback

                    logger.error(
                        f"Traceback for formador error: {traceback.format_exc()}"
                    )
                    continue

            logger.info(f"Returning {len(formadores_data)} formadores")
            return JsonResponse(
                {
                    "success": True,
                    "formadores": formadores_data,
                    "total": len(formadores_data),
                }
            )

        except Exception as e:
            logger.error(f"FormadoresSuperintendenciaView error: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)
