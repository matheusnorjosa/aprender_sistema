# Data migration - Rename status values
# PRE_AGENDA → AGENDADO
# CONCLUIDO → REALIZADO (if exists)

from django.db import migrations

OLD_PRE = "PreAgenda"
NEW_AGD = "Agendado"
OLD_CONC = "Concluido"  # Pode não existir ainda
NEW_REAL = "Realizado"


def forwards(apps, schema_editor):
    Solicitacao = apps.get_model("core", "Solicitacao")

    # Trocas diretas em lote (eficiente)
    updated_pre = Solicitacao.objects.filter(status=OLD_PRE).update(status=NEW_AGD)
    updated_conc = Solicitacao.objects.filter(status=OLD_CONC).update(status=NEW_REAL)

    print(f"✅ Status renomeados: PRE_AGENDA→AGENDADO ({updated_pre}), CONCLUIDO→REALIZADO ({updated_conc})")


def backwards(apps, schema_editor):
    Solicitacao = apps.get_model("core", "Solicitacao")

    # Reverter para status antigos
    Solicitacao.objects.filter(status=NEW_AGD).update(status=OLD_PRE)
    Solicitacao.objects.filter(status=NEW_REAL).update(status=OLD_CONC)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_add_canonical_models_and_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
