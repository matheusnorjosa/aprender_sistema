# Generated manually - Fix TipoEvento online flags

from django.db import migrations


def fix_online_flags(apps, schema_editor):
    """Corrige flags online para tipos de evento específicos"""
    TipoEvento = apps.get_model('core', 'TipoEvento')
    
    # Garantir que "Formação Online" tenha online=True
    online_tipos = [
        "Formação Online",
        "Workshop Online",
        "Capacitação Online",
        "Treinamento Online",
    ]
    
    for tipo_nome in online_tipos:
        TipoEvento.objects.filter(
            nome__icontains="online"
        ).update(online=True)
    
    # Garantir que tipos presenciais tenham online=False
    presencial_tipos = [
        "Formação Presencial",
        "Workshop Presencial", 
        "Capacitação Presencial",
        "Treinamento Presencial",
    ]
    
    for tipo_nome in presencial_tipos:
        TipoEvento.objects.filter(
            nome__icontains="presencial"
        ).update(online=False)
    
    # Log das mudanças
    print("Flags online corrigidas para TipoEvento")


def reverse_fix_online_flags(apps, schema_editor):
    """Reverter não é necessário, flags já estão corretas"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_add_pre_agenda_status'),
    ]

    operations = [
        migrations.RunPython(
            fix_online_flags,
            reverse_fix_online_flags,
        ),
    ]