"""Bug 1 fix follow-up (PR #1248, 2026-04-27): realinha `view_all_availability`
para excluir Coordenador/Apoio de Coordenação.

Contexto
--------

A migration 0077 (Epic 1 do RBAC Access Policy Realignment) atribuiu
`view_all_availability` a 4 grupos: Controle, Gerente, Coordenador, Apoio.
Essa decisão se baseou em intent matrix declarada na memória, mas expôs
ambiguidade do nome quando o E2E journey J05 quebrou:

    coord_fluir tentando ver grade mensal do setor Vidas → 200
    (esperado: 403, conforme regra de privacidade Coord-só-vê-próprio-setor)

Decisão (stakeholder, 2026-04-27)
---------------------------------

`view_all_availability` deve significar literalmente "ver TODAS as
disponibilidades sem restrição de setor". Isso só faz sentido para papéis
com escopo organizacional amplo:

    Controle (operação transversal)
    Gerente  (supervisão transversal)

Coordenador/Apoio são SCOPED — devem cair em `HasSectorAccess` (filtro por
gerência vinculada via EquipeGerencia). A composition em
`MonthlyAvailabilityView`:

    permission_classes = [IsAuthenticated, CanViewAllAvailability | HasSectorAccess]

já implementa o pattern correto:
- Quem tem capability → bypass scope (Controle/Gerente)
- Quem não tem → cai em scope (Coordenador/Apoio respeitam EquipeGerencia)

Mudança vs 0077
---------------

`view_all_availability`:
    Antes: ["Controle", "Gerente", "Coordenador", "Apoio de Coordenação"]
    Agora: ["Controle", "Gerente"]

Idempotente via `groups.set(...)`. Se admin tiver atribuído manualmente a
outro grupo via UI, será sobrescrito — comportamento intencional.
"""

from __future__ import annotations

from django.db import migrations

CODENAME = "view_all_availability"
GROUPS_AFTER = ["Controle", "Gerente"]


def forwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")
    try:
        perm = PermissaoFuncional.objects.get(codename=CODENAME)
    except PermissaoFuncional.DoesNotExist:
        return
    groups = list(Group.objects.filter(name__in=GROUPS_AFTER))
    perm.groups.set(groups)


def backwards(apps, schema_editor):
    """Restaura state da 0077 (4 grupos)."""
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")
    try:
        perm = PermissaoFuncional.objects.get(codename=CODENAME)
    except PermissaoFuncional.DoesNotExist:
        return
    groups = list(Group.objects.filter(name__in=["Controle", "Gerente", "Coordenador", "Apoio de Coordenação"]))
    perm.groups.set(groups)


class Migration(migrations.Migration):
    dependencies = [("core", "0077_realign_funcperm_groups")]
    operations = [migrations.RunPython(forwards, backwards)]
