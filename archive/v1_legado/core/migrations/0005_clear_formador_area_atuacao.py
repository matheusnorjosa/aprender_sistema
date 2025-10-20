# Clear existing area_atuacao data before changing field type
from django.db import migrations

def clear_area_atuacao(apps, schema_editor):
    """Clear existing area_atuacao data to prepare for field type change"""
    Formador = apps.get_model('core', 'Formador')
    Formador.objects.update(area_atuacao=None)

def reverse_clear_area_atuacao(apps, schema_editor):
    """No reverse operation needed"""
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_rf05_calendar_fields'),
    ]

    operations = [
        migrations.RunPython(clear_area_atuacao, reverse_clear_area_atuacao),
    ]