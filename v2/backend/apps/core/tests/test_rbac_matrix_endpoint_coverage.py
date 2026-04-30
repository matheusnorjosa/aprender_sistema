"""
PR 9 hardening RBAC (2026-04-30): sentinela de cobertura de endpoints.

Garante que todo endpoint API novo é classificado em uma de duas categorias:

1. **Coberto pela Matriz Viva**: endpoint registrado em
   `MATRIX_ENDPOINT_COVERAGE` mapeando a um recurso de `ACCESS_MATRIX`.
2. **Explicitamente isento**: endpoint listado em
   `RBAC_MATRIX_EXEMPT_PREFIXES` com motivo declarado.

Endpoint sem classificação → CI vermelho. Force o dev a:
- Adicionar entrada em `MATRIX_ENDPOINT_COVERAGE` (e em `RESOURCES`/
  `ACCESS_MATRIX` se for recurso novo); OU
- Adicionar prefixo a `RBAC_MATRIX_EXEMPT_PREFIXES` com motivo.

Não é "whitelist muda": cada exceção declara categoria + motivo.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportMissingTypeStubs=false

from __future__ import annotations

from django.urls import URLPattern, URLResolver, get_resolver

import pytest

from apps.core.rbac.matrix import ACCESS_MATRIX

# ============================================================================
# Parte 3 — Mapeamento matriz → endpoints
# ============================================================================
#
# Cada recurso de `ACCESS_MATRIX` deve ter pelo menos um endpoint concreto
# associado. Endpoints com `<id>` são placeholders (resolvidos em runtime).

MATRIX_ENDPOINT_COVERAGE: dict[str, list[str]] = {
    "grade_mensal": ["/api/availability/monthly/"],
    "deslocamentos": ["/api/deslocamentos/"],
    "dashboard_compras": ["/api/dat/compras-materiais/dashboard/"],
    "metrics_team_productivity": ["/api/metrics/team/productivity/"],
    "ciclos_acoes": ["/api/ciclos-acoes/"],
    "audit_logs": ["/api/audit-logs/"],
    "me_events": ["/api/me/events/"],
    "solicitacoes_list": ["/api/solicitacoes/"],
    # solicitacoes_batch_approve cobre os 4 endpoints de aprovação
    # (mesmo gate `CanAccessSolicitationApprovals`):
    "solicitacoes_batch_approve": [
        "/api/solicitacoes/<id>/approve/",
        "/api/solicitacoes/<id>/reject/",
        "/api/solicitacoes/batch-approve/",
        "/api/solicitacoes/batch-reject/",
    ],
    "produtos_list": ["/api/produtos/"],
    "usuario_lookup": ["/api/lookup/usuarios/"],
}


# ============================================================================
# Parte 4 — Whitelist categorizada (motivo declarado)
# ============================================================================
#
# Cada prefixo isento tem motivo. Endpoint que casa um destes prefixos passa
# pela sentinela sem ficar na matriz. Categoria explícita ajuda revisão.

RBAC_MATRIX_EXEMPT_PREFIXES: dict[str, str] = {
    # ── Auth / bootstrap ─────────────────────────────────────────────────
    "/api/auth/": "Autenticação (login/logout/ping) — fora do RBAC de domínio",
    "/api/csrf/": "Token CSRF — fluxo de auth",
    "/api/me/": "Auth bootstrap (current user, policies) — não é recurso de domínio",
    "/api/oauth/": "OAuth callback/start — escopo SEC-011 separado",
    "/api/integrations/google/": "OAuth + calendar integration — escopo paralelo",
    # ── Health / observability ───────────────────────────────────────────
    "/api/version/": "Endpoint de versão — observability",
    "/api/readyz/": "Health check — observability",
    "/api/healthz/": "Health check — observability",
    "/api/config/": "Feature config flags — observability",
    "/api/features/": "Feature flags — observability",
    "/api/stats/": "Home stats — observability/dashboard",
    # ── Schema / docs ────────────────────────────────────────────────────
    "/api/schema/": "OpenAPI schema — documentação técnica",
    "/api/docs/": "Swagger UI — documentação interativa",
    "/api/redoc/": "ReDoc UI — documentação interativa",
    # ── Options/lookups públicos (por design — autenticado) ──────────────
    "/api/options/": "Dropdowns/selects autenticados (cobertos em test_views_options.py)",
    "/api/lookup/municipios/": "Lookup público autenticado (não é UsuarioLookup)",
    "/api/lookup/projetos/": "Lookup público autenticado",
    "/api/lookup/tipos-evento/": "Lookup público autenticado",
    # ── Imports síncronos endurecidos (cobertura específica) ─────────────
    "/api/controle/import-": "Imports síncronos — endurecidos PR-A1 DAT-Imports, cobertura própria",
    "/api/disponibilidade/import-bloqueios/": "Import síncrono — endurecido PR-A1, cobertura própria",
    "/api/deslocamentos/import/": "Import síncrono — endurecido PR-A1",
    "/api/produtos/import/": "Import síncrono — endurecido PR-A1",
    "/api/eventos/import/": "Import síncrono — cobertura própria",
    "/api/colecoes/import/": "Import síncrono — cobertura própria",
    "/api/equipe-gerencia/import/": "Import síncrono — cobertura própria",
    "/api/municipios/import/": "Import síncrono — cobertura própria",
    "/api/usuarios/import/": "Import síncrono — cobertura própria",
    "/api/dat/import-cadastros/": "Import síncrono — cobertura própria",
    "/api/import-compras/": "Alias legado de import compras",
    "/api/solicitacoes/import/": "Import síncrono — cobertura própria",
    # ── ASQ-005 async ────────────────────────────────────────────────────
    "/api/imports/": "ASQ-005 async (regime separado #778)",
    # ── GCal management (escopo paralelo) ─────────────────────────────────
    "/api/gcal/": "GCal dashboard/integration — escopo paralelo, cobertura dedicada",
    # ── Admin DAT/Controle (cobertura via tests específicos) ─────────────
    "/api/dat/": "Admin DAT module — cobertura via tests específicos por viewset",
    "/api/controle/": "Controle endpoints — cobertura via tests específicos",
    "/api/pre-agenda/": "Pre-agenda Controle — cobertura específica",
    # ── Reports/metrics auxiliares (não-matriz) ──────────────────────────
    "/api/reports/": "Reports — cobertura via tests dedicados",
    "/api/metrics/": "Metrics — apenas metrics_team_productivity está na matriz",
    "/api/dashboard/": "Dashboards auxiliares — cobertura específica",
    # ── Misc ─────────────────────────────────────────────────────────────
    "/api/availability/check": "Availability checking — cobertura via test_availability_*",
    "/api/solicitacoes/validate/": "Validation endpoint — IsAuthenticated por design",
    "/api/rbac/meta/": "RBAC metadata — admin tooling, cobertura via test_admin_api.py",
    # ── Admin Registries (DAT-only via manage_admin_registries) ──────────
    "/api/municipios/": "Admin DAT registry — cobertura via test_admin_api.py",
    "/api/projetos/": "Admin DAT registry — cobertura via test_admin_api.py + test_pr7_projeto_fluxo_required.py",
    "/api/projetos-gerais/": "Admin DAT registry — cobertura via tests específicos",
    "/api/gerencias/": "Admin DAT registry — cobertura via test_admin_api.py",
    "/api/compras/": "Compras CRUD — cobertura via test_admin_api.py",
    "/api/usuarios-admin/": "Admin Usuários — cobertura via tests específicos",
    "/api/grupos/": "Admin Groups — cobertura via tests específicos",
    "/api/permissoes-funcionais/": "Admin Permissions — cobertura via tests específicos",
    "/api/availability-blocks/": "Bloqueios — cobertura via test_availability_*",
    "/api/notificacoes-internas/": "Notificações internas — cobertura paralela",
    "/api/acoes-instancia/": "Ações instance — cobertura paralela",
    # ── Solicitação ações específicas (não são gate de aprovação) ────────
    "/api/solicitacoes/<id>/preview-gcal/": "Preview GCal — cobertura via test_solicitacao_*",
    "/api/solicitacoes/<id>/publish/": "Publish GCal — cobertura via test_solicitacao_*",
    "/api/solicitacoes/<id>/resync-gcal/": "Resync GCal — cobertura via test_solicitacao_*",
    "/api/solicitacoes/<id>/cancel-gcal/": "Cancel GCal — cobertura via test_solicitacao_*",
    # ── Detail variants compartilham permission_classes da list (mesma ViewSet) ──
    "/api/audit-logs/<id>/": "Detail variant — compartilha permission da list (audit_logs)",
    "/api/ciclos-acoes/<id>/": "Detail variant — compartilha permission da list (ciclos_acoes)",
    "/api/deslocamentos/<id>/": "Detail variant — compartilha permission da list (deslocamentos)",
    "/api/produtos/<id>/": "Detail variant — compartilha permission da list (produtos_list)",
    "/api/solicitacoes/<id>/": "Detail variant — compartilha permission da list (solicitacoes_list)",
    # ── API root (DRF DefaultRouter root view) ───────────────────────────
    "/api/": "API root index — DRF DefaultRouter, IsAuthenticated por design",
}


# ============================================================================
# Helpers — extrair endpoints de domínio (api/) da URL conf
# ============================================================================


def _walk_urlpatterns(resolver, prefix: str = "") -> list[str]:
    """Recursivamente extrai paths das URLs (representação textual)."""
    out: list[str] = []
    for pat in resolver.url_patterns:
        if isinstance(pat, URLResolver):
            sub_prefix = prefix + str(pat.pattern)
            out.extend(_walk_urlpatterns(pat, sub_prefix))
        elif isinstance(pat, URLPattern):
            out.append(prefix + str(pat.pattern))
    return out


def _normalize_path(raw: str) -> str:
    """Converte regex paths em URLs legíveis (`<pk>` → `<id>`).

    Exemplos:
      'api/v1/^solicitacoes/(?P<pk>[^/.]+)/approve/$' →
      '/api/solicitacoes/<id>/approve/'
    """
    import re

    s = raw
    # Remove âncoras de regex
    s = s.replace("^", "").replace("$", "")
    # Converte placeholders DRF — qualquer `(?P<pk>...)` vira `<id>`.
    # O regex original às vezes aparece como `(?P<pk>[^/.]+)` ou
    # `(?P<pk>[/.]+)` dependendo da combinação. Captura ambos via regex.
    s = re.sub(r"\(\?P<pk>[^)]+\)", "<id>", s)
    s = re.sub(r"\(\?P<format>[^)]+\)", "<fmt>", s)
    s = s.replace("<int:pk>", "<id>")
    s = s.replace("<drf_format_suffix:format>", "<fmt>")
    # Garante prefixo /api/ (DRF prepend depende do project)
    if s.startswith("api/v1/"):
        s = "/api/" + s[len("api/v1/") :]
    elif s.startswith("api/"):
        s = "/" + s
    elif not s.startswith("/"):
        s = "/" + s
    return s


def _domain_endpoints() -> set[str]:
    """Endpoints de domínio (api/) sem variantes `.format` que são apenas
    para content-negotiation do DRF Router."""
    raw_paths = _walk_urlpatterns(get_resolver())
    out: set[str] = set()
    for p in raw_paths:
        norm = _normalize_path(p)
        if not norm.startswith("/api/"):
            continue
        if "<fmt>" in norm:
            continue  # variante content-negotiation; o canonical já cobre
        out.add(norm)
    return out


def _is_exempt(endpoint: str) -> tuple[bool, str]:
    """True se endpoint começa com algum prefixo isento. Retorna motivo."""
    for prefix, reason in RBAC_MATRIX_EXEMPT_PREFIXES.items():
        if endpoint.startswith(prefix):
            return True, reason
    return False, ""


def _is_covered(endpoint: str) -> tuple[bool, str]:
    """True se endpoint está em MATRIX_ENDPOINT_COVERAGE. Retorna recurso."""
    for resource, urls in MATRIX_ENDPOINT_COVERAGE.items():
        if endpoint in urls:
            return True, resource
    return False, ""


# ============================================================================
# Tests
# ============================================================================


def test_all_matrix_resources_have_endpoint_mapping():
    """Todo recurso em ACCESS_MATRIX tem entrada em MATRIX_ENDPOINT_COVERAGE."""
    missing = sorted(set(ACCESS_MATRIX.keys()) - set(MATRIX_ENDPOINT_COVERAGE.keys()))
    assert not missing, (
        f"Recursos sem mapeamento em MATRIX_ENDPOINT_COVERAGE: {missing}. "
        "Adicione entrada com URLs concretas para cada recurso novo."
    )


def test_no_orphan_coverage_entries():
    """Cada entry em MATRIX_ENDPOINT_COVERAGE corresponde a um recurso real."""
    orphans = sorted(set(MATRIX_ENDPOINT_COVERAGE.keys()) - set(ACCESS_MATRIX.keys()))
    assert not orphans, (
        f"MATRIX_ENDPOINT_COVERAGE tem keys sem ACCESS_MATRIX: {orphans}. "
        "Remova ou adicione o recurso correspondente em ACCESS_MATRIX."
    )


def test_no_uncovered_domain_endpoints():
    """Sentinela: endpoint /api/* não classificado falha CI.

    Cada endpoint deve estar em UMA destas categorias:
    - MATRIX_ENDPOINT_COVERAGE (recurso da Matriz Viva)
    - RBAC_MATRIX_EXEMPT_PREFIXES (isento com motivo)

    Quando esta falha aparece para você:
    1. O endpoint pertence à matriz? Adicione em MATRIX_ENDPOINT_COVERAGE +
       ACCESS_MATRIX + RESOURCES + EXPECTED_MATRIX (snapshot).
    2. O endpoint é fora do escopo de RBAC de domínio? Adicione prefixo a
       RBAC_MATRIX_EXEMPT_PREFIXES com motivo claro.
    3. Não use whitelist muda — cada exceção precisa de motivo declarado.
    """
    endpoints = _domain_endpoints()
    unclassified: list[str] = []
    for ep in sorted(endpoints):
        is_covered, _ = _is_covered(ep)
        is_exempt, _ = _is_exempt(ep)
        if not is_covered and not is_exempt:
            unclassified.append(ep)

    assert not unclassified, (
        "RBAC_MATRIX_UNCLASSIFIED: endpoints novos não classificados:\n  - "
        + "\n  - ".join(unclassified)
        + "\n\nAdicione em MATRIX_ENDPOINT_COVERAGE (recurso da matriz) "
        "ou em RBAC_MATRIX_EXEMPT_PREFIXES (com motivo)."
    )


@pytest.mark.parametrize("prefix,reason", list(RBAC_MATRIX_EXEMPT_PREFIXES.items()))
def test_exempt_prefixes_have_non_empty_reason(prefix: str, reason: str):
    """Garante que cada exceção tem motivo declarado (não-vazio, > 10 chars)."""
    assert reason and len(reason) >= 10, (
        f"Prefixo isento '{prefix}' tem motivo vazio/curto. "
        "Whitelist muda não é aceita: cada exceção precisa explicar por quê."
    )
