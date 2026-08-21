"""Adiciona `ano` (ano de uso da coleção) ao DATRegistro + backfill pelo ano dominante das compras.

Primeiro passo da dimensão temporal por ano (cohort anual): `nr_codigos` passa a contar só as
compras cujo `ano_uso` bate com `registro.ano`, em vez de somar 2026 + 2027 + sem-ano no mesmo balde.
Campo NULLABLE nesta fase (transição segura); o backfill preenche pelo ano_uso DOMINANTE das compras
do par (municipio, projeto). Registros sem compras ficam com ano=NULL (mantêm o cálculo somando tudo).

A chave natural passa a incluir `ano` (split de registros per-year) num PR seguinte — junto do import
per-year e da reconciliação contra o Nº de Códigos por ano. Após esta migration, rodar
`recalcular_nr_codigos_dat` recomputa `nr_codigos` já por ano (o cálculo filtra por `ano` quando setado).
"""

from django.db import migrations, models
from django.db.models import Count


def backfill_ano(apps, schema_editor):
    DATRegistro = apps.get_model("core", "DATRegistro")
    DATCompra = apps.get_model("core", "DATCompra")
    updates = []
    for reg in DATRegistro.objects.all().only("id", "municipio_id", "projeto_id"):
        dom = (
            DATCompra.objects.filter(municipio_id=reg.municipio_id, projeto_id=reg.projeto_id, ativo=True)
            .values("ano_uso")
            .annotate(n=Count("id"))
            .order_by("-n", "-ano_uso")
            .first()
        )
        if dom and dom["ano_uso"] is not None:
            reg.ano = dom["ano_uso"]
            updates.append(reg)
    if updates:
        DATRegistro.objects.bulk_update(updates, ["ano"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0088_fix_projeto_geral_por_aluno"),
    ]

    operations = [
        migrations.AddField(
            model_name="datregistro",
            name="ano",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text="Ano de uso da coleção — nr_codigos conta apenas as compras deste ano.",
                verbose_name="Ano de uso",
            ),
        ),
        migrations.RunPython(backfill_ano, migrations.RunPython.noop),
    ]
