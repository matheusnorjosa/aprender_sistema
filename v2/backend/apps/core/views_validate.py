"""
PR16: Validação Canônica de Solicitações

Endpoint: POST /api/solicitacoes/validate/
Payload:
{
  "municipio": "Fortaleza" ou {id: 1},
  "projeto": "ACerta" ou {id: 2},
  "tipo_evento": "Formação" ou {id: 3},
  "date": "2025-01-15",
  "start": "09:00",
  "end": "12:00",
  "participants": {
    "coordenador": "coord@example.com",
    "formadores": ["form1@example.com", "form2@example.com"],
    "coord_acompanha": ["acomp@example.com"]
  }
}

Retorna:
{
  "ok": true|false,
  "errors": [...],
  "canonical": {
    "municipio_id": 1,
    "projeto_id": 2,
    "tipo_evento_id": 3,
    "inicio": "2025-01-15T09:00:00-03:00",
    "fim": "2025-01-15T12:00:00-03:00",
    "usuarios": {
      "coordenador_id": 10,
      "formadores_ids": [11, 12],
      "coord_acompanha_ids": [13],
      "formadores_not_found": [],
      "coord_acompanha_not_found": []
    }
  }
}
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

from datetime import datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import pytz

from .models import Municipio, Projeto, TipoEvento
from apps.core.services.resolvers import (
    resolve_municipio,
    resolve_projeto,
    resolve_tipo_evento,
    resolve_user_by_email,
)


class SolicitationValidateView(APIView):
    """
    POST /api/solicitacoes/validate/
    Valida e canoniza dados de solicitação antes do submit
    """
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        data = request.data
        errors = []
        canonical = {}

        # 1. Validar e resolver município
        municipio_input = data.get('municipio')
        if not municipio_input:
            errors.append("Campo 'municipio' é obrigatório")
        else:
            municipio_obj = self._resolve_field(
                municipio_input,
                Municipio,
                resolve_municipio,
                "município"
            )
            if municipio_obj:
                canonical['municipio_id'] = municipio_obj.id
            else:
                errors.append(f"Município não encontrado: {municipio_input}")

        # 2. Validar e resolver projeto
        projeto_input = data.get('projeto')
        if not projeto_input:
            errors.append("Campo 'projeto' é obrigatório")
        else:
            projeto_obj = self._resolve_field(
                projeto_input,
                Projeto,
                resolve_projeto,
                "projeto"
            )
            if projeto_obj:
                canonical['projeto_id'] = projeto_obj.id
            else:
                errors.append(f"Projeto não encontrado: {projeto_input}")

        # 3. Validar e resolver tipo_evento
        tipo_input = data.get('tipo_evento')
        if not tipo_input:
            errors.append("Campo 'tipo_evento' é obrigatório")
        else:
            tipo_obj = self._resolve_field(
                tipo_input,
                TipoEvento,
                resolve_tipo_evento,
                "tipo de evento"
            )
            if tipo_obj:
                canonical['tipo_evento_id'] = tipo_obj.id
            else:
                errors.append(f"Tipo de evento não encontrado: {tipo_input}")

        # 4. Validar data/hora
        date_str = data.get('date')
        start_str = data.get('start')
        end_str = data.get('end')

        if not all([date_str, start_str, end_str]):
            errors.append("Campos 'date', 'start' e 'end' são obrigatórios")
        else:
            try:
                # Converter para datetime com timezone America/Fortaleza
                tz = pytz.timezone('America/Fortaleza')

                # Parse date
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Parse times
                start_time = datetime.strptime(start_str, '%H:%M').time()
                end_time = datetime.strptime(end_str, '%H:%M').time()

                # Combinar e aplicar timezone
                inicio_naive = datetime.combine(date_obj, start_time)
                fim_naive = datetime.combine(date_obj, end_time)

                inicio_aware = tz.localize(inicio_naive)
                fim_aware = tz.localize(fim_naive)

                # Validar que fim > inicio
                if fim_aware <= inicio_aware:
                    errors.append("Horário de término deve ser posterior ao de início")
                else:
                    canonical['inicio'] = inicio_aware.isoformat()
                    canonical['fim'] = fim_aware.isoformat()

            except ValueError as e:
                errors.append(f"Erro ao processar data/hora: {str(e)}")

        # 5. Validar e resolver participantes
        participants = data.get('participants', {})
        usuarios_canonical = {
            'coordenador_id': None,
            'formadores_ids': [],
            'coord_acompanha_ids': [],
            'formadores_not_found': [],
            'coord_acompanha_not_found': [],
        }

        # Coordenador
        coord_email = participants.get('coordenador')
        if coord_email:
            coord_user = resolve_user_by_email(coord_email)
            if coord_user:
                usuarios_canonical['coordenador_id'] = coord_user.id
            else:
                errors.append(f"Coordenador não encontrado: {coord_email}")

        # Formadores
        formadores_emails = participants.get('formadores', [])
        for email in formadores_emails:
            if email:
                user = resolve_user_by_email(email)
                if user:
                    usuarios_canonical['formadores_ids'].append(user.id)
                else:
                    usuarios_canonical['formadores_not_found'].append(email)

        # Coordenadores acompanhantes
        coord_acomp_emails = participants.get('coord_acompanha', [])
        for email in coord_acomp_emails:
            if email:
                user = resolve_user_by_email(email)
                if user:
                    usuarios_canonical['coord_acompanha_ids'].append(user.id)
                else:
                    usuarios_canonical['coord_acompanha_not_found'].append(email)

        canonical['usuarios'] = usuarios_canonical

        # 6. Resultado final
        ok = len(errors) == 0
        return Response({
            'ok': ok,
            'errors': errors,
            'canonical': canonical if ok else None,
        })

    def _resolve_field(self, input_value, model_class, resolver_func, field_name):
        """
        Resolve campo que pode ser {id: ...} ou string

        Args:
            input_value: Valor de entrada (dict com id ou string)
            model_class: Classe do modelo Django
            resolver_func: Função de resolver por nome
            field_name: Nome do campo para mensagens de erro

        Returns:
            Objeto do modelo ou None
        """
        # Se é dict com id, buscar direto no banco
        if isinstance(input_value, dict) and 'id' in input_value:
            try:
                return model_class.objects.get(id=input_value['id'])
            except model_class.DoesNotExist:
                return None

        # Se é string, usar resolver
        if isinstance(input_value, str):
            return resolver_func(input_value)

        return None
