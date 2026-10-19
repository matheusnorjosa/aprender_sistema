"""Descriptions de duas capacidades que ficaram para trás (item 36a, alinhamento de 19/10/2026).

- `create_solicitation_without_purchase`: dizia "só o superusuário passa", mas desde o PR 10 a capacidade
  está no pacote do perfil administrador operacional (`rbac_pacotes.PACOTE`).
- `manage_internal_actions`: mandava "atribuir via admin UI", e desde a D4 do ADR-020 a matriz só muda
  por PR.

Só o texto mostrado ao admin muda: label, categoria e vínculos Grupo × Capability ficam como estão.
Espelha `services/functional_permissions_seed.py`. Idempotente; reverse volta o texto anterior.
"""

from __future__ import annotations

from django.db import migrations

DESCRICOES_ANTIGAS = {
    "create_solicitation_without_purchase": (
        "Criar e editar evento em município e projeto sem compra que os libere (isenção da regra da "
        "compra). Sem grupo atribuído por padrão: só o superusuário passa."
    ),
    "manage_internal_actions": (
        "CRUD de templates de ações, ciclos, instâncias e notificações "
        "internas. Feature em desenvolvimento — capability sem grupos "
        "atribuídos por padrão (apenas superuser bypassa por ora). Quando "
        "a feature for liberada, atribuir via admin UI ao papel correto."
    ),
}

DESCRICOES_NOVAS = {
    "create_solicitation_without_purchase": (
        "Criar e editar evento em município e projeto sem compra que os libere (isenção da regra da "
        "compra). Sem grupo: vem do pacote do perfil administrador operacional e do superusuário."
    ),
    "manage_internal_actions": (
        "CRUD de templates de ações, ciclos, instâncias e notificações "
        "internas. Feature em desenvolvimento — capability sem grupos e "
        "fora de todo pacote de perfil (apenas superuser bypassa por ora). "
        "Liberar = PR que põe a capacidade no pacote de um perfil (D4 do ADR-020)."
    ),
}


def _grava(apps, descricoes: dict[str, str]) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    for codename, descricao in descricoes.items():
        PermissaoFuncional.objects.filter(codename=codename).update(description=descricao)


def forwards(apps, schema_editor):
    _grava(apps, DESCRICOES_NOVAS)


def backwards(apps, schema_editor):
    _grava(apps, DESCRICOES_ANTIGAS)


class Migration(migrations.Migration):
    dependencies = [("core", "0128_usuario_aviso_senha_redefinida")]
    operations = [migrations.RunPython(forwards, backwards)]
