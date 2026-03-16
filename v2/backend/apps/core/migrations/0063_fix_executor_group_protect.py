# Generated manually — revert CASCADE to PROTECT on AcaoTemplateExecutor.group

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0062_fix_acaotemplate_constraint_notificacao_on_delete"),
    ]

    operations = [
        migrations.AlterField(
            model_name="acaotemplateexecutor",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="acoes_template",
                to="auth.group",
            ),
        ),
    ]
