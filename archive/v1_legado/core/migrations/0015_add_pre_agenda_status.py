# Generated manually for adding PRE_AGENDA status

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_add_vinculado_superintendencia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitacao',
            name='status',
            field=models.CharField(
                choices=[
                    ('Pendente', 'Pendente'), 
                    ('PreAgenda', 'Pré-Agenda'), 
                    ('Aprovado', 'Aprovado'), 
                    ('Reprovado', 'Reprovado')
                ], 
                default='Pendente', 
                max_length=20
            ),
        ),
    ]