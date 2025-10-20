# Generated migration for custom permissions
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_setup_groups_permissions'),
    ]

    operations = [
        # Add custom permissions to existing models
        migrations.AlterModelOptions(
            name='solicitacao',
            options={
                'ordering': ['-data_solicitacao'],
                'permissions': [
                    ('sync_calendar', 'Can sync with Google Calendar'),
                    ('view_own_solicitacoes', 'Can view own solicitações (Coordenador)'),
                    ('view_all_solicitacoes', 'Can view all solicitações'),
                    ('view_calendar', 'Can view calendar'),
                ]
            },
        ),
        migrations.AlterModelOptions(
            name='aprovacao',
            options={
                'ordering': ['-data_aprovacao'],
                'permissions': []
            },
        ),
        migrations.AlterModelOptions(
            name='logauditoria',
            options={
                'ordering': ['-data_hora'],
                'permissions': [
                    ('view_relatorios', 'Can view consolidated reports'),
                ]
            },
        ),
        migrations.AlterModelOptions(
            name='formador',
            options={
                'ordering': ['nome'],
                'permissions': [
                    ('view_own_events', 'Can view own events (Formador)'),
                ]
            },
        ),
    ]