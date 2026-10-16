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

import logging
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.services.compra_elegibilidade import isento_da_regra_da_compra, par_liberado
from apps.core.services.resolvers import resolve_municipio, resolve_projeto, resolve_tipo_evento

from .models import Municipio, Projeto, TipoEvento, Usuario

logger = logging.getLogger(__name__)

# Mesmo teto das listas do criar/editar (`_ExtraParticipantsSerializer`, M10-04).
_MAX_PARTICIPANTES = 200


class _ParticipantsSerializer(serializers.Serializer):
    """F2 (scan 16/10/2026): forma de `participants` antes de qualquer consulta ao banco."""

    coordenador = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    formadores = serializers.ListField(
        child=serializers.EmailField(allow_blank=True), required=False, default=list, max_length=_MAX_PARTICIPANTES
    )
    coord_acompanha = serializers.ListField(
        child=serializers.EmailField(allow_blank=True), required=False, default=list, max_length=_MAX_PARTICIPANTES
    )


class _ValidateSerializer(serializers.Serializer):
    """O corpo tem de ser um objeto; município, projeto, tipo e horários seguem na validação abaixo."""

    participants = _ParticipantsSerializer(required=False)


def _sem_repetir(emails: list[str]) -> list[str]:
    """E-mails não vazios, sem repetição (sem diferença de caixa), na ordem em que vieram."""
    return list(dict.fromkeys(e.strip().lower() for e in emails if e and e.strip()))


def _resolver_emails(emails: list[str]) -> dict[str, int]:
    """Uma consulta para todos os e-mails: `{email: id}` só para os que batem com UMA conta.

    E-mail repetido em duas contas fica de fora (não escolhe no chute, #1658), como no
    `resolve_user_by_email`.
    """
    if not emails:
        return {}
    contas: dict[str, list[int]] = {}
    for email, pk in (
        Usuario.objects.annotate(email_minusculo=Lower("email"))
        .filter(email_minusculo__in=emails)
        .values_list("email_minusculo", "pk")
    ):
        contas.setdefault(email, []).append(pk)
    ambiguos = sum(1 for pks in contas.values() if len(pks) > 1)
    if ambiguos:
        logger.warning("Validate solicitacao: %d e-mail(s) ambíguo(s) — não resolvidos (#1658).", ambiguos)
    return {e: pks[0] for e, pks in contas.items() if len(pks) == 1}


class SolicitationValidateView(APIView):
    """
    POST /api/solicitacoes/validate/
    Valida e canoniza dados de solicitação antes do submit
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        corpo = _ValidateSerializer(data=request.data)
        corpo.is_valid(raise_exception=True)
        data = request.data
        errors = []
        canonical = {}

        # 1. Validar e resolver município
        municipio_input = data.get("municipio")
        if not municipio_input:
            errors.append("Campo 'municipio' é obrigatório")
        else:
            municipio_obj = self._resolve_field(municipio_input, Municipio, resolve_municipio, "município")
            if municipio_obj:
                canonical["municipio_id"] = municipio_obj.id
            else:
                errors.append(f"Município não encontrado: {municipio_input}")

        # 2. Validar e resolver projeto
        projeto_obj: Projeto | None = None
        projeto_input = data.get("projeto")
        if not projeto_input:
            errors.append("Campo 'projeto' é obrigatório")
        else:
            projeto_obj = self._resolve_field(projeto_input, Projeto, resolve_projeto, "projeto")
            if projeto_obj:
                canonical["projeto_id"] = projeto_obj.id
            else:
                errors.append(f"Projeto não encontrado: {projeto_input}")

        # 3. Validar e resolver tipo_evento
        tipo_input = data.get("tipo_evento")
        if not tipo_input:
            errors.append("Campo 'tipo_evento' é obrigatório")
        else:
            tipo_obj = self._resolve_field(tipo_input, TipoEvento, resolve_tipo_evento, "tipo de evento")
            if tipo_obj:
                canonical["tipo_evento_id"] = tipo_obj.id
            else:
                errors.append(f"Tipo de evento não encontrado: {tipo_input}")

        # 3.1 Regra da compra (SSOT `compra_elegibilidade`); isentos: superuser e a capacidade.
        if (
            not isento_da_regra_da_compra(request.user)
            and canonical.get("municipio_id") is not None
            and projeto_obj is not None
            and not par_liberado(canonical["municipio_id"], projeto_obj)
        ):
            errors.append("Município e projeto sem compra que os libere para a solicitação")

        # 4. Validar data/hora
        date_str = data.get("date")
        start_str = data.get("start")
        end_str = data.get("end")

        if not all([date_str, start_str, end_str]):
            errors.append("Campos 'date', 'start' e 'end' são obrigatórios")
        else:
            try:
                # Converter para datetime com timezone America/Fortaleza
                tz = ZoneInfo("America/Fortaleza")

                # Parse date
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                # Parse times
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()

                # Combinar e aplicar timezone
                inicio_naive = datetime.combine(date_obj, start_time)
                fim_naive = datetime.combine(date_obj, end_time)

                inicio_aware = inicio_naive.replace(tzinfo=tz)
                fim_aware = fim_naive.replace(tzinfo=tz)

                # Validar que fim > inicio
                if fim_aware <= inicio_aware:
                    errors.append("Horário de término deve ser posterior ao de início")
                else:
                    canonical["inicio"] = inicio_aware.isoformat()
                    canonical["fim"] = fim_aware.isoformat()

            except ValueError:
                # Security: não expor ``str(e)`` na response — pode propagar
                # detalhes do parsing/stack trace (CodeQL py/stack-trace-exposure).
                # Detalhes completos ficam no log server-side.
                logger.warning("Validate solicitacao: failed to parse data/hora", exc_info=True)
                errors.append("Data ou horário em formato inválido (use YYYY-MM-DD para data e HH:MM para horários)")

        # 5. Validar e resolver participantes (forma já validada pelo serializer: F2)
        participants = corpo.validated_data.get("participants") or {}
        coord_email = (participants.get("coordenador") or "").strip()
        formadores_emails = _sem_repetir(participants.get("formadores", []))
        coord_acomp_emails = _sem_repetir(participants.get("coord_acompanha", []))
        ids_por_email = _resolver_emails(_sem_repetir([coord_email, *formadores_emails, *coord_acomp_emails]))

        usuarios_canonical: dict[str, Any] = {
            "coordenador_id": None,
            "formadores_ids": [],
            "coord_acompanha_ids": [],
            "formadores_not_found": [],
            "coord_acompanha_not_found": [],
        }

        # Coordenador
        if coord_email:
            coord_id = ids_por_email.get(coord_email.lower())
            if coord_id:
                usuarios_canonical["coordenador_id"] = coord_id
            else:
                errors.append(f"Coordenador não encontrado: {coord_email}")

        # Formadores e coordenadores acompanhantes
        for emails, campo_ids, campo_nao_achados in (
            (formadores_emails, "formadores_ids", "formadores_not_found"),
            (coord_acomp_emails, "coord_acompanha_ids", "coord_acompanha_not_found"),
        ):
            for email in emails:
                user_id = ids_por_email.get(email)
                if user_id:
                    usuarios_canonical[campo_ids].append(user_id)
                else:
                    usuarios_canonical[campo_nao_achados].append(email)

        canonical["usuarios"] = usuarios_canonical

        # 6. Resultado final
        ok = len(errors) == 0
        return Response(
            {
                "ok": ok,
                "errors": errors,
                "canonical": canonical if ok else None,
            }
        )

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
        if isinstance(input_value, dict) and "id" in input_value:
            try:
                return model_class.objects.get(id=input_value["id"])
            except model_class.DoesNotExist:
                return None

        # Se é string, usar resolver
        if isinstance(input_value, str):
            return resolver_func(input_value)

        return None
