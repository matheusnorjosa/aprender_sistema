from django.db import migrations, models
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0056_remove_marcadorplanilha_disponibilidade_and_more'),
    ]
    operations = [
        migrations.AlterField(
            model_name='deslocamento',
            name='pessoa_1',
            field=models.ForeignKey(null=True, blank=True, to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='deslocamentos_1'),
        ),
        migrations.AlterField(
            model_name='deslocamento',
            name='pessoa_2',
            field=models.ForeignKey(null=True, blank=True, to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='deslocamentos_2'),
        ),
    ]
