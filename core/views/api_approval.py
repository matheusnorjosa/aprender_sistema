"""
API views para sistema de aprovação avançado com operações em lote.
SEMANA 3 - DIA 2: Sistema de aprovação/rejeição aprimorado
"""

import json

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import (
    Aprovacao,
    AprovacaoStatus,
    LogAuditoria,
    Solicitacao,
    SolicitacaoStatus,
)
from core.services.conflicts import check_conflicts


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.add_aprovacao"), name="dispatch")
class BulkApprovalAPI(View):
    """
    API para aprovação/rejeição em lote de múltiplas solicitações.
    Permite operações eficientes para superintendência.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)

            # Validar dados de entrada
            solicitacao_ids = data.get("solicitacao_ids", [])
            acao = data.get("acao")  # 'aprovar' ou 'reprovar'
            justificativa = data.get("justificativa", "")

            if not solicitacao_ids:
                return JsonResponse(
                    {"success": False, "error": "Nenhuma solicitação selecionada"}
                )

            if acao not in ["aprovar", "reprovar"]:
                return JsonResponse(
                    {
                        "success": False,
                        "error": 'Ação inválida. Use "aprovar" ou "reprovar"',
                    }
                )

            # Processar solicitações
            resultados = []
            erros = []

            with transaction.atomic():
                for sol_id in solicitacao_ids:
                    try:
                        resultado = self._processar_solicitacao(
                            sol_id, acao, justificativa, request.user
                        )
                        resultados.append(resultado)
                    except Exception as e:
                        erros.append({"solicitacao_id": sol_id, "erro": str(e)})

            # Preparar resposta
            total_processadas = len(resultados)
            total_sucesso = len([r for r in resultados if r["success"]])
            total_erro = len(erros)

            return JsonResponse(
                {
                    "success": total_erro == 0,
                    "processadas": total_processadas,
                    "sucessos": total_sucesso,
                    "erros": total_erro,
                    "detalhes": resultados,
                    "erros_detalhes": erros,
                    "mensagem": f"{total_sucesso} solicitações processadas com sucesso"
                    f'{f", {total_erro} com erro" if total_erro > 0 else ""}',
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Dados JSON inválidos"})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})

    def _processar_solicitacao(self, sol_id, acao, justificativa, usuario):
        """Processa uma solicitação individual"""
        try:
            solicitacao = get_object_or_404(Solicitacao, pk=sol_id)

            # Verificar se já foi processada
            if solicitacao.status != SolicitacaoStatus.PENDENTE:
                return {
                    "success": False,
                    "solicitacao_id": sol_id,
                    "titulo": solicitacao.titulo_evento,
                    "erro": "Solicitação já foi processada",
                }

            # Definir status baseado na ação
            if acao == "aprovar":
                novo_status = SolicitacaoStatus.PRE_AGENDA
                decisao = AprovacaoStatus.APROVADO
            else:
                novo_status = SolicitacaoStatus.REPROVADO
                decisao = AprovacaoStatus.REPROVADO

            # Criar aprovação
            aprovacao = Aprovacao.objects.create(
                solicitacao=solicitacao,
                usuario_aprovador=usuario,
                status_decisao=decisao,
                justificativa=justificativa,
            )

            # Atualizar solicitação
            solicitacao.status = novo_status
            solicitacao.usuario_aprovador = usuario
            solicitacao.data_aprovacao_rejeicao = timezone.now()
            solicitacao.save(
                update_fields=["status", "usuario_aprovador", "data_aprovacao_rejeicao"]
            )

            # Registrar auditoria
            LogAuditoria.objects.create(
                usuario=usuario,
                acao=f"RF04: {acao} solicitação (lote)",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Solicitação '{solicitacao.titulo_evento}' — {acao}da em lote"
                f"{f' — justificativa: {justificativa}' if justificativa else ''}",
            )

            # Enviar notificações (SEMANA 3 - DIA 4)
            from core.services.notifications_simplified import (
                notify_solicitacao_approved,
            )

            try:
                if acao == "aprovar":
                    notify_result = notify_solicitacao_approved(solicitacao, usuario)
                    if notify_result["success"]:
                        LogAuditoria.objects.create(
                            usuario=usuario,
                            acao="RF07: Notificações de aprovação enviadas",
                            entidade_afetada_id=solicitacao.id,
                            detalhes=f"Notificações enviadas: {notify_result['notifications_sent']}",
                        )
            except Exception as e:
                # Erro nas notificações não deve interromper o processo
                LogAuditoria.objects.create(
                    usuario=usuario,
                    acao="RF07: Erro em notificações de aprovação",
                    entidade_afetada_id=solicitacao.id,
                    detalhes=f"Erro: {str(e)}",
                )

            return {
                "success": True,
                "solicitacao_id": sol_id,
                "titulo": solicitacao.titulo_evento,
                "novo_status": novo_status,
                "acao": acao,
            }

        except Exception as e:
            # Log do erro
            LogAuditoria.objects.create(
                usuario=usuario,
                acao="RF04: ERRO na aprovação em lote",
                entidade_afetada_id=sol_id,
                detalhes=f"ERRO ao processar {acao}: {str(e)}",
            )
            raise


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.view_aprovacao"), name="dispatch")
class SolicitacoesPendentesAPI(View):
    """
    API para listar solicitações pendentes com filtros avançados e paginação.
    """

    def get(self, request):
        try:
            # Parâmetros de busca e filtro
            termo = request.GET.get("q", "")
            municipio = request.GET.get("municipio", "")
            tipo_evento = request.GET.get("tipo_evento", "")
            formador = request.GET.get("formador", "")
            data_inicio = request.GET.get("data_inicio", "")
            data_fim = request.GET.get("data_fim", "")
            page = int(request.GET.get("page", 1))
            page_size = min(int(request.GET.get("page_size", 20)), 100)  # Max 100

            # Query base
            queryset = (
                Solicitacao.objects.filter(status=SolicitacaoStatus.PENDENTE)
                .select_related(
                    "projeto", "municipio", "tipo_evento", "usuario_solicitante"
                )
                .prefetch_related("formadores")
                .order_by("data_inicio")
            )

            # Aplicar filtros
            if termo:
                queryset = queryset.filter(titulo_evento__icontains=termo)

            if municipio:
                queryset = queryset.filter(municipio_id=municipio)

            if tipo_evento:
                queryset = queryset.filter(tipo_evento_id=tipo_evento)

            if formador:
                queryset = queryset.filter(formadores=formador)

            if data_inicio:
                queryset = queryset.filter(data_inicio__gte=data_inicio)

            if data_fim:
                queryset = queryset.filter(data_inicio__lte=data_fim)

            # Paginação
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            # Serializar dados
            solicitacoes = []
            for sol in page_obj:
                # Verificar conflitos para cada solicitação
                conflitos = check_conflicts(
                    sol.formadores.all(), sol.data_inicio, sol.data_fim, sol.municipio
                )

                has_conflicts = any(
                    [
                        conflitos.get("bloqueios", []),
                        conflitos.get("solicitacoes", []),
                        conflitos.get("deslocamentos", []),
                        conflitos.get("capacidade_diaria", []),
                    ]
                )

                # Verificar conflitos críticos (bloqueios e eventos)
                has_blocking_conflicts = any(
                    [conflitos.get("bloqueios", []), conflitos.get("solicitacoes", [])]
                )

                solicitacoes.append(
                    {
                        "id": str(sol.id),
                        "titulo_evento": sol.titulo_evento,
                        "projeto": sol.projeto.nome if sol.projeto else "",
                        "municipio": sol.municipio.nome if sol.municipio else "",
                        "tipo_evento": sol.tipo_evento.nome if sol.tipo_evento else "",
                        "data_inicio": (
                            sol.data_inicio.isoformat() if sol.data_inicio else None
                        ),
                        "data_fim": sol.data_fim.isoformat() if sol.data_fim else None,
                        "formadores": [f.nome for f in sol.formadores.all()],
                        "usuario_solicitante": (
                            sol.usuario_solicitante.username
                            if sol.usuario_solicitante
                            else ""
                        ),
                        "coordenador_acompanha": sol.coordenador_acompanha,
                        "observacoes": sol.observacoes or "",
                        "has_conflicts": has_conflicts,
                        "has_blocking_conflicts": has_blocking_conflicts,
                        "conflicts_count": sum(
                            [
                                len(conflitos.get("bloqueios", [])),
                                len(conflitos.get("solicitacoes", [])),
                                len(conflitos.get("deslocamentos", [])),
                                len(conflitos.get("capacidade_diaria", [])),
                            ]
                        ),
                    }
                )

            return JsonResponse(
                {
                    "success": True,
                    "solicitacoes": solicitacoes,
                    "pagination": {
                        "current_page": page_obj.number,
                        "total_pages": paginator.num_pages,
                        "total_items": paginator.count,
                        "page_size": page_size,
                        "has_next": page_obj.has_next(),
                        "has_previous": page_obj.has_previous(),
                    },
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Erro ao buscar solicitações: {str(e)}"}
            )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.view_aprovacao"), name="dispatch")
class SolicitacaoConflictsAPI(View):
    """
    API para obter detalhes de conflitos de uma solicitação específica.
    """

    def get(self, request, solicitacao_id):
        try:
            solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

            # Verificar conflitos detalhados
            conflitos = check_conflicts(
                solicitacao.formadores.all(),
                solicitacao.data_inicio,
                solicitacao.data_fim,
                solicitacao.municipio,
            )

            # Formatar detalhes dos conflitos
            conflict_details = []

            # Bloqueios (T/P)
            for bloqueio in conflitos.get("bloqueios", []):
                tipo_codigo = (
                    "T" if bloqueio.tipo_bloqueio.upper() in ["T", "TOTAL"] else "P"
                )
                conflict_details.append(
                    {
                        "type": "bloqueio",
                        "code": tipo_codigo,
                        "severity": "error",
                        "formador": bloqueio.formador.nome,
                        "message": f"[{tipo_codigo}] {bloqueio.formador.nome} bloqueado em {bloqueio.data_bloqueio.strftime('%d/%m')} {bloqueio.hora_inicio.strftime('%H:%M')}-{bloqueio.hora_fim.strftime('%H:%M')}",
                        "observacoes": bloqueio.observacoes,
                    }
                )

            # Eventos confirmados (E)
            for sol_conflito in conflitos.get("solicitacoes", []):
                formadores_nomes = ", ".join(
                    [f.nome for f in sol_conflito.formadores.all()]
                )
                conflict_details.append(
                    {
                        "type": "evento",
                        "code": "E",
                        "severity": "error",
                        "formadores": formadores_nomes,
                        "message": f"[E] Conflito com '{sol_conflito.titulo_evento}' ({sol_conflito.data_inicio.strftime('%d/%m %H:%M')}-{sol_conflito.data_fim.strftime('%d/%m %H:%M')})",
                        "solicitacao_conflito_id": str(sol_conflito.id),
                    }
                )

            # Deslocamentos (D)
            for desl in conflitos.get("deslocamentos", []):
                sol = desl["solicitacao"]
                gap_min = desl["gap_minutes"]
                req_min = desl["required_minutes"]
                conflict_details.append(
                    {
                        "type": "deslocamento",
                        "code": "D",
                        "severity": "warning",
                        "message": f"[D] Buffer insuficiente para {sol.titulo_evento} em {sol.municipio} (gap: {gap_min:.0f}min, necessário: {req_min}min)",
                        "gap_minutes": gap_min,
                        "required_minutes": req_min,
                    }
                )

            # Capacidade diária (M)
            for cap in conflitos.get("capacidade_diaria", []):
                formador = cap["formador"]
                data_formatada = cap["data"].strftime("%d/%m")
                total_horas = cap["total_com_novo"]
                limite = cap["limite_diario"]
                conflict_details.append(
                    {
                        "type": "capacidade",
                        "code": "M",
                        "severity": "warning",
                        "formador": formador.nome,
                        "message": f"[M] {formador.nome} em {data_formatada}: capacidade diária excedida ({total_horas:.1f}h/{limite}h)",
                        "total_horas": total_horas,
                        "limite_diario": limite,
                    }
                )

            has_conflicts = len(conflict_details) > 0
            has_blocking_conflicts = any(
                c["severity"] == "error" for c in conflict_details
            )

            return JsonResponse(
                {
                    "success": True,
                    "solicitacao_id": str(solicitacao.id),
                    "titulo": solicitacao.titulo_evento,
                    "has_conflicts": has_conflicts,
                    "has_blocking_conflicts": has_blocking_conflicts,
                    "conflicts": conflict_details,
                    "total_conflicts": len(conflict_details),
                    "recommendation": self._get_recommendation(
                        has_blocking_conflicts, conflict_details
                    ),
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Erro ao analisar conflitos: {str(e)}"}
            )

    def _get_recommendation(self, has_blocking_conflicts, conflicts):
        """Gera recomendação baseada nos conflitos encontrados"""
        if not conflicts:
            return {
                "action": "approve",
                "message": "✅ Solicitação pode ser aprovada sem restrições",
                "confidence": "high",
            }
        elif has_blocking_conflicts:
            error_count = len([c for c in conflicts if c["severity"] == "error"])
            return {
                "action": "reject",
                "message": f"❌ Rejeição recomendada ({error_count} conflitos críticos)",
                "confidence": "high",
            }
        else:
            warning_count = len([c for c in conflicts if c["severity"] == "warning"])
            return {
                "action": "review",
                "message": f"⚠️ Aprovação com ressalvas ({warning_count} avisos)",
                "confidence": "medium",
            }
