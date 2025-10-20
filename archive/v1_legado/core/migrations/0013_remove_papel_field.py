# Migration to completely remove papel field and finalize transition to Groups
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_usuario_to_formador'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usuario',
            name='papel',
        ),
    ]