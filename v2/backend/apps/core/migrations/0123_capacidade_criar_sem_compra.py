"""Regra da compra (decisão do dono, 14/10/2026): capacidade `create_solicitation_without_purchase`.

Quem a tem cria evento em par (município, projeto) sem compra que o libere, como o superusuário. É
checada só em `services/compra_elegibilidade.isento_da_regra_da_compra`.

Nasce SEM grupo nenhum: entra no pacote do DAT (ADMIN_OPERACIONAL) num PR próprio, com `rbac_diff`
medido. Até lá ninguém muda de poder; só o superusuário fica isento. Esta migration não toca em
vínculo Grupo × Capability.

Idempotente (`update_or_create`). Reverse apaga a capacidade.
"""

from __future__ import annotations

from django.db import migrations

CODENAME = "create_solicitation_without_purchase"
LABEL = "Criar solicitações sem compra"
DESCRIPTION = (
    "Criar e editar evento em município e projeto sem compra que os libere (isenção da regra da "
    "compra). Sem grupo atribuído por padrão: só o superusuário passa."
)
CATEGORY = "solicitacao"


def forwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    PermissaoFuncional.objects.update_or_create(
        codename=CODENAME,
        defaults={"label": LABEL, "description": DESCRIPTION, "category": CATEGORY, "is_system": True},
    )


def backwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    PermissaoFuncional.objects.filter(codename=CODENAME).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0122_projeto_eh_nome_geral")]
    operations = [migrations.RunPython(forwards, backwards)]
