# Generated manually — fixes M-01 (constraint) and M-03 (on_delete)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0061_alter_acaotemplateexecutor_group"),
    ]

    operations = [
        # M-01: Relax constraint to allow MARCO_CALENDARIO without ref_evento_externo
        migrations.RemoveConstraint(
            model_name="acaotemplate",
            name="acao_template_ancora_evento_requer_ref",
        ),
        migrations.AddConstraint(
            model_name="acaotemplate",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("tipo_ancora__in", ["ACAO_ANTERIOR", "MARCO_CALENDARIO"]),
                    models.Q(("ref_evento_externo", ""), _negated=True),
                    _connector="OR",
                ),
                name="acao_template_ancora_evento_requer_ref",
            ),
        ),
        # M-03: Change NotificacaoInterna.acao_instancia from CASCADE to SET_NULL
        migrations.AlterField(
            model_name="notificacaointerna",
            name="acao_instancia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notificacoes",
                to="core.acaoinstancia",
            ),
        ),
    ]
