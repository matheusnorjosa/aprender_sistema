"""
Views relacionadas aos formadores e bloqueios de agenda.
"""

from .base import *


class BloqueioCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "core.add_disponibilidadeformadores"
    template_name = "core/bloqueio_form.html"
    form_class = BloqueioAgendaForm
    success_url = reverse_lazy("bloqueio_ok")

    def form_valid(self, form):
        from core.models import DisponibilidadeFormadores

        formador = form.cleaned_data["formador"]
        inicio = form.cleaned_data["inicio"]
        fim = form.cleaned_data["fim"]
        tipo = form.cleaned_data["tipo"]

        hora_ini = time(0, 0) if tipo == "Total" else time(8, 0)
        hora_fim = time(23, 59) if tipo == "Total" else time(17, 0)

        atual = inicio
        criados = 0
        while atual <= fim:
            obj, created = DisponibilidadeFormadores.objects.get_or_create(
                formador=formador,
                data_bloqueio=atual,
                hora_inicio=hora_ini,
                hora_fim=hora_fim,
                defaults={"tipo_bloqueio": tipo, "motivo": ""},
            )
            if not created:
                obj.tipo_bloqueio = tipo
                obj.save(update_fields=["tipo_bloqueio"])
            else:
                criados += 1
            atual += timedelta(days=1)

        try:
            send_mail(
                "Confirmação de Bloqueio de Agenda",
                (
                    f"Olá, {formador.nome}.\n\n"
                    f"Seu bloqueio foi registrado:\n"
                    f" - Início: {inicio.strftime('%d/%m/%Y')}\n"
                    f" - Fim: {fim.strftime('%d/%m/%Y')}\n"
                    f" - Tipo: {tipo}\n"
                    f"Total de dias afetados: {criados}\n\n"
                    f"Equipe DAT"
                ),
                settings.DEFAULT_FROM_EMAIL,
                [formador.email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(
            self.request, "Bloqueio registrado e e‑mail enviado (console em dev)."
        )
        return super().form_valid(form)


class FormadorEventosView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "core.view_solicitacao"
    template_name = "core/formador_eventos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # MODO ADMIN: Superuser pode ver qualquer formador ou todos os eventos
        if user.is_superuser:
            admin_formador_id = self.request.GET.get("admin_formador_id")
            admin_mode = self.request.GET.get("admin_mode", "geral")

            context["admin_mode"] = True
            context["admin_mode_type"] = admin_mode

            if admin_mode == "formador" and admin_formador_id:
                try:
                    formador = Formador.objects.get(id=admin_formador_id, ativo=True)
                    context["admin_formador_simulado"] = formador
                except Formador.DoesNotExist:
                    formador = None
            else:
                formador = None
                context["formadores_disponiveis"] = Formador.objects.filter(
                    ativo=True
                ).order_by("nome")
        else:
            # MODO NORMAL: Encontrar formador pelo email
            try:
                formador = Formador.objects.get(email=user.email, ativo=True)
            except Formador.DoesNotExist:
                formador = None

        if formador:
            agora = timezone.now()

            # Eventos futuros (aprovados)
            eventos_futuros = (
                Solicitacao.objects.filter(
                    formadores=formador,
                    status=SolicitacaoStatus.APROVADO,
                    data_inicio__gt=agora,
                )
                .select_related(
                    "projeto", "municipio", "tipo_evento", "usuario_solicitante"
                )
                .order_by("data_inicio")
            )

            # Eventos em andamento (aprovados e dentro do período)
            eventos_andamento = (
                Solicitacao.objects.filter(
                    formadores=formador,
                    status=SolicitacaoStatus.APROVADO,
                    data_inicio__lte=agora,
                    data_fim__gte=agora,
                )
                .select_related(
                    "projeto", "municipio", "tipo_evento", "usuario_solicitante"
                )
                .order_by("data_inicio")
            )

            # Eventos passados (últimos 30 dias)
            ultimos_30_dias = agora - timedelta(days=30)
            eventos_passados = (
                Solicitacao.objects.filter(
                    formadores=formador,
                    status=SolicitacaoStatus.APROVADO,
                    data_fim__lt=agora,
                    data_fim__gte=ultimos_30_dias,
                )
                .select_related(
                    "projeto", "municipio", "tipo_evento", "usuario_solicitante"
                )
                .order_by("-data_inicio")
            )

            # Eventos pendentes
            eventos_pendentes = (
                Solicitacao.objects.filter(
                    formadores=formador, status=SolicitacaoStatus.PENDENTE
                )
                .select_related(
                    "projeto", "municipio", "tipo_evento", "usuario_solicitante"
                )
                .order_by("data_inicio")
            )

            todos_eventos = (
                list(eventos_andamento)
                + list(eventos_futuros)
                + list(eventos_pendentes)
                + list(eventos_passados)
            )

            context.update(
                {
                    "formador": formador,
                    "eventos_futuros": eventos_futuros,
                    "eventos_andamento": eventos_andamento,
                    "eventos_passados": eventos_passados,
                    "eventos_pendentes": eventos_pendentes,
                    "todos_eventos": todos_eventos,
                    "total_eventos": len(todos_eventos),
                }
            )
        else:
            if user.is_superuser and context.get("admin_mode"):
                agora = timezone.now()

                total_formadores = Formador.objects.filter(ativo=True).count()
                eventos_admin_sample = (
                    Solicitacao.objects.filter(
                        status=SolicitacaoStatus.APROVADO, data_inicio__gte=agora
                    )
                    .select_related(
                        "projeto", "municipio", "tipo_evento", "usuario_solicitante"
                    )
                    .prefetch_related("formadores")
                    .order_by("data_inicio")[:10]
                )

                context.update(
                    {
                        "formador": None,
                        "eventos_futuros": eventos_admin_sample,
                        "eventos_andamento": [],
                        "eventos_passados": [],
                        "eventos_pendentes": [],
                        "todos_eventos": list(eventos_admin_sample),
                        "total_eventos": eventos_admin_sample.count(),
                        "total_formadores": total_formadores,
                        "admin_message": f"Modo Admin: Visualizando dados gerais. {total_formadores} formadores disponíveis.",
                    }
                )
            else:
                context.update(
                    {
                        "formador": None,
                        "eventos_futuros": [],
                        "eventos_andamento": [],
                        "eventos_passados": [],
                        "eventos_pendentes": [],
                        "todos_eventos": [],
                        "total_eventos": 0,
                        "erro": "Formador não encontrado. Verifique se seu email está registrado no sistema.",
                    }
                )

        return context
