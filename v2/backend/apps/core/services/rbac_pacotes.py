"""
Pacote de capacidades por perfil de gerência (ADR-020). Só constantes; nada lê o pacote até o PR B.

O pacote é o **estado de produção de hoje** do grupo de setor correspondente (medição de 02/10/2026),
não o pacote final do relatório de arquitetura (seção 2.3). Por isso o PR B (grupos ∪ pacote) não dá
poder novo a quem já está no grupo. Mudar um pacote é mudar poder: PR com `rbac_diff` medido.

Fica fora de `apps/core/rbac/` de propósito: `rbac/__init__` importa `rbac/helpers`, que importa
`services/rbac_permissions`. Quando `rbac_permissions` passar a ler o pacote (PR B), um módulo dentro
de `rbac/` fecharia um ciclo de import na subida. Este módulo não importa nada do projeto
(`test_import_do_modulo_nao_cria_ciclo`). As chaves são os valores de `Gerencia.Perfil`
(`test_todo_perfil_tem_linha_explicita`).
"""

from __future__ import annotations

# Uma linha explícita por perfil (`Gerencia.Perfil`).
PACOTE: dict[str, frozenset[str]] = {
    "PADRAO": frozenset(),
    # Grupo DAT em produção (02/10) menos `import_spreadsheet` ("técnico só para mim").
    "ADMIN_OPERACIONAL": frozenset(
        {
            "manage_admin_registries",
            "manage_purchases_and_materials",
            "view_all_availability",
            "view_map_metrics",
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

# Capacidades técnicas: nunca entram em pacote (só o superusuário as tem pelo grupo).
TECNICAS: frozenset[str] = frozenset({"import_spreadsheet"})

# `Gerencia.nome` → único perfil ≠ PADRAO aceito nela. `rbac_diff --auditar` sai com exit 1 para
# qualquer outro. Cresce no PR que liberar o próximo perfil.
PERFIL_PERMITIDO: dict[str, str] = {
    "GERENCIA DAT": "ADMIN_OPERACIONAL",
    "CONTROLE": "CONTROLE",
}
