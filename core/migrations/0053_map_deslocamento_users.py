from django.db import migrations


def forwards(apps, schema_editor):
    Desloc = apps.get_model("core", "Deslocamento")
    # Mapear pessoa_1..pessoa_6 (Formador) -> pessoa_1_user..pessoa_6_user (Usuario)
    batch = []
    for d in Desloc.objects.all().iterator():
        updates = {}
        for i in range(1, 7):
            f = getattr(d, f"pessoa_{i}", None)
            if f and getattr(f, "usuario_id", None):
                updates[f"pessoa_{i}_user_id"] = f.usuario_id
        if updates:
            Desloc.objects.filter(pk=d.pk).update(**updates)


def backwards(apps, schema_editor):
    # Não reverter mapeamento
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0052_remove_marcadorplanilha_disponibilidade_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
