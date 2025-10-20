# Generated migration to add usuario field to Formador model
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_assign_permissions_to_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='formador',
            name='usuario',
            field=models.OneToOneField(
                blank=True, 
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='formador_profile',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Usuário'
            ),
        ),
    ]