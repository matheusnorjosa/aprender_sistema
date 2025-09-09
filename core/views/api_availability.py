"""
API views para verificação de disponibilidade em tempo real.
SEMANA 3 - DIA 1: Interface de solicitação aprimorada
"""

import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import Formador, Municipio
from core.services.availability_service import DisponibilidadeEngine
from core.services.conflicts import check_conflicts


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
class CheckAvailabilityAPI(View):
    """
    API endpoint para verificação em tempo real de disponibilidade dos formadores.

    Retorna informações detalhadas sobre conflitos, com códigos E,M,D,P,T,X
    conforme as regras RD-01 a RD-08.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)

            # Validar dados de entrada
            formador_ids = data.get("formadores", [])
            data_inicio_str = data.get("data_inicio", "")
            data_fim_str = data.get("data_fim", "")
            municipio_id = data.get("municipio", None)

            # Validações básicas
            if not formador_ids:
                return JsonResponse(
                    {"success": False, "error": "Formadores devem ser selecionados"}
                )

            if not data_inicio_str or not data_fim_str:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Datas de início e fim são obrigatórias",
                    }
                )

            # Parsear datas
            try:
                data_inicio = parse_datetime(data_inicio_str)
                data_fim = parse_datetime(data_fim_str)

                if not data_inicio or not data_fim:
                    raise ValueError("Formato de data inválido")

                # Garantir timezone awareness
                if timezone.is_naive(data_inicio):
                    data_inicio = timezone.make_aware(data_inicio)
                if timezone.is_naive(data_fim):
                    data_fim = timezone.make_aware(data_fim)

            except ValueError as e:
                return JsonResponse(
                    {"success": False, "error": f"Erro ao processar datas: {str(e)}"}
                )

            # Validar ordem das datas
            if data_fim <= data_inicio:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Data de fim deve ser posterior à data de início",
                    }
                )

            # Buscar formadores e município
            try:
                formadores = Formador.objects.filter(id__in=formador_ids, ativo=True)

                if len(formadores) != len(formador_ids):
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "Alguns formadores não foram encontrados",
                        }
                    )

                municipio = None
                if municipio_id:
                    municipio = Municipio.objects.get(id=municipio_id)

            except Exception as e:
                return JsonResponse(
                    {"success": False, "error": f"Erro ao buscar dados: {str(e)}"}
                )

            # Verificar conflitos usando o sistema implementado
            conflitos = check_conflicts(formadores, data_inicio, data_fim, municipio)

            # Processar resultados
            has_conflicts = any(
                [
                    conflitos.get("bloqueios", []),
                    conflitos.get("solicitacoes", []),
                    conflitos.get("deslocamentos", []),
                    conflitos.get("capacidade_diaria", []),
                ]
            )

            # Formatar mensagens de conflito seguindo RD-08
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
                        "formador": bloqueio.formador.nome,
                        "message": f"[{tipo_codigo}] {bloqueio.formador.nome} bloqueado em {bloqueio.data_bloqueio.strftime('%d/%m')} {bloqueio.hora_inicio.strftime('%H:%M')}-{bloqueio.hora_fim.strftime('%H:%M')}",
                        "severity": "error",
                    }
                )

            # Eventos confirmados (E)
            for solicitacao in conflitos.get("solicitacoes", []):
                formadores_nomes = ", ".join(
                    [f.nome for f in solicitacao.formadores.all()]
                )
                conflict_details.append(
                    {
                        "type": "evento",
                        "code": "E",
                        "formadores": formadores_nomes,
                        "message": f"[E] Conflito com '{solicitacao.titulo_evento}' ({solicitacao.data_inicio.strftime('%d/%m %H:%M')}-{solicitacao.data_fim.strftime('%d/%m %H:%M')})",
                        "severity": "error",
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
                        "message": f"[D] Buffer insuficiente para {sol.titulo_evento} em {sol.municipio} (gap: {gap_min:.0f}min, necessário: {req_min}min)",
                        "severity": "warning",
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
                        "formador": formador.nome,
                        "message": f"[M] {formador.nome} em {data_formatada}: capacidade diária excedida ({total_horas:.1f}h/{limite}h)",
                        "severity": "warning",
                    }
                )

            # Resposta da API
            return JsonResponse(
                {
                    "success": True,
                    "available": not has_conflicts,
                    "conflicts": conflict_details,
                    "formadores_verificados": [f.nome for f in formadores],
                    "periodo": f"{data_inicio.strftime('%d/%m/%Y %H:%M')} - {data_fim.strftime('%d/%m/%Y %H:%M')}",
                    "municipio": municipio.nome if municipio else "Não informado",
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Dados JSON inválidos"})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})


@method_decorator(login_required, name="dispatch")
class FormadorDetailsAPI(View):
    """
    API para obter detalhes de formadores selecionados.
    Usado para exibir informações contextuais na interface.
    """

    def get(self, request):
        formador_ids = request.GET.getlist("ids[]")

        if not formador_ids:
            return JsonResponse(
                {"success": False, "error": "IDs de formadores não fornecidos"}
            )

        try:
            formadores = Formador.objects.filter(
                id__in=formador_ids, ativo=True
            ).values("id", "nome", "email", "ativo")

            return JsonResponse({"success": True, "formadores": list(formadores)})

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Erro ao buscar formadores: {str(e)}"}
            )


@method_decorator(login_required, name="dispatch")
class FormadoresSuperintendenciaAPI(View):
    """
    API para obter lista de formadores vinculados à superintendência.
    Usado no dropdown da interface de disponibilidade.
    """

    def get(self, request):
        try:
            # Buscar grupo superintendencia
            try:
                grupo_super = Group.objects.get(name="superintendencia")
            except Group.DoesNotExist:
                return JsonResponse({
                    "success": False, 
                    "error": "Grupo superintendência não encontrado"
                })

            # Buscar formadores vinculados ao grupo superintendencia via usuario
            formadores = Formador.objects.filter(
                usuario__groups=grupo_super,
                ativo=True
            ).select_related('usuario').order_by('nome')

            # Preparar dados de resposta
            formadores_data = []
            for formador in formadores:
                formadores_data.append({
                    "id": str(formador.id),
                    "nome": formador.nome,
                    "email": formador.email,
                    "area_atuacao": formador.area_atuacao.name if formador.area_atuacao else None,
                    "usuario_ativo": formador.usuario.is_active if formador.usuario else False
                })

            return JsonResponse({
                "success": True,
                "formadores": formadores_data,
                "total": len(formadores_data)
            })

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Erro interno: {str(e)}"}
            )
