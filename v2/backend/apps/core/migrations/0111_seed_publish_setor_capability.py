"""#1656 Feature 2: capability `publish_setor_solicitacao` (Apoio de Coordenação).

Contexto
--------

Uma Apoio de Coordenação precisa publicar/prever/resincronizar/cancelar no Google
Calendar os eventos APROVADOS do PRÓPRIO setor (qualquer criador), sem virar global
e sem poder editar/excluir eventos alheios. A capability dedicada é referenciada
pela Policy `CanPublishSetorSolicitacao` (composta via OR com `CanUseGcal` nos 4
@actions GCal do `SolicitacaoViewSet`); o alcance de objeto vem do tier aditivo em
`scope_solicitacoes`, e a edição segue barrada por `user_can_access_solicitacao`
(inalterado).

NÃO estende `use_gcal` de propósito: essa policy porteia os endpoints GCal em lote
(`views_gcal/*`) sem escopo por id.

Idempotente / ADITIVO
---------------------

- `update_or_create` na PermissaoFuncional (mesmo padrão do seed em código).
- `groups.add(...)` (ADITIVO) — NUNCA `.set()`/`.clear()`, para não pisar em
  vínculos Group × Capability geridos via admin UI. Re-rodar é no-op.

Reverse: remove o grupo do vínculo e deleta a capability.
"""

from __future__ import annotations

from django.db import migrations

CODENAME = "publish_setor_solicitacao"
LABEL = "Publicar eventos do setor na agenda"
DESCRIPTION = (
    "Publicar/prever/resincronizar/cancelar no Google Calendar os eventos "
    "APROVADOS do próprio setor (qualquer criador), escopado por vínculo "
    "EquipeGerencia. NÃO concede edição/exclusão de eventos de terceiros "
    "(a checagem de objeto continua em `user_can_access_solicitacao`) nem "
    "acesso aos endpoints GCal em lote (`use_gcal`). #1656 Feature 2."
)
CATEGORY = "solicitacao"
GROUP_NAME = "Apoio de Coordenação"


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
    # noqa abaixo: seed ADITIVO do grupo default de uma capability NOVA (#1656 F2).
    # Uso legítimo do escape D17/V003 — `.add()` (não `.set()`/`.clear()`) preserva
    # vínculos Group × Capability geridos via admin UI; sem isto a cap nasceria sem
    # grupo no `migrate` de prod e a Apoio só a ganharia por ação manual.
    perm.groups.add(grupo)  # noqa: RBAC-migration-allowed


def backwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")

    perm = PermissaoFuncional.objects.filter(codename=CODENAME).first()
    if perm is not None:
        grupo = Group.objects.filter(name=GROUP_NAME).first()
        if grupo is not None:
            perm.groups.remove(grupo)
        perm.delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0110_dat_compra_check_constraints")]
    operations = [migrations.RunPython(forwards, backwards)]
