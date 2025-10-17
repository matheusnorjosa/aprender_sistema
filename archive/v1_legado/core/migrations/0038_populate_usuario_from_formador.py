# Generated manually - Data migration to populate usuario fields
# Step 2 of 3: Fill usuario from formador.usuario_id

from django.db import migrations


def populate_usuario_fields(apps, schema_editor):
    """
    Popula os campos usuario em DisponibilidadeFormadores e FormadoresSolicitacao
    a partir do campo formador.usuario_id existente.
    """
    DisponibilidadeFormadores = apps.get_model("core", "DisponibilidadeFormadores")
    FormadoresSolicitacao = apps.get_model("core", "FormadoresSolicitacao")
    Formador = apps.get_model("core", "Formador")

    # 1. Populate DisponibilidadeFormadores.usuario from formador_id->usuario_id
    updated_disp = 0
    for disp in DisponibilidadeFormadores.objects.select_related("formador").all():
        if disp.formador and disp.formador.usuario_id:
            disp.usuario_id = disp.formador.usuario_id
            disp.save(update_fields=["usuario_id"])
            updated_disp += 1

    # 2. Populate FormadoresSolicitacao.usuario from formador_id->usuario_id
    updated_form_sol = 0
    for form_sol in FormadoresSolicitacao.objects.select_related("formador").all():
        if form_sol.formador and form_sol.formador.usuario_id:
            form_sol.usuario_id = form_sol.formador.usuario_id
            form_sol.save(update_fields=["usuario_id"])
            updated_form_sol += 1

    print(
        f"✅ Populated {updated_disp} DisponibilidadeFormadores and {updated_form_sol} FormadoresSolicitacao records"
    )


def reverse_populate(apps, schema_editor):
    """
    Reversão: limpar campos usuario (retornar para NULL).
    """
    DisponibilidadeFormadores = apps.get_model("core", "DisponibilidadeFormadores")
    FormadoresSolicitacao = apps.get_model("core", "FormadoresSolicitacao")

    DisponibilidadeFormadores.objects.all().update(usuario_id=None)
    FormadoresSolicitacao.objects.all().update(usuario_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0037_add_usuario_fields"),
    ]

    operations = [
        migrations.RunPython(populate_usuario_fields, reverse_code=reverse_populate),
    ]
