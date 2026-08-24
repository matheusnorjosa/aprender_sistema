"""Adiciona `ano` ao PlanoFormacoes + troca a NK para (municipio, projeto, ano).

Última fatia do domínio temporal por ano (irmã de 0092 DATAcao / 0093 DATCadastro). O plano de formações
é ANUAL (a origem era "1 planilha por ano"; a planilha vigente é o ciclo 2026). O `ano` NÃO é derivável de
uma data no model (ao contrário dos irmãos) — no import ele vem DECLARADO do workbook. Aqui, todo o dado já
existente foi carregado do ciclo 2026, então o backfill usa a constante **2026** (contrato travado com o
pipeline sheets.banco, 2026-08-24).

⚠️ `backend-migrate-integrity` roda em DB VAZIO → o backfill vira no-op no CI; validar em clone prod-like
antes do apply real. A NK antiga garante ≤1 linha por par → somar 2026 não colide.
"""

from django.db import migrations, models


def backfill_ano(apps, schema_editor):
    PlanoFormacoes = apps.get_model("core", "PlanoFormacoes")
    updates = []
    for p in PlanoFormacoes.objects.filter(ano__isnull=True).only("id", "ano"):
        p.ano = 2026  # todo dado atual = ciclo 2026 (planilha vigente); ano não é derivável do model
        updates.append(p)
    if updates:
        PlanoFormacoes.objects.bulk_update(updates, ["ano"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0094_equipe_gerencia_vigencia"),
    ]

    operations = [
        migrations.AddField(
            model_name="planoformacoes",
            name="ano",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text="Ano do ciclo anual do plano (declarado no import).",
                verbose_name="Ano",
            ),
        ),
        migrations.RunPython(backfill_ano, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="planoformacoes",
            name="unique_plano_municipio_projeto",
        ),
        migrations.AddConstraint(
            model_name="planoformacoes",
            constraint=models.UniqueConstraint(
                fields=("municipio", "projeto", "ano"),
                name="unique_plano_municipio_projeto_ano",
                nulls_distinct=False,
            ),
        ),
    ]
