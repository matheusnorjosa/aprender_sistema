"""PR 13 hardening RBAC (2026-05-04): adiciona `created_by` em AvailabilityBlock.

Contexto
--------

O fluxo atual permite apenas que o owner crie seu próprio bloqueio
(`usuario=request.user`). PR 13 introduz delegação: Asst Admin Controle,
DAT e Superuser podem criar bloqueio em nome de um Formador.

Para auditoria, separamos `usuario` (target — quem está bloqueado) de
`created_by` (quem digitou). `created_by != usuario` indica delegação.

- Registros antigos ficam com `created_by = NULL` (não há identidade
  histórica retroativa; o owner já é `usuario`).
- Novos registros próprios salvam `created_by = request.user` (== usuario).
- Bloqueios delegados salvam `created_by = request.user`, `usuario = target`.

`on_delete=SET_NULL` preserva o histórico de bloqueios mesmo se o
delegate for desativado/excluído (auditoria sobrevive ao usuário).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0081_create_assistente_administrativo_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="availabilityblock",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="availability_blocks_created",
                to=settings.AUTH_USER_MODEL,
                help_text=(
                    "Usuario que criou o bloqueio. Quando != usuario, " "indica delegação (PR 13 hardening RBAC)."
                ),
            ),
        ),
    ]
