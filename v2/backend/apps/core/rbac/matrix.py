"""
RBAC Living Matrix — SSOT canônica de autorização (Onda 3, 2026-04-27).

Espelha a tabela canônica de `v2/docs/rbac_authorization_matrix.md` §3 em
formato Python para tests parametrizados. Cada (ator × recurso) declara o
status code HTTP esperado.

Quando código diverge desta matriz, **CI vermelho imediato** com mensagem
explicativa do que mudou. A intenção é que o diff do test vire checklist
de revisão no PR.

## Como manter

1. Mudança de comportamento em `permission_classes`, seed ou capability
   atribuída → atualizar `ACCESS_MATRIX` aqui (decisão consciente).
2. Novo recurso/ator → adicionar entrada e ratificar com stakeholder.
3. Nunca silenciar test parametrizado sem entender o que mudou.

## Escopo desta primeira versão (decisão stakeholder, opção `c` híbrida)

- **8 atores** × **8 recursos** = 64 cases parametrizados
- **Sem scope cases** (Coord vs gerência X vs Y) — esses ficam em tests
  dedicados (`test_deslocamento_rbac.py`, `test_availability_monthly_rbac.py`).
- **GET only** — POST/create coberto em tests específicos por endpoint.
- **Sem cobertura combinatorial** de múltiplos grupos por user.

Expansão futura: adicionar mais recursos sob demanda; representar scope
como valor especial `SCOPED` quando precisarmos discriminar visibilidade.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

# ============================================================================
# Atores reconhecidos (espelham doc §2)
# ============================================================================

SUPERUSER: Final = "Superuser"
DAT: Final = "DAT"
CONTROLE: Final = "Controle"
DIRETORIA: Final = "Diretoria"
GERENTE: Final = "Gerente"
COORDENADOR: Final = "Coordenador"
APOIO: Final = "Apoio de Coordenação"
FORMADOR: Final = "Formador"

ACTORS: Final[tuple[str, ...]] = (
    SUPERUSER,
    DAT,
    CONTROLE,
    DIRETORIA,
    GERENTE,
    COORDENADOR,
    APOIO,
    FORMADOR,
)

# Mapping ator → group_names usados em `_make_user`. Superuser é caso especial.
ACTOR_GROUPS: Final[dict[str, list[str]]] = {
    SUPERUSER: [],  # is_superuser=True (não usa grupos)
    DAT: ["DAT"],
    CONTROLE: ["Controle"],
    DIRETORIA: ["Diretoria"],
    GERENTE: ["Gerente"],
    COORDENADOR: ["Coordenador"],
    APOIO: ["Apoio de Coordenação"],
    FORMADOR: ["Formador"],
}


# ============================================================================
# Recursos canônicos (8 endpoints discriminantes)
# ============================================================================


@dataclass(frozen=True)
class ResourceCase:
    """Endpoint a auditar. `query` adicionado à URL via querystring."""

    name: str
    method: str
    url: str
    query: dict[str, str] = field(default_factory=dict)

    def full_url(self) -> str:
        if not self.query:
            return self.url
        qs = "&".join(f"{k}={v}" for k, v in self.query.items())
        return f"{self.url}?{qs}"


# Status codes canônicos. Manter como int para que pytest exiba diff legível.
ALLOW = 200
DENY = 403


RESOURCES: Final[tuple[ResourceCase, ...]] = (
    ResourceCase(
        "grade_mensal",
        "GET",
        "/api/availability/monthly/",
        {"year": "2026", "month": "5", "role": "FORMADOR"},
    ),
    ResourceCase("deslocamentos", "GET", "/api/deslocamentos/"),
    ResourceCase("dashboard_compras", "GET", "/api/dat/compras-materiais/dashboard/"),
    ResourceCase("metrics_team_productivity", "GET", "/api/metrics/team/productivity/"),
    ResourceCase("ciclos_acoes", "GET", "/api/ciclos-acoes/"),
    ResourceCase("audit_logs", "GET", "/api/audit-logs/"),
    ResourceCase("me_events", "GET", "/api/me/events/"),
    ResourceCase("solicitacoes_list", "GET", "/api/solicitacoes/"),
)


# ============================================================================
# Matriz canônica — atores × recursos → expected status code
# ============================================================================
#
# Comentários por linha registram a justificativa (rastreável no diff de PR).
# Mudar uma célula = decisão arquitetural consciente.
# ============================================================================


# Atalho — todos os atores autenticados acessam (recurso aberto pra auth)
_ALL_AUTH: Final[dict[str, int]] = {actor: ALLOW for actor in ACTORS}


ACCESS_MATRIX: Final[dict[str, dict[str, int]]] = {
    # Grade Mensal — D8 + D9 (2026-04-28).
    # Composition: `[IsAuthenticated, CanViewAllAvailability | HasSectorAccess]`
    # com HasSectorAccess endurecida (sem gerencia_id exige EquipeGerencia ativa).
    # Para Coord/Apoio/Gerente retornar 200, a fixture `_make_user_for_actor` cria EquipeGerencia.
    # Scope discriminante (Gerente Vidas não vê Fluir, etc.) é PR 8 / test_availability_monthly_rbac.py.
    "grade_mensal": {
        SUPERUSER: ALLOW,
        DAT: ALLOW,  # D9: ator transversal admin recebe view_all_availability via seed 0080
        CONTROLE: ALLOW,  # view_all_availability via seed 0080 (mantém de D6)
        DIRETORIA: DENY,  # D8: decisão executiva, não consulta operacional
        GERENTE: ALLOW,  # D9: scoped via EquipeGerencia (perdeu cap global) — fixture cria vínculo
        COORDENADOR: ALLOW,  # scoped via EquipeGerencia (D6) — fixture cria vínculo
        APOIO: ALLOW,  # scoped via EquipeGerencia (D6) — fixture cria vínculo
        FORMADOR: DENY,  # D8: caso especial; só Meus Eventos + Bloqueios próprios
    },
    #
    # Deslocamentos: `[IsAuthenticated]` + queryset scope filter (Onda 1 C2).
    # Todos autenticados retornam 200; queryset filtra cross-table via EquipeGerencia.
    # Scope discriminante coberto em test_deslocamento_rbac.py (Onda 1 C2 PR #1250).
    "deslocamentos": _ALL_AUTH,
    #
    # Dashboard Compras: `[CanViewComprasDashboard]` (Epic 4.2.b1).
    # Capabilities elegíveis: view_compras_dashboard | manage_admin_registries.
    # Diretoria + DAT (Decisão D7 + ator transversal).
    "dashboard_compras": {
        SUPERUSER: ALLOW,
        DAT: ALLOW,  # manage_admin_registries
        CONTROLE: DENY,
        DIRETORIA: ALLOW,  # view_compras_dashboard
        GERENTE: DENY,
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # Metrics team productivity: composition (Onda 2 A3 β).
    # `run_daily_operations | supervise_operations | manage_admin_registries`.
    # Controle + Diretoria + DAT (representa Dashboard Equipe).
    "metrics_team_productivity": {
        SUPERUSER: ALLOW,
        DAT: ALLOW,  # manage_admin_registries
        CONTROLE: ALLOW,  # run_daily_operations
        DIRETORIA: ALLOW,  # supervise_operations
        GERENTE: DENY,
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # Ações Internas (CicloAcoesViewSet): `[HasPerm("manage_internal_actions")]` (Onda 1 C3).
    # Capability sem grupos atribuídos no seed → apenas superuser bypassa.
    # Quando feature ficar madura, admin atribui grupo via UI sem code change.
    "ciclos_acoes": {
        SUPERUSER: ALLOW,
        DAT: DENY,
        CONTROLE: DENY,
        DIRETORIA: DENY,
        GERENTE: DENY,
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # AuditLog: `[CanAccessAuditLogs]` (Epic 4.2.a).
    # Capabilities: manage_admin_registries | operate_preagenda |
    #               approve_solicitation | approve_solicitation_batch.
    # 4 motivos legítimos: auditar/operar/suportar.
    "audit_logs": {
        SUPERUSER: ALLOW,
        DAT: ALLOW,  # manage_admin_registries (suportar)
        CONTROLE: ALLOW,  # operate_preagenda (operar)
        DIRETORIA: DENY,  # sem nenhuma das 4 capabilities elegíveis
        GERENTE: ALLOW,  # approve_solicitation_batch (auditar batch)
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # /api/me/events/: `[IsAuthenticated]` (Epic 2 — Formador é caso primário).
    # Todos autenticados acessam; serializer filtra por participação.
    "me_events": _ALL_AUTH,
    #
    # /api/solicitacoes/ list: `[IsAuthenticated]` via get_permissions (sem create).
    # Queryset filtra por permissions de quem pode ver tudo vs próprias.
    "solicitacoes_list": _ALL_AUTH,
}


def expand_matrix() -> list[tuple[str, ResourceCase, int]]:
    """Yield (actor, resource, expected_status) — usado em pytest.parametrize."""
    cases: list[tuple[str, ResourceCase, int]] = []
    for resource in RESOURCES:
        actor_map = ACCESS_MATRIX.get(resource.name)
        if actor_map is None:
            raise ValueError(
                f"Recurso '{resource.name}' não está em ACCESS_MATRIX. "
                f"Adicione em rbac/matrix.py ou remova de RESOURCES."
            )
        for actor in ACTORS:
            if actor not in actor_map:
                raise ValueError(f"Ator '{actor}' não tem entry para recurso '{resource.name}' em ACCESS_MATRIX.")
            cases.append((actor, resource, actor_map[actor]))
    return cases


def format_failure_message(
    actor: str,
    resource: ResourceCase,
    expected: int,
    received: int,
    response_body: str,
) -> str:
    """
    Mensagem de falha rica. Diz: ator, recurso, esperado, recebido,
    causa provável, próximos passos.
    """
    if received == DENY and expected == ALLOW:
        cause = (
            "Ator perdeu acesso. Causas prováveis: "
            "(1) seed/migration removeu capability do grupo; "
            "(2) view_class restrigiu permission_classes; "
            "(3) HasSectorAccess block hardcoded reintroduzido."
        )
    elif received == ALLOW and expected == DENY:
        cause = (
            "Ator GANHOU acesso indevido. RISCO DE PRIVACIDADE. Causas prováveis: "
            "(1) seed/migration adicionou capability sem revisão; "
            "(2) view_class virou IsAuthenticated sem scope; "
            "(3) policy nova OR muito permissiva."
        )
    else:
        cause = (
            f"Status inesperado ({received}). Esperado: {expected}. "
            "Verifique se a view retornou 4xx por payload inválido (não autorização)."
        )

    return (
        f"\n=== RBAC LIVING MATRIX MISMATCH ===\n"
        f"Ator:        {actor}\n"
        f"Recurso:     {resource.name} ({resource.method} {resource.url})\n"
        f"Esperado:    HTTP {expected}\n"
        f"Recebido:    HTTP {received}\n"
        f"Provável:    {cause}\n"
        f"\n"
        f"Para resolver:\n"
        f"  - Se mudança intencional: atualizar ACCESS_MATRIX em apps/core/rbac/matrix.py\n"
        f"  - Se regressão: investigar permission_classes da view ou seed da capability\n"
        f"  - Doc canônico: v2/docs/rbac_authorization_matrix.md §3\n"
        f"\n"
        f"Response body (truncado):\n"
        f"  {response_body[:200]}\n"
        f"==================================="
    )
