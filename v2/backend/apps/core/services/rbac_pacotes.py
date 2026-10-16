"""
Pacote de capacidades por perfil de gerência (ADR-020) e direitos de evento do papel (PR 8). Só
constantes; quem lê é a fórmula da união (`rbac_permissions.capacidades_sem_cache`).

CONTROLE e DIRETORIA são o **estado de produção de hoje** do grupo de setor correspondente (medição de
02/10/2026), para que o PR B (grupos ∪ pacote) não desse poder novo a quem já estava no grupo. O
ADMIN_OPERACIONAL é o pacote **final** desde o PR 10 (16/10/2026, seção 2.3 do relatório de
arquitetura mais a isenção da regra da compra): o DAT é o administrador operacional. Mudar um pacote é
mudar poder: PR com `rbac_diff` medido.

Fica fora de `apps/core/rbac/` de propósito: `rbac/__init__` importa `rbac/helpers`, que importa
`services/rbac_permissions`. Como `rbac_permissions` lê o pacote (PR B), um módulo dentro
de `rbac/` fecharia um ciclo de import na subida. Este módulo não importa nada do projeto
(`test_import_do_modulo_nao_cria_ciclo`). As chaves são os valores de `Gerencia.Perfil`
(`test_todo_perfil_tem_linha_explicita`).
"""

from __future__ import annotations

# Uma linha explícita por perfil (`Gerencia.Perfil`).
PACOTE: dict[str, frozenset[str]] = {
    "PADRAO": frozenset(),
    # PR 10 (decisões do dono de 02/10, nº 12 e 16, e de 14/10): o DAT aprova (base 5 de
    # `solicitation_approval_basis`), cria, edita e exclui evento em qualquer projeto, sem a regra da
    # compra, exclui nos cadastros e opera a pré-agenda e a seção Controle. Sem `import_spreadsheet`
    # ("técnico só para mim"); o grupo DAT também o perdeu (migration 0126).
    "ADMIN_OPERACIONAL": frozenset(
        {
            "manage_admin_registries",
            "manage_purchases_and_materials",
            "view_all_availability",
            "view_map_metrics",
            "create_solicitation",
            "edit_solicitation_as_owner_or_privileged",
            "approve_solicitation",
            "execute_restricted_operations",
            "operate_preagenda",
            "run_daily_operations",
            "create_solicitation_without_purchase",
        }
    ),
    "CONTROLE": frozenset(
        {
            "manage_purchases_and_materials",
            "operate_preagenda",
            "run_daily_operations",
            "view_all_availability",
        }
    ),
    # A aprovação de SUPER vem do papel GERENTE na gerência aprovadora, não de pacote.
    "APROVACAO": frozenset(),
    "DIRETORIA": frozenset(
        {
            "supervise_operations",
            "view_compras_dashboard",
            "view_map_metrics",
            "view_overview_dashboard",
        }
    ),
}

# D3 (a): só EQUIPE e GERENTE recebem o pacote. FORMADOR, COORDENADOR e APOIO nunca.
PAPEIS_COM_PACOTE: frozenset[str] = frozenset({"EQUIPE", "GERENTE"})

# PR 8 das permissões (ADR-020, "o papel dá o poder"): direito de EVENTO do papel vigente, em qualquer
# gerência ativa. Não é pacote: não depende do perfil da gerência, e o D3 continua valendo para o
# pacote (FORMADOR, COORDENADOR e APOIO não recebem pacote). Uma linha explícita por papel
# (`EquipeGerencia.PAPEL_CHOICES`). A GERENTE não publica no Google (O8-4, paridade).
_DIREITOS_DE_EVENTO: frozenset[str] = frozenset({"create_solicitation", "edit_solicitation_as_owner_or_privileged"})
DIREITOS_PAPEL: dict[str, frozenset[str]] = {
    "FORMADOR": frozenset(),
    "EQUIPE": frozenset(),
    "COORDENADOR": _DIREITOS_DE_EVENTO,
    "GERENTE": _DIREITOS_DE_EVENTO,
    "APOIO": _DIREITOS_DE_EVENTO | {"publish_setor_solicitacao"},
}

# Capacidades técnicas: nunca entram em pacote (só o superusuário as tem pelo grupo).
TECNICAS: frozenset[str] = frozenset({"import_spreadsheet"})

# `Gerencia.nome` → único perfil ≠ PADRAO aceito nela. `rbac_diff --auditar` sai com exit 1 para
# qualquer outro. Cresce no PR que liberar o próximo perfil.
PERFIL_PERMITIDO: dict[str, str] = {
    "GERENCIA DAT": "ADMIN_OPERACIONAL",
    "CONTROLE": "CONTROLE",
}
