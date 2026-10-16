"""PR 10 das permissões (ADR-020): o DAT vira o administrador operacional pelo pacote, não pelo grupo.

O pacote `ADMIN_OPERACIONAL` (`services/rbac_pacotes.py`) passa a ser o final e dá ao DAT, pelo
vínculo EQUIPE/GERENTE na gerência DAT, a aprovação (`approve_solicitation`, base 5 de
`solicitation_approval_basis`) e as demais capacidades. Esta migration tira dos grupos o que não
pode ficar neles:

- `import_spreadsheet` do grupo DAT ("técnico só para mim"; nenhuma tela usa). Sem isso a união
  grupo ∪ pacote devolveria a capacidade ao DAT até o PR 12;
- `approve_solicitation` e `execute_restricted_operations` do grupo Superintendência (0 membros em
  produção). Sem isso, quem o superusuário pusesse nesse grupo passaria a aprovar sem vínculo.

A matriz do seed (`functional_permissions_seed.py`) muda junto; `rbac_diff --auditar` segue em 0.
Reverse devolve os três pares.
"""

from __future__ import annotations

from django.db import migrations

PARES: tuple[tuple[str, str], ...] = (
    ("DAT", "import_spreadsheet"),
    ("Superintendência", "approve_solicitation"),
    ("Superintendência", "execute_restricted_operations"),
)


def forwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    for grupo, codename in PARES:
        pares = PermissaoFuncional.groups.through.objects.filter(
            group__name=grupo, permissaofuncional__codename=codename
        )
        pares.delete()  # noqa: RBAC-migration-allowed


def backwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")
    for grupo, codename in PARES:
        perm = PermissaoFuncional.objects.filter(codename=codename).first()
        if perm is None:
            continue
        perm.groups.add(Group.objects.get_or_create(name=grupo)[0])  # noqa: RBAC-migration-allowed


class Migration(migrations.Migration):
    dependencies = [("core", "0125_funcoes_sem_capacidade")]
    operations = [migrations.RunPython(forwards, backwards)]
