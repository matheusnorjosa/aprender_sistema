# Generated manually - Migration to add usuario fields
# Step 1 of 3: Add fields as nullable

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0036_normalize_status_values"),
    ]

    operations = [
        # Add usuario field to DisponibilidadeFormadores (nullable)
        migrations.AddField(
            model_name="disponibilidadeformadores",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="disponibilidades",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Formador",
            ),
        ),
        # Add usuario field to FormadoresSolicitacao (nullable)
        migrations.AddField(
            model_name="formadoressolicitacao",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
                verbose_name="Formador",
            ),
        ),
    ]
