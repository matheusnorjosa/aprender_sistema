"""Vigência (valid_from/valid_to) para EquipeGerencia — 1 janela por vínculo.

Domínio temporal (irmão de 0089-0093): o vínculo de equipe passa a ter uma janela
[valid_from, valid_to] além do kill-switch `ativo`. "vigente hoje" = ativo E hoje na janela.
Mantém a NK (gerencia, usuario, papel) — UMA linha por vínculo (writer reabre a mesma).

Ordem (para não preencher HOJE em vez da data real):
1. AddField valid_from nullable SEM default; valid_to nullable.
2. Backfill: valid_from = data local (Fortaleza) de created_at; valid_to = data local de
   updated_at só para inativos (ativo=False), senão NULL (janela aberta).
3. AlterField valid_from → default=timezone.localdate + NOT NULL (estado final = model).
4. AddConstraint CheckConstraint valid_to IS NULL OR valid_to >= valid_from.

⚠️ `backend-migrate-integrity` roda em DB VAZIO → o backfill vira no-op no CI. Validar o
backfill num clone golden/prod-like antes do apply real. `valid_to` de inativos LEGADOS é
aproximado (updated_at muda em qualquer edição); vínculos novos nascem exatos.
"""

from django.db import migrations, models
from django.utils import timezone


def backfill_vigencia(apps, schema_editor):
    EquipeGerencia = apps.get_model("core", "EquipeGerencia")
    updates = []
    for e in EquipeGerencia.objects.all().only("id", "created_at", "updated_at", "ativo"):
        # localtime → data no fuso de exibição (America/Fortaleza), evita drift de borda UTC.
        e.valid_from = timezone.localtime(e.created_at).date()
        e.valid_to = None if e.ativo else timezone.localtime(e.updated_at).date()
        updates.append(e)
    if updates:
        EquipeGerencia.objects.bulk_update(updates, ["valid_from", "valid_to"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0093_dat_cadastro_ano_nk"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipegerencia",
            name="valid_from",
            field=models.DateField(
                null=True,
                help_text="Início da vigência do vínculo (inclusive).",
            ),
        ),
        migrations.AddField(
            model_name="equipegerencia",
            name="valid_to",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Fim da vigência (inclusive); NULL = janela aberta / vigente.",
            ),
        ),
        migrations.RunPython(backfill_vigencia, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="equipegerencia",
            name="valid_from",
            field=models.DateField(
                default=timezone.localdate,
                help_text="Início da vigência do vínculo (inclusive).",
            ),
        ),
        migrations.AddConstraint(
            model_name="equipegerencia",
            constraint=models.CheckConstraint(
                condition=(models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=models.F("valid_from"))),
                name="equipe_gerencia_valid_window",
                violation_error_message="valid_to deve ser vazio ou >= valid_from",
            ),
        ),
    ]
