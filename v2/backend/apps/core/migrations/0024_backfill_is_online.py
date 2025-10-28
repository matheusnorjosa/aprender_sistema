from django.db import migrations


def forwards(apps, schema_editor):
    Solicitacao = apps.get_model("core", "Solicitacao")
    # Setar is_online=True quando já existe meet_link persistido
    Solicitacao.objects.filter(meet_link__isnull=False).exclude(meet_link="").update(is_online=True)


def backwards(apps, schema_editor):
    Solicitacao = apps.get_model("core", "Solicitacao")
    # Não é seguro inferir o inverso; manter como NOOP
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0023_add_is_online"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

