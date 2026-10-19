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

- **10 atores** (`ACTORS`) × **12 recursos** (`RESOURCES`) = 120 cases parametrizados
  (começou com 8 × 8 = 64; o PR 8 e o import pela tela ampliaram)
- **Sem scope cases** (Coord vs gerência X vs Y) — esses ficam em tests
  dedicados (`test_deslocamento_rbac.py`, `test_availability_monthly_rbac.py`).
- **GET e dois POST** (`solicitacoes_batch_approve` e `import_pela_tela`); os demais
  POST/create ficam em tests específicos por endpoint.
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
GERENTE: Final = "Gerente"  # legacy — Setor Vidas + Função Gerente (Gerente pedagógico)
COORDENADOR: Final = "Coordenador"
APOIO: Final = "Apoio de Coordenação"
FORMADOR: Final = "Formador"

# PR 8 hardening RBAC (2026-04-30): atores compostos para distinguir
# regras endurecidas em PRs 3-6 (Aprovações + Audit Logs).
# PR B1: aprova pelo vínculo GERENTE na gerência SUPERINTENDENCIA (a fixture cria). PR 11: o
# Assistente Administrativo do Controle aprova pelo vínculo EQUIPE na gerência CONTROLE (a fixture cria),
# como a u7 em produção; os grupos ficam só como nome (renomear a persona fica para o PR 13).
GERENTE_SUPER: Final = "Gerente da Superintendência"
ASST_ADMIN_CONTROLE: Final = "Assistente Administrativo do Controle"  # grupos + vínculo EQUIPE no Controle

ACTORS: Final[tuple[str, ...]] = (
    SUPERUSER,
    DAT,
    CONTROLE,
    DIRETORIA,
    GERENTE,
    GERENTE_SUPER,
    ASST_ADMIN_CONTROLE,
    COORDENADOR,
    APOIO,
    FORMADOR,
)

# Mapping ator → group_names usados em `_make_user`. Superuser é caso especial.
# Atores compostos têm múltiplos grupos (Setor + Função). PR 12a: o grupo é etiqueta; o poder de DAT,
# Controle, Diretoria e Assistente Administrativo do Controle vem do vínculo que a fixture cria na gerência
# do pacote (`test_rbac_matrix_living._make_user_for_actor`), como em produção.
ACTOR_GROUPS: Final[dict[str, list[str]]] = {
    SUPERUSER: [],  # is_superuser=True (não usa grupos)
    DAT: ["DAT"],
    CONTROLE: ["Controle"],
    DIRETORIA: ["Diretoria"],
    GERENTE: ["Gerente"],
    GERENTE_SUPER: ["Superintendência", "Gerente"],  # + vínculo GERENTE em SUPERINTENDENCIA (fixture)
    ASST_ADMIN_CONTROLE: ["Controle", "Assistente Administrativo"],  # + vínculo EQUIPE em CONTROLE (fixture)
    COORDENADOR: ["Coordenador"],
    APOIO: ["Apoio de Coordenação"],
    FORMADOR: ["Formador"],
}


# ============================================================================
# Recursos canônicos (12 endpoints discriminantes)
# ============================================================================


@dataclass(frozen=True)
class ResourceCase:
    """Endpoint a auditar. `query` adicionado à URL via querystring.

    `body` permite payload válido em POST (ex: `{"ids": []}` para
    batch-approve evitar 400 por ids_required quando o gate aprova).
    """

    name: str
    method: str
    url: str
    query: dict[str, str] = field(default_factory=dict)
    body: dict[str, object] = field(default_factory=dict)

    def full_url(self) -> str:
        if not self.query:
            return self.url
        qs = "&".join(f"{k}={v}" for k, v in self.query.items())
        return f"{self.url}?{qs}"


# Status codes canônicos. Manter como int para que pytest exiba diff legível.
ALLOW = 200
DENY = 403
# PR 8 hardening RBAC (2026-04-30): para endpoints POST cujo gate de
# autorização passa antes da validação de payload, o test runner usa
# `ALLOW_PAYLOAD_INVALID` — significa "gate aprovou; serviço rejeitou
# payload por motivo não-RBAC". Útil para batch-approve com `ids: []`
# (gate aprova; serviço retorna 400 ids_required). Permanece distinto
# de DENY (403) para garantir que o gate diferenciou o ator.
ALLOW_PAYLOAD_INVALID = 400


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
    # PR 8 hardening RBAC (2026-04-30): cobre regras endurecidas em PRs 3-6.
    # Aprovação composite (PR 3 #1308): batch-approve representa os 4 endpoints
    # de aprovação (mesmo gate `CanAccessSolicitationApprovals`). approve/reject
    # individuais e batch-reject têm cobertura dedicada em test_pr3_approvals_policy.
    ResourceCase(
        "solicitacoes_batch_approve",
        "POST",
        "/api/solicitacoes/batch-approve/",
        body={"ids": []},  # lista vazia é no-op (200 com approved=0); evita 400 por ids_required
    ),
    # ProdutoViewSet (PR 4 #1309): list restrito a DAT/Controle.
    ResourceCase("produtos_list", "GET", "/api/produtos/"),
    # UsuarioLookup (PR 5 #1310): cap-gated, sem hardcode de grupos.
    ResourceCase("usuario_lookup", "GET", "/api/lookup/usuarios/"),
    # Upload de planilha (2026-10-02): import-compras representa as 13 rotas (12 endpoints + 1 alias) de
    # import pela tela (mesmo gate `SuperuserOnly`); cada um tem cobertura em
    # test_imports_pela_tela_so_superusuario.py.
    ResourceCase("import_pela_tela", "POST", "/api/controle/import-compras/"),
    # Escrita em gerências (decisão do dono, 19/10/2026): POST representa create/update/partial_update/
    # destroy (mesmo gate em `GerenciaViewSet.get_permissions`); método a método em
    # test_gerencias_escrita_so_dat.py. Corpo vazio: o gate aprova e o serializer responde 400.
    ResourceCase("gerencias_escrita", "POST", "/api/gerencias/"),
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
        DAT: ALLOW,  # D9: view_all_availability pelo pacote ADMIN_OPERACIONAL (vínculo EQUIPE)
        CONTROLE: ALLOW,  # view_all_availability pelo pacote CONTROLE (vínculo EQUIPE; mantém de D6)
        DIRETORIA: DENY,  # D8: decisão executiva, não consulta operacional
        GERENTE: ALLOW,  # D9: scoped via EquipeGerencia (perdeu cap global) — fixture cria vínculo
        GERENTE_SUPER: ALLOW,  # PR 8: composite Sup+Gerente — fixture cria EquipeGerencia
        ASST_ADMIN_CONTROLE: ALLOW,  # view_all_availability pelo pacote CONTROLE (vínculo EQUIPE)
        COORDENADOR: ALLOW,  # scoped via EquipeGerencia (D6) — fixture cria vínculo
        APOIO: ALLOW,  # scoped via EquipeGerencia (D6) — fixture cria vínculo
        # PR 9 (P9-3): o `HasSectorAccess` só aceita papel G/C/A vigente (`gerencias_de_atuacao`), o
        # mesmo da tela (policy `access_monthly_availability`). O papel FORMADOR sozinho não abre a API.
        FORMADOR: DENY,
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
        GERENTE_SUPER: DENY,
        ASST_ADMIN_CONTROLE: DENY,
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
        GERENTE_SUPER: DENY,
        ASST_ADMIN_CONTROLE: ALLOW,  # herda Controle (run_daily_operations)
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # Ações Internas (CicloAcoesViewSet): `[HasPerm("manage_internal_actions")]` (Onda 1 C3).
    # Capacidade fora de todo pacote e papel → só o superuser abre. Para liberar, incluir no
    # pacote do perfil (`rbac_pacotes.py`) num PR com `rbac_diff`; atribuir grupo não dá poder desde o PR 12.
    "ciclos_acoes": {
        SUPERUSER: ALLOW,
        DAT: DENY,
        CONTROLE: DENY,
        DIRETORIA: DENY,
        GERENTE: DENY,
        GERENTE_SUPER: DENY,
        ASST_ADMIN_CONTROLE: DENY,
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # AuditLog: `[CanAccessAuditLogs]` (Epic 4.2.a + PR 6 hardening RBAC 2026-04-30).
    # Capabilities: manage_admin_registries | operate_preagenda.
    # PR 6 (2026-04-30): removidos `approve_solicitation` e
    # `approve_solicitation_batch` para evitar liberação indevida a
    # Gerente pedagógico, Sup pura e Gerente da Sup.
    "audit_logs": {
        SUPERUSER: ALLOW,
        DAT: ALLOW,  # manage_admin_registries (suportar)
        CONTROLE: ALLOW,  # operate_preagenda (operar)
        DIRETORIA: DENY,
        GERENTE: DENY,  # PR 6: removido approve_solicitation_batch do gate
        GERENTE_SUPER: DENY,  # PR 6: idem (já não tem mais approve_solicitation no gate)
        ASST_ADMIN_CONTROLE: ALLOW,  # herda Controle (operate_preagenda)
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
    #
    # PR 8 (2026-04-30): consolida regras dos PRs 3, 4, 5 na matriz.
    #
    # Aprovação de solicitação (PR 3 #1308): policy composta
    # `CanAccessSolicitationApprovals` = vínculo GERENTE em g1 OR a capacidade `approve_solicitation`,
    # que vem do pacote do perfil da gerência: ADMIN_OPERACIONAL (DAT, PR 10) e CONTROLE (PR 11), pelo
    # vínculo EQUIPE/GERENTE. Nenhum grupo aprova (PR 11).
    # Os 4 endpoints (approve/reject individual + batch) compartilham o mesmo
    # gate; batch-approve representa todos. Cobertura granular fica em
    # `test_pr3_approvals_policy.py`.
    # Status code esperado para POST sem ids = 200 (lista vazia → no-op) para
    # personas allowed; demais perfis recebem 403 antes do payload.
    "solicitacoes_batch_approve": {
        # ALLOW_PAYLOAD_INVALID (400) = gate aprovou; serviço rejeita payload
        # `ids: []` por ids_required. Cobertura granular dos 4 endpoints com
        # solicitação pendente real está em test_pr3_approvals_policy.py.
        SUPERUSER: ALLOW_PAYLOAD_INVALID,
        DAT: ALLOW_PAYLOAD_INVALID,  # PR 10: `capacidade_aprovar` pelo pacote ADMIN_OPERACIONAL
        CONTROLE: ALLOW_PAYLOAD_INVALID,  # PR 12a: o ator tem o vínculo na gerência CONTROLE (D1, pacote)
        DIRETORIA: DENY,
        GERENTE: DENY,  # Gerente pedagógico (Vidas + Gerente) NÃO aprova
        GERENTE_SUPER: ALLOW_PAYLOAD_INVALID,  # vínculo GERENTE na gerência SUPERINTENDENCIA
        ASST_ADMIN_CONTROLE: ALLOW_PAYLOAD_INVALID,  # PR 11: `capacidade_aprovar` pelo pacote CONTROLE (vínculo)
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # ProdutoViewSet list (PR 4 #1309): list/retrieve restrito a operação/admin.
    # Composition: `manage_admin_registries | manage_purchases_and_materials | run_daily_operations`.
    # DAT (admin) + Controle (operação). Dropdowns/selects de Coord/Apoio
    # consomem `/api/options/produtos/` (IsAuthenticated, intocado).
    "produtos_list": {
        SUPERUSER: ALLOW,
        DAT: ALLOW,  # manage_admin_registries
        CONTROLE: ALLOW,  # run_daily_operations + manage_purchases_and_materials
        DIRETORIA: DENY,
        GERENTE: DENY,
        GERENTE_SUPER: DENY,
        ASST_ADMIN_CONTROLE: ALLOW,  # herda Controle
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # UsuarioLookup (PR 5 #1310): cap-gated, sem hardcode de grupos.
    # Composition: `create_solicitation | manage_admin_registries`.
    # Coord/Apoio/Gerente (pedagógico ou Sup) usam `create_solicitation` para
    # popular pickers em NewSolicitacaoWizard. DAT usa manage_admin_registries.
    # `create_solicitation` vem do papel vigente (vínculo EquipeGerencia, `DIREITOS_PAPEL`), não da
    # Função. Asst Admin Controle (vínculo EQUIPE) não tem; só passaria com papel
    # COORDENADOR/GERENTE/APOIO vigente — não esse ator.
    "usuario_lookup": {
        SUPERUSER: ALLOW,
        DAT: ALLOW,  # manage_admin_registries
        CONTROLE: DENY,  # PR 5: sem create_solicitation nem manage_admin_registries
        DIRETORIA: DENY,
        GERENTE: ALLOW,  # create_solicitation pelo papel GERENTE (DIREITOS_PAPEL) — fixture cria vínculo
        GERENTE_SUPER: ALLOW,  # idem (vínculo GERENTE na SUPERINTENDENCIA)
        ASST_ADMIN_CONTROLE: DENY,  # composite Asst Admin não tem create_solicitation
        COORDENADOR: ALLOW,  # create_solicitation
        APOIO: ALLOW,  # create_solicitation
        FORMADOR: DENY,
    },
    #
    # Import pela tela (2026-10-02): `[IsAuthenticated, SuperuserOnly]`.
    # Nenhuma capability abre (nem `import_spreadsheet` nem `manage_admin_registries`
    # do DAT): cargas passam por script, com ensaio. POST sem arquivo: o gate aprova
    # o superuser e a view responde 400.
    "import_pela_tela": {
        SUPERUSER: ALLOW_PAYLOAD_INVALID,
        DAT: DENY,  # antes importava (PR-A1 DAT-Imports, 2026-04-29)
        CONTROLE: DENY,
        DIRETORIA: DENY,
        GERENTE: DENY,
        GERENTE_SUPER: DENY,
        ASST_ADMIN_CONTROLE: DENY,
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
    #
    # Escrita em gerências (decisão do dono, 19/10/2026; D29): `HasPerm("manage_admin_registries")`, a
    # capacidade da tela /dat/admin/gerencias. Antes era `manage_purchases_and_materials`, que o pacote
    # CONTROLE também tem. A leitura segue `IsAuthenticated`.
    "gerencias_escrita": {
        SUPERUSER: ALLOW_PAYLOAD_INVALID,
        DAT: ALLOW_PAYLOAD_INVALID,  # manage_admin_registries (pacote ADMIN_OPERACIONAL)
        CONTROLE: DENY,  # 19/10: o pacote CONTROLE tem manage_purchases_and_materials, não manage_admin_registries
        DIRETORIA: DENY,
        GERENTE: DENY,
        GERENTE_SUPER: DENY,
        ASST_ADMIN_CONTROLE: DENY,  # 19/10: idem Controle (vínculo EQUIPE no Controle)
        COORDENADOR: DENY,
        APOIO: DENY,
        FORMADOR: DENY,
    },
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
