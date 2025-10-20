# Generated manually - Migration to make usuario fields NOT NULL
# Step 3 of 3: Make fields NOT NULL after data migration

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_populate_usuario_from_formador"),
    ]

    operations = [
        # Step 1: Remove old unique_together constraint (references formador)
        migrations.AlterUniqueTogether(
            name="formadoressolicitacao",
            unique_together=set(),  # Remove constraint
        ),
        # Step 2: Remove old uniq_formador_intervalo constraint
        migrations.RemoveConstraint(
            model_name="disponibilidadeformadores",
            name="uniq_formador_intervalo",
        ),
        # Step 3: Make usuario fields NOT NULL
        migrations.AlterField(
            model_name="disponibilidadeformadores",
            name="usuario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="disponibilidades",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Formador",
            ),
        ),
        migrations.AlterField(
            model_name="formadoressolicitacao",
            name="usuario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
                verbose_name="Formador",
            ),
        ),
        # Step 4: Remove old formador fields
        migrations.RemoveField(
            model_name="disponibilidadeformadores",
            name="formador",
        ),
        migrations.RemoveField(
            model_name="formadoressolicitacao",
            name="formador",
        ),
        # Step 5: Add new constraints using usuario
        migrations.AlterUniqueTogether(
            name="formadoressolicitacao",
            unique_together={("solicitacao", "usuario")},
        ),
        migrations.AddConstraint(
            model_name="disponibilidadeformadores",
            constraint=models.UniqueConstraint(
                fields=("usuario", "data_bloqueio", "hora_inicio", "hora_fim"),
                name="uniq_usuario_intervalo",
            ),
        ),
    ]
