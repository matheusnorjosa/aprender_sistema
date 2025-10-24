# Generated manually for PR19 - RF06
# Add meet_link field to Solicitacao model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_change_outros_to_nao_super'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='meet_link',
            field=models.URLField(
                blank=True,
                help_text='Link do Google Meet gerado automaticamente (RF06)',
                max_length=500,
                null=True,
                verbose_name='Link do Google Meet'
            ),
        ),
    ]
