from functools import wraps

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def require_groups(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_groups = set(request.user.groups.values_list("name", flat=True))
            allowed_groups = set(group_names)

            if not user_groups.intersection(allowed_groups):
                return JsonResponse(
                    {
                        "error": "Forbidden",
                        "detail": f"Acesso permitido apenas para grupos: {', '.join(allowed_groups)}",
                    },
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


@login_required
@require_groups("controle", "coordenador", "superintendencia")
def conflitos(request):
    """
    GET /api/reports/conflitos?limit=200
    Retorna pares de eventos em conflito com contexto completo.
    """
    limit = int(request.GET.get("limit", 200))

    sql = """
    WITH base AS (
      SELECT sf1.usuario_id,
             LEAST(s1.id, s2.id) AS ev_a,
             GREATEST(s1.id, s2.id) AS ev_b,
             s1.data_inicio AS a_ini, s1.data_fim AS a_fim,
             s2.data_inicio AS b_ini, s2.data_fim AS b_fim
      FROM core_solicitacao s1
      JOIN core_formadoressolicitacao sf1 ON sf1.solicitacao_id = s1.id
      JOIN core_solicitacao s2 ON s2.id <> s1.id
      JOIN core_formadoressolicitacao sf2 ON sf2.solicitacao_id = s2.id
        AND sf2.usuario_id = sf1.usuario_id
      WHERE tstzrange(s1.data_inicio, s1.data_fim) && tstzrange(s2.data_inicio, s2.data_fim)
    )
    SELECT b.usuario_id,
           a.id AS ev_a, a.titulo_evento AS ev_a_titulo,
           a.data_inicio AS ev_a_ini, a.data_fim AS ev_a_fim,
           m1.nome AS ev_a_municipio, te1.nome AS ev_a_tipo,
           c.id AS ev_b, c.titulo_evento AS ev_b_titulo,
           c.data_inicio AS ev_b_ini, c.data_fim AS ev_b_fim,
           m2.nome AS ev_b_municipio, te2.nome AS ev_b_tipo
    FROM base b
    JOIN core_solicitacao a ON a.id = b.ev_a
    LEFT JOIN core_municipio m1 ON m1.id = a.municipio_id
    LEFT JOIN core_tipoevento te1 ON te1.id = a.tipo_evento_id
    JOIN core_solicitacao c ON c.id = b.ev_b
    LEFT JOIN core_municipio m2 ON m2.id = c.municipio_id
    LEFT JOIN core_tipoevento te2 ON te2.id = c.tipo_evento_id
    ORDER BY b.usuario_id, ev_a, ev_b
    LIMIT %s
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [limit])
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return JsonResponse(
        {"count": len(rows), "limit": limit, "results": rows},
        json_dumps_params={"indent": 2, "default": str},
    )


@login_required
@require_groups("controle", "coordenador", "superintendencia")
def workload(request):
    """
    GET /api/reports/workload?from=YYYY-MM&to=YYYY-MM
    Retorna carga horária mensal por usuário no período especificado.
    """
    from_month = request.GET.get("from")
    to_month = request.GET.get("to")

    if not from_month or not to_month:
        return JsonResponse(
            {
                "error": "Bad Request",
                "detail": "Parâmetros obrigatórios: from (YYYY-MM) e to (YYYY-MM)",
            },
            status=400,
        )

    sql = """
    SELECT
      sf.usuario_id,
      TO_CHAR(s.data_inicio, 'YYYY-MM') AS mes,
      SUM(EXTRACT(EPOCH FROM (s.data_fim - s.data_inicio)) / 3600.0) AS ch
    FROM core_solicitacao s
    JOIN core_formadoressolicitacao sf ON sf.solicitacao_id = s.id
    WHERE TO_CHAR(s.data_inicio, 'YYYY-MM') BETWEEN %s AND %s
    GROUP BY sf.usuario_id, TO_CHAR(s.data_inicio, 'YYYY-MM')
    ORDER BY ch DESC, mes DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [from_month, to_month])
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return JsonResponse(
        {
            "count": len(rows),
            "period": {"from": from_month, "to": to_month},
            "results": rows,
        },
        json_dumps_params={"indent": 2, "default": str},
    )


@login_required
@require_groups("controle", "coordenador", "superintendencia")
@require_GET
def kpis(request):
    """
    GET /api/reports/kpis
    Retorna KPIs executivos do sistema.
    """
    with connection.cursor() as cur:
        # Total de solicitações
        cur.execute("SELECT COUNT(*) FROM core_solicitacao")
        total = cur.fetchone()[0]

        # Por status
        cur.execute("SELECT status, COUNT(*) FROM core_solicitacao GROUP BY 1")
        by_status_rows = cur.fetchall()
        by_status = {str(k): int(v) for k, v in by_status_rows}

        # Conflitos (pares únicos)
        cur.execute(
            """
            WITH pairs AS (
              SELECT DISTINCT LEAST(s1.id,s2.id) a, GREATEST(s1.id,s2.id) b
              FROM core_solicitacao s1
              JOIN core_solicitacao s2 ON s2.id<>s1.id
               AND tstzrange(s1.data_inicio,s1.data_fim) && tstzrange(s2.data_inicio,s2.data_fim)
              JOIN core_formadoressolicitacao f1 ON f1.solicitacao_id=s1.id
              JOIN core_formadoressolicitacao f2 ON f2.solicitacao_id=s2.id AND f2.usuario_id=f1.usuario_id
            )
            SELECT COUNT(*) FROM pairs
        """
        )
        conflitos = cur.fetchone()[0]

        # Overload (>=110h/mês últimos 3 meses)
        cur.execute(
            """
            WITH h AS (
              SELECT sf.usuario_id,
                     date_trunc('month', s.data_inicio) AS mes,
                     SUM(EXTRACT(EPOCH FROM (s.data_fim-s.data_inicio))/3600.0) AS ch
              FROM core_solicitacao s
              JOIN core_formadoressolicitacao sf ON sf.solicitacao_id=s.id
              GROUP BY 1,2
            )
            SELECT COUNT(*) FROM (
              SELECT usuario_id FROM h
              WHERE mes >= date_trunc('month', now()) - interval '2 month'
                AND ch >= 110
              GROUP BY usuario_id
            ) q
        """
        )
        overload_users = cur.fetchone()[0]

        # Dimensionais
        def count(table):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]

        usuarios = count("core_usuario")
        municipios = count("core_municipio")
        projetos = count("core_projeto")

        # Disponibilidades staging (se existir)
        disp_staging = 0
        try:
            cur.execute("SELECT COUNT(*) FROM ingestao_disp_staging")
            disp_staging = cur.fetchone()[0]
        except Exception:
            pass

    return JsonResponse(
        {
            "total_solicitacoes": total,
            "by_status": by_status,
            "conflitos_total": conflitos,
            "overload_users": overload_users,
            "usuarios_total": usuarios,
            "municipios_total": municipios,
            "projetos_total": projetos,
            "disp_staging_total": disp_staging,
        }
    )


@login_required
@require_groups("controle", "coordenador", "superintendencia")
@require_GET
def series(request):
    """
    GET /api/reports/series?from=YYYY-MM&to=YYYY-MM
    Retorna séries temporais de solicitações por status.
    """
    from_param = request.GET.get("from")  # YYYY-MM
    to_param = request.GET.get("to")  # YYYY-MM

    if not from_param or not to_param:
        return JsonResponse({"error": "missing from/to (YYYY-MM)"}, status=400)

    with connection.cursor() as cur:
        cur.execute(
            """
          SELECT to_char(date_trunc('month', s.data_inicio),'YYYY-MM') AS mes,
                 status,
                 COUNT(*)
          FROM core_solicitacao s
          WHERE date_trunc('month', s.data_inicio) BETWEEN to_date(%s,'YYYY-MM') AND to_date(%s,'YYYY-MM')
          GROUP BY 1,2
          ORDER BY 1 ASC
        """,
            [from_param, to_param],
        )
        rows = cur.fetchall()

    # Pivot leve
    out = {}
    for mes, status, cnt in rows:
        out.setdefault(mes, {})[str(status)] = int(cnt)

    series_data = [{"mes": mes, **vals} for mes, vals in sorted(out.items())]

    return JsonResponse({"count": len(series_data), "results": series_data})
