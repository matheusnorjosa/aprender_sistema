"""Adiciona `ano` (cohort anual) ao DATAcao + backfill pela data da reunião, e troca a NK
para (municipio, projeto, ano).

Decisão B (domínio temporal): DATAcao é cohortada por ano — um ciclo de ação por ano de uso do
mesmo par (municipio, projeto). O `ano` é DERIVADO da data da reunião (âncora do ciclo DAT), com
fallback data_reuniao → data_entrega → data_carta → data_contato; ação sem nenhuma data fica com
ano=NULL (bucket pendente/NÃO_CLASSIFICADO). Como a NK antiga garantia ≤1 DATAcao por (municipio,
projeto), o backfill não pode colidir na nova NK (municipio, projeto, ano). `nulls_distinct=False`
garante um só pendente (ano=NULL) por par.
"""

from django.db import migrations, models


def backfill_ano(apps, schema_editor):
    DATAcao = apps.get_model("core", "DATAcao")
    updates = []
    for a in DATAcao.objects.all().only("id", "data_reuniao", "data_entrega", "data_carta", "data_contato"):
        d = a.data_reuniao or a.data_entrega or a.data_carta or a.data_contato
        if d is not None:
            a.ano = d.year
            updates.append(a)
    if updates:
        DATAcao.objects.bulk_update(updates, ["ano"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0091_dat_registro_nk_ano"),
    ]

    operations = [
        migrations.AddField(
            model_name="datacao",
            name="ano",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text="Ano-cohort da ação (derivado da data da reunião no import). NULL = não classificado.",
                verbose_name="Ano",
            ),
        ),
        migrations.RunPython(backfill_ano, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="datacao",
            name="unique_dat_acao_municipio_projeto",
        ),
        migrations.AddConstraint(
            model_name="datacao",
            constraint=models.UniqueConstraint(
                fields=("municipio", "projeto", "ano"),
                name="unique_dat_acao_municipio_projeto_ano",
                nulls_distinct=False,
            ),
        ),
    ]
