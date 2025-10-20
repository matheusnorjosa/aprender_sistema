# Generated manually for RF05
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_deslocamento'),
    ]

    operations = [
        # Renomear google_calendar_id para provider_event_id
        migrations.RenameField(
            model_name='eventogooglecalendar',
            old_name='google_calendar_id',
            new_name='provider_event_id',
        ),
        # Renomear link_evento para html_link
        migrations.RenameField(
            model_name='eventogooglecalendar',
            old_name='link_evento',
            new_name='html_link',
        ),
        # Renomear link_meet para meet_link
        migrations.RenameField(
            model_name='eventogooglecalendar',
            old_name='link_meet',
            new_name='meet_link',
        ),
        # Adicionar campo raw_payload
        migrations.AddField(
            model_name='eventogooglecalendar',
            name='raw_payload',
            field=models.JSONField(blank=True, null=True, verbose_name='Payload bruto da resposta'),
        ),
        # Atualizar índice
        migrations.RemoveIndex(
            model_name='eventogooglecalendar',
            name='core_evento_google__8bfd32_idx',
        ),
        migrations.AddIndex(
            model_name='eventogooglecalendar',
            index=models.Index(fields=['provider_event_id'], name='core_eventog_provide_b7f45d_idx'),
        ),
        # Adicionar verboses e atualizar o modelo
        migrations.AlterField(
            model_name='eventogooglecalendar',
            name='provider_event_id',
            field=models.CharField(max_length=255, verbose_name='ID do evento no provedor'),
        ),
        migrations.AlterField(
            model_name='eventogooglecalendar',
            name='html_link',
            field=models.TextField(blank=True, null=True, verbose_name='Link do evento'),
        ),
        migrations.AlterField(
            model_name='eventogooglecalendar',
            name='meet_link',
            field=models.TextField(blank=True, null=True, verbose_name='Link do Meet'),
        ),
    ]