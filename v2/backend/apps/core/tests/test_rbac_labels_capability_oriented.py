"""
Epic 1 RBAC Refactor — regression tests for capability-oriented naming.

Garantem que labels e descriptions de FunctionalPermissionSeed não contenham
nome de setor/função (acoplamento identity↔capability), e que categorias
sigam o vocabulário canônico definido em v2/docs/plans/rbac-refactor/master-plan.md.

Se um desses testes falhar num PR futuro, significa que o programa RBAC
Refactor está regredindo para o anti-pattern original (labels acopladas
ao organograma em vez de ao que a pessoa pode fazer).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import re

from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED

# Termos proibidos em labels/descriptions — nomes de setores ou funções.
# Acoplar capability a identity é o anti-pattern que o Epic 1 elimina.
FORBIDDEN_IDENTITY_TOKENS = (
    "DAT",
    "Controle",
    "Superintend",  # casa Superintendência, Superintendencia
    "Gerência",
    "Gerencia",
    "Coordenação",
    "Coordenacao",
    "Coordenador",
    "Apoio",
    "Formador",
    "Diretoria",
    "Comercial",
    "Relacionamento",
)

# Categorias válidas após o Epic 1 (ver master-plan §3.4).
# Removidas: admin_dat, gerencia (acopladas a identity).
# Adicionadas: cadastros_administrativos, supervisao.
VALID_CATEGORIES = frozenset(
    {
        "solicitacao",
        "importacao",
        "cadastros_administrativos",
        "dashboard",
        "operacao",
        "supervisao",
    }
)


def test_labels_are_capability_oriented():
    """Nenhum label de FunctionalPermissionSeed pode conter nome de setor/função.

    Match por word-boundary para não gerar falso positivo em adjetivos
    descritivos de capacidade (ex: "gerencial" não é "Gerência").
    """
    offenders: list[tuple[str, str, str]] = []
    for seed in FUNCTIONAL_PERMISSIONS_SEED:
        for token in FORBIDDEN_IDENTITY_TOKENS:
            pattern = rf"\b{re.escape(token)}\b"
            if re.search(pattern, seed.label, flags=re.IGNORECASE):
                offenders.append((seed.codename, "label", token))
                break
    assert not offenders, (
        "Labels devem descrever o que a pessoa PODE FAZER, não QUEM FAZ. "
        f"Ofensores: {offenders}. Ver master-plan §3.2."
    )


def test_descriptions_are_capability_oriented():
    """Nenhuma description pode mencionar nome de setor/função."""
    offenders: list[tuple[str, str, str]] = []
    for seed in FUNCTIONAL_PERMISSIONS_SEED:
        for token in FORBIDDEN_IDENTITY_TOKENS:
            # Match whole-word via word boundary para evitar false positive
            # em palavras compostas (ex: "DATA" vs "DAT").
            pattern = rf"\b{re.escape(token)}\b"
            if re.search(pattern, seed.description, flags=re.IGNORECASE):
                offenders.append((seed.codename, "description", token))
                break
    assert not offenders, (
        "Descriptions devem descrever capacidade, não identidade organizacional. " f"Ofensores: {offenders}."
    )


def test_categories_are_in_canonical_vocabulary():
    """Categorias de FunctionalPermissionSeed devem ser do vocabulário canônico."""
    invalid: list[tuple[str, str]] = []
    for seed in FUNCTIONAL_PERMISSIONS_SEED:
        if seed.category not in VALID_CATEGORIES:
            invalid.append((seed.codename, seed.category))
    assert not invalid, (
        f"Categorias fora do vocabulário canônico ({sorted(VALID_CATEGORIES)}): " f"{invalid}. Ver master-plan §3.4."
    )


def test_labels_follow_infinitive_verb_form():
    """
    Labels devem começar com verbo infinitivo (convenção Nielsen Norman).

    Aceita verbos em infinitivo: Aprovar, Criar, Importar, Administrar,
    Visualizar, Executar, Operar, Exercer, Editar, etc.

    Rejeita: gerúndio (-ando/-endo), substantivação (Aprovação), adjetivo
    puro (Owner), nome de módulo (Dashboard, Map).
    """
    # Verbos conhecidos esperados no domínio — lista positiva (whitelist).
    ACCEPTED_VERBS = {
        "Aprovar",
        "Reprovar",
        "Criar",
        "Importar",
        "Exportar",
        "Executar",
        "Administrar",
        "Gerenciar",
        "Visualizar",
        "Consultar",
        "Operar",
        "Exercer",
        "Editar",
        "Publicar",
        "Cancelar",
        "Atribuir",
    }
    offenders: list[tuple[str, str]] = []
    for seed in FUNCTIONAL_PERMISSIONS_SEED:
        first_word = seed.label.split()[0] if seed.label else ""
        if first_word not in ACCEPTED_VERBS:
            offenders.append((seed.codename, seed.label))
    assert not offenders, (
        "Labels devem começar com verbo infinitivo (ver master-plan §3.2). "
        f"Verbos aceitos: {sorted(ACCEPTED_VERBS)}. Ofensores: {offenders}."
    )


def test_seed_count_stays_fourteen():
    """
    Epic 1 não adiciona nem remove permissões. Epic 3 adicionará a 15ª
    (view_all_availability); até lá o count permanece 14.
    """
    assert len(FUNCTIONAL_PERMISSIONS_SEED) == 14, (
        f"Epic 1 não deve alterar o count de permissões (esperado 14, achei "
        f"{len(FUNCTIONAL_PERMISSIONS_SEED)}). Epic 3 adicionará "
        "view_all_availability."
    )


def test_codenames_unchanged_by_epic_1():
    """
    Epic 1 é puro rename de texto user-visible. Codenames (identificadores
    internos) só mudam no Epic 4 (dual-write).
    """
    expected_codenames = frozenset(
        {
            "pode_aprovar_superintendencia",
            "pode_aprovar_gerente_superintendencia",
            "pode_gerenciar_superintendencia_only",
            "pode_criar_solicitacao_coord_dat",
            "pode_importar_controle_super",
            "pode_operar_dat",
            "pode_acessar_dashboard_compras",
            "pode_operar_dat_exclusivo",
            "pode_operar_controle_dat",
            "pode_operar_controle",
            "pode_operar_gerencia",
            "pode_acessar_dashboard_overview",
            "pode_acessar_map_metrics",
            "pode_editar_como_owner_ou_privilegiado",
        }
    )
    actual = frozenset(seed.codename for seed in FUNCTIONAL_PERMISSIONS_SEED)
    assert actual == expected_codenames, (
        "Epic 1 não deve alterar codenames. Diferença: "
        f"faltando {expected_codenames - actual}, extras {actual - expected_codenames}"
    )
