"""D4 do ADR-020 (PR A da arquitetura de permissões): a matriz muda por PR, com a migration de dados.

O PR A alinhou o seed (`functional_permissions_seed.py`) à matriz de produção medida em 02/10/2026:
Assistente Administrativo com `manage_purchases_and_materials`, `operate_preagenda` e
`run_daily_operations`, e DAT com `view_map_metrics`. Nenhuma migration até a 0120 grava esses
quatro pares (a 0077 é a última que mexe neles). Sem esta, um banco montado só por `migrate`
(ambiente novo, reconstrução, job migrate-integrity) fica com a matriz antiga e
`rbac_diff --auditar` sai com exit 1.

Em produção os pares já existem (editados pelo Admin antes da D4): aqui é no-op.

ADITIVO e idempotente: `groups.add(...)`, nunca `.set()`/`.clear()`. Reverse é no-op de propósito:
em produção estes pares são anteriores à migration, e removê-los tiraria poder que ela não deu.
"""

from __future__ import annotations

from django.db import migrations

PARES: tuple[tuple[str, str], ...] = (
    ("Assistente Administrativo", "manage_purchases_and_materials"),
    ("Assistente Administrativo", "operate_preagenda"),
    ("Assistente Administrativo", "run_daily_operations"),
    ("DAT", "view_map_metrics"),
)


def forwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")

    for nome_grupo, codename in PARES:
        # Sem a capacidade não há par a gravar: banco de teste reaproveitado (`--reuse-db`) depois
        # de um teste `transaction=True` truncar as tabelas. Num banco real ela existe (0065/0075).
        perm = PermissaoFuncional.objects.filter(codename=codename).first()
        if perm is None:
            continue
        grupo, _ = Group.objects.get_or_create(name=nome_grupo)
        perm.groups.add(grupo)  # noqa: RBAC-migration-allowed


class Migration(migrations.Migration):
    dependencies = [("core", "0120_gerencia_perfil")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
