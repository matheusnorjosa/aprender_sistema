"""
Formador Metrics Views - §9 Epic #459

Formadores ranking and performance metrics.
Extracted from views_metrics.py.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.models import Usuario
from apps.core.permissions import HasPerm
from apps.core.services.horas_formacao import horas_formacao, ocupacoes_aprovadas


def eventos_e_municipios_por_pessoa(*, de: date, ate: date) -> dict[int, tuple[int, int]]:
    """pessoa → (eventos, municípios distintos) aprovados no período, com a população da CH.

    Formador e COORD_ACOMPANHA sempre; o responsável (`coordenador`; sem ele, quem criou) só quando
    acompanha (decisão do dono, 04/11/2026). A mesma pessoa conta uma vez por evento.
    """
    eventos: dict[int, int] = defaultdict(int)
    municipios: dict[int, set[int]] = defaultdict(set)
    for (uid, _sol_id), ocupacao in ocupacoes_aprovadas(de=de, ate=ate).items():
        eventos[uid] += 1
        if ocupacao.municipio_id is not None:
            municipios[uid].add(ocupacao.municipio_id)
    return {uid: (n, len(municipios[uid])) for uid, n in eventos.items()}


@api_view(["GET"])
@permission_classes(
    # Onda 2 A3 (β, 2026-04-27): adicionado `manage_admin_registries` para DAT
    # como ator transversal (validar/suportar). Mesma decisão dos demais
    # endpoints metrics — preserva Lote 4.2.b2 (composition OR ad-hoc por
    # objetos semanticamente diferentes). Ver ADR-019 (v2/docs/adr/ADR-019-metrics-composition-or.md).
    [HasPerm("run_daily_operations") | HasPerm("supervise_operations") | HasPerm("manage_admin_registries")]
)
@throttle_classes([ScopedRateThrottle])
def formadores_metrics(request: Request) -> Response:
    """
    Formadores ranking by performance (top 10) (Issue #189).

    Query params:
        days (int): Number of days to look back (default: 30)

    Returns:
        {
            "period": "30d",
            "formadores": [
                {
                    "id": 1,
                    "nome": "João Silva",
                    "eventos": 45,
                    "horas_trabalhadas": 180.0,
                    "municipios_atendidos": 12
                },
                ...
            ]
        }

    Calculations:
        - Pessoas e eventos = a população da CH (`ocupacoes_aprovadas`): FORMADOR e COORD_ACOMPANHA
          sempre, o coordenador responsável só quando acompanha (04/11/2026); eventos aprovados com
          início nos últimos `days` dias locais, hoje incluído
        - Aggregate by pessoa: count distinct events (dois papéis no mesmo evento = 1), count
          distinct municipios
        - horas_trabalhadas: services/horas_formacao.py (teto por evento, mesma conta da
          Grade Mensal)
        - Order by -eventos, limit to top 10

    Permissions: HasPerm("run_daily_operations") | HasPerm("supervise_operations") (only authorized users)
    """
    days = int(request.GET.get("days", 30))
    # Período = os `days` dias locais [hoje − (days − 1), hoje], pelo INÍCIO do evento (antes filtrava
    # `created_at`, e um evento antigo importado hoje entrava como hora do período).
    ate = timezone.localdate()
    de = ate - timedelta(days=days - 1)

    contagens = eventos_e_municipios_por_pessoa(de=de, ate=ate)
    top = sorted(contagens, key=lambda uid: (-contagens[uid][0], uid))[:10]

    # Nome e horas dos 10 em consultas fixas, sem N+1 (#781). Horas = a contagem única de horas de
    # formação (teto por evento), a mesma da Grade Mensal.
    nomes = {u.pk: u for u in Usuario.objects.filter(pk__in=top).only("id", "first_name", "last_name")}
    horas_por_pessoa = horas_formacao(top, de=de, ate=ate)

    formadores_list = []
    for uid in top:
        eventos, municipios_atendidos = contagens[uid]
        # 2 casas, como `ch_month`/`ch_year` da Grade Mensal: os dois mostram o mesmo número.
        horas = round(horas_por_pessoa[uid].total, 2)

        # Nome, ou "Usuario #id" como `str(usuario)`: nunca o login (CPF)
        nome = f"{nomes[uid].first_name} {nomes[uid].last_name}".strip()
        if not nome:
            nome = f"Usuario #{uid}"

        formadores_list.append(
            {
                "id": uid,
                "nome": nome,
                "eventos": eventos,
                "horas_trabalhadas": horas,
                "municipios_atendidos": municipios_atendidos,
            }
        )

    return Response(
        {"period": f"{days}d", "formadores": formadores_list},
        status=http_status.HTTP_200_OK,
    )


# Throttle scope for formadores_metrics (#409)
formadores_metrics.throttle_scope = "metrics"  # type: ignore[attr-defined]
