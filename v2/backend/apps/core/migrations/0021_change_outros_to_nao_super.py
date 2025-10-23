# Generated manually for PR15
# Renames OUTROS → NAO_SUPER in Projeto.fluxo

from django.db import migrations, models


def migrate_outros_to_nao_super(apps, schema_editor):
    """Update all Projeto rows from OUTROS to NAO_SUPER."""
    Projeto = apps.get_model('core', 'Projeto')
    Projeto.objects.filter(fluxo='OUTROS').update(fluxo='NAO_SUPER')


def reverse_nao_super_to_outros(apps, schema_editor):
    """Reverse: Update all NAO_SUPER back to OUTROS."""
    Projeto = apps.get_model('core', 'Projeto')
    Projeto.objects.filter(fluxo='NAO_SUPER').update(fluxo='OUTROS')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_solicitacao_gcal_last_error_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_outros_to_nao_super,
            reverse_code=reverse_nao_super_to_outros
        ),
        migrations.AlterField(
            model_name='projeto',
            name='fluxo',
            field=models.CharField(
                max_length=12,
                choices=[
                    ('SUPER', 'Superintendência'),
                    ('NAO_SUPER', 'Não-Superintendência'),
                ],
                default='NAO_SUPER',
                db_index=True,
                help_text="SUPER: requer aprovação da Superintendência. NAO_SUPER: auto-aprovado."
            ),
        ),
    ]
