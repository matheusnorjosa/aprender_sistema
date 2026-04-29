"""Decisão D9 (2026-04-28): redistribui `view_all_availability` para papéis
realmente transversais.

Contexto
--------

A migration 0078 (2026-04-27) reduziu `view_all_availability` para
`["Controle", "Gerente"]`, removendo Coordenador/Apoio (que caíram em
HasSectorAccess scoped via EquipeGerencia).

Em 2026-04-28, regra de negócio confirmada pelo stakeholder:

- **Gerente pedagógico** (ACerta, Vidas, Fluir, Brincando, Sou da Paz, Gestão
  Escolar, Superintendência) deve ver apenas a própria gerência via vínculo
  EquipeGerencia. Não deve receber visão global por ser Gerente.

- **Gerente da Superintendência** também é scoped (vê apenas Sup) — combinação
  Setor Superintendência + Função Gerente, sem cap global.

- **DAT** é ator transversal admin (suporte, validação, troubleshooting) e
  deve acessar Grade Mensal completa. Recebe a cap global.

- **Controle** mantém cap global (operação transversal cross-setor).

Mudança vs 0078
---------------

`view_all_availability`:
    Antes (0078): ["Controle", "Gerente"]
    Agora (0080): ["Controle", "DAT"]

Idempotente via `groups.set(...)`. Se admin tiver atribuído manualmente a
outro grupo via UI, será sobrescrito — comportamento intencional.

Backend já implementa o pattern correto em `MonthlyAvailabilityView`:

    permission_classes = [IsAuthenticated, CanViewAllAvailability | HasSectorAccess]

Quem tem cap (Controle/DAT) → bypass scope. Quem não tem (Gerente, Coord,
Apoio) → cai em scope via EquipeGerencia (D8 fortaleceu HasSectorAccess
para exigir vínculo ativo).
"""

from __future__ import annotations

from django.db import migrations

CODENAME = "view_all_availability"
GROUPS_AFTER = ["Controle", "DAT"]


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
    """Restaura state da 0078 (Controle, Gerente)."""
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")
    try:
        perm = PermissaoFuncional.objects.get(codename=CODENAME)
    except PermissaoFuncional.DoesNotExist:
        return
    groups = list(Group.objects.filter(name__in=["Controle", "Gerente"]))
    perm.groups.set(groups)


class Migration(migrations.Migration):
    dependencies = [("core", "0079_add_manage_internal_actions")]
    operations = [migrations.RunPython(forwards, backwards)]
