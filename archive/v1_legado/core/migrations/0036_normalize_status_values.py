# core/migrations/0036_normalize_status_values.py
from django.db import migrations

TO_CANON = {
    # Legados → canônicos
    "PRE_AGENDA": "AGENDADO",
    "PreAgenda": "AGENDADO",
    "pre_agenda": "AGENDADO",

    "CONCLUIDO": "REALIZADO",
    "Concluido": "REALIZADO",
    "Concluído": "REALIZADO",

    # (Se existirem legados ainda no banco, normalizar)
    "PENDENTE": "CRIADO",
    "Pendente": "CRIADO",
    "REPROVADO": "CRIADO",
    "Reprovado": "CRIADO",

    # Identidade (idempotência)
    "AGENDADO": "AGENDADO",
    "APROVADO": "APROVADO",
    "REALIZADO": "REALIZADO",
    "CANCELADO": "CANCELADO",
    "CRIADO": "CRIADO",
}

def forwards(apps, schema_editor):
    Solicitacao = apps.get_model("core", "Solicitacao")
    total = 0
    for old, new in TO_CANON.items():
        updated = Solicitacao.objects.filter(status=old).update(status=new)
        total += updated
    print(f"[normalize_status] registros atualizados: {total}")

def backwards(apps, schema_editor):
    # Best-effort: não reverte para legados.
    pass

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0035_add_origem_to_marcador_planilha"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
