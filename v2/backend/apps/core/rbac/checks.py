"""
Django system checks do RBAC (Wave B do refactor de composites, H2, 2026-09-15).

`check_approver_composites` é a guarda de drift: valida, em memória (sem DB), que
todo nome em `APPROVER_COMPOSITES` (SSOT dos composites aprovadores) existe em
`SETOR_GROUPS`/`FUNCAO_GROUPS` (`apps.core.constants`). Se alguém renomear um grupo
de composite em `constants.py` sem atualizar a SSOT, `manage.py check` (rodado no
CI e no deploy) FALHA — em vez de o sistema deixar de reconhecer aprovadores em
silêncio (fail-open em `can_admin_mutate_target`). Registrado em `CoreConfig.ready()`.
"""

# pyright: reportMissingTypeStubs=false, reportUntypedFunctionDecorator=false, reportUnknownVariableType=false, reportImplicitStringConcatenation=false

from __future__ import annotations

from typing import Any

from django.core.checks import CheckMessage, Error, register

from apps.core.constants import FUNCAO_GROUPS, SETOR_GROUPS
from apps.core.rbac import helpers


@register()
def check_approver_composites(app_configs: Any, **kwargs: Any) -> list[CheckMessage]:
    """Cada (setor, função) de `APPROVER_COMPOSITES` tem que existir nas constantes.

    Lê `helpers.APPROVER_COMPOSITES` em tempo de chamada (não importa o nome), para
    que a guarda acompanhe a SSOT — e para ser testável via patch.
    """
    errors: list[CheckMessage] = []
    setores = set(SETOR_GROUPS)
    funcoes = set(FUNCAO_GROUPS)
    for setor, funcao in helpers.APPROVER_COMPOSITES:
        if setor not in setores:
            errors.append(
                Error(
                    f"APPROVER_COMPOSITES referencia o setor '{setor}', ausente de SETOR_GROUPS.",
                    hint="Rename de grupo? Atualize apps.core.rbac.helpers.APPROVER_COMPOSITES e "
                    "apps.core.constants.SETOR_GROUPS juntos (+ migração que renomeia o Group).",
                    id="core.E010",
                )
            )
        if funcao not in funcoes:
            errors.append(
                Error(
                    f"APPROVER_COMPOSITES referencia a função '{funcao}', ausente de FUNCAO_GROUPS.",
                    hint="Rename de grupo? Atualize apps.core.rbac.helpers.APPROVER_COMPOSITES e "
                    "apps.core.constants.FUNCAO_GROUPS juntos (+ migração que renomeia o Group).",
                    id="core.E011",
                )
            )
    return errors
