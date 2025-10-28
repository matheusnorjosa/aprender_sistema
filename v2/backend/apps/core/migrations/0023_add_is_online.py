# Generated manually for modalidade online/presencial
# Add is_online field to Solicitacao model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_add_meet_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='is_online',
            field=models.BooleanField(
                default=False,
                help_text='Se True, gera Google Meet link no APPLY (RF06). Se False, evento presencial sem conferenceData.',
                verbose_name='Evento Online?'
            ),
        ),
    ]
