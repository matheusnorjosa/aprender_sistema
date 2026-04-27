"""C3 fix (Onda 1, PR fix/rbac-critical-divergences-wave1, 2026-04-27):
adiciona capability `manage_internal_actions` com ZERO grupos atribuídos.

Contexto
--------

`CicloAcoesViewSet` e `AcaoInstanciaViewSet` usavam `[IsAdminUser]` (DRF
built-in que checa `is_staff=True`, não `is_superuser`), bypassando o
Capability Policy Layer e contradizendo a intent matrix da memória
`reference_rbac_intent_matrix.md` que declara o módulo como superuser-only
durante desenvolvimento.

Fix em código (mesmo PR): substituir `[IsAdminUser]` por
`[HasPerm("manage_internal_actions")]`. Como a capability tem 0 grupos
atribuídos por seed, apenas superuser passa (via bypass natural de
`HasPerm`).

Quando a feature for liberada para outros papéis (DAT, Diretoria, etc.):
basta atribuir o grupo via admin UI (`/admin/grupos`) ou nova migration
data-only — zero code change necessário. Esse é o padrão correto da
camada Policy.

Idempotente
-----------

Usa `update_or_create` em PermissaoFuncional + `groups.set([])` (vazio).
Re-rodar é no-op.
"""

from __future__ import annotations

from django.db import migrations

CODENAME = "manage_internal_actions"
LABEL = "Administrar ações internas"
DESCRIPTION = (
    "CRUD de templates de ações, ciclos, instâncias e notificações "
    "internas. Feature em desenvolvimento — capability sem grupos "
    "atribuídos por padrão (apenas superuser bypassa por ora). Quando "
    "a feature for liberada, atribuir via admin UI ao papel correto."
)
CATEGORY = "cadastros_administrativos"


def forwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    perm, _ = PermissaoFuncional.objects.update_or_create(
        codename=CODENAME,
        defaults={
            "label": LABEL,
            "description": DESCRIPTION,
            "category": CATEGORY,
            "is_system": True,
        },
    )
    perm.groups.set([])


def backwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    PermissaoFuncional.objects.filter(codename=CODENAME).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0078_scope_view_all_availability")]
    operations = [migrations.RunPython(forwards, backwards)]
