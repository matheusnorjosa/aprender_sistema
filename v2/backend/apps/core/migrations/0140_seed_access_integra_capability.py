"""Integra (decisão do dono de 24/11/2026, Q9): capability `access_integra`.

Contexto
--------

A Integra é o protótipo das ferramentas do gestor pedagógico (ICA, Semáforo, DFF) para a validação de
07/12/2026, com dados simulados na tela. Abrem a página o superusuário, a Diretoria e a gerente da
Superintendência. A capacidade vem do pacote DIRETORIA (`services/rbac_pacotes.py`); a gerente da
Superintendência entra pelo vínculo GERENTE vigente, na policy composta `access_integra`
(`rbac/policies.py`), sem passar por esta capacidade.

O grupo Diretoria recebe a capacidade porque o seed é a matriz (`rbac_diff --auditar`) e o pacote
DIRETORIA fica contido no grupo do seed (`test_pacote_contido_no_grupo_do_seed`). Desde o PR 12 o grupo é
etiqueta: ele só dá poder no modo de emergência `RBAC_FONTE=uniao`.

Idempotente / ADITIVO
---------------------

- `update_or_create` na PermissaoFuncional (mesmo padrão do seed em código).
- `groups.add(...)` (ADITIVO): NUNCA `.set()`/`.clear()`, para não pisar em vínculos Group × Capability
  geridos pela tela. Re-rodar é no-op.

Reverse: remove o grupo do vínculo e apaga a capacidade.
"""

from __future__ import annotations

from django.db import migrations

CODENAME = "access_integra"
LABEL = "Visualizar a Integra"
DESCRIPTION = (
    "Abrir a Integra, a página das ferramentas do gestor pedagógico (ICA, Semáforo e DFF). No "
    "protótipo os dados são simulados na tela e nada é gravado no banco."
)
CATEGORY = "dashboard"
GROUP_NAME = "Diretoria"


def forwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")

    perm, _ = PermissaoFuncional.objects.update_or_create(
        codename=CODENAME,
        defaults={
            "label": LABEL,
            "description": DESCRIPTION,
            "category": CATEGORY,
            "is_system": True,
        },
    )
    grupo, _ = Group.objects.get_or_create(name=GROUP_NAME)
    # noqa abaixo: seed ADITIVO do grupo default de uma capability NOVA (Integra). Uso legítimo do escape
    # D17/V003: `.add()` (não `.set()`/`.clear()`) preserva os vínculos geridos pela tela; sem isto o
    # `rbac_diff --auditar` acusaria o par (Diretoria, access_integra) do seed fora do banco.
    perm.groups.add(grupo)  # noqa: RBAC-migration-allowed


def backwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")

    perm = PermissaoFuncional.objects.filter(codename=CODENAME).first()
    if perm is not None:
        grupo = Group.objects.filter(name=GROUP_NAME).first()
        if grupo is not None:
            perm.groups.remove(grupo)  # noqa: RBAC-migration-allowed
        perm.delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0139_solicitacao_cancelado_na_agenda")]
    operations = [migrations.RunPython(forwards, backwards)]
