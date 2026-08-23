"""Adiciona `ano` (cohort anual) ao DATCadastro + backfill pela 1ª etapa com data, e troca a NK
para (municipio, projeto_geral, plataforma, ano).

Domínio temporal: um cadastro de plataforma por ano de uso do mesmo (municipio, projeto_geral,
plataforma). O `ano` é DERIVADO da 1ª etapa com data (início do ciclo FORMAR/AVALIAR); cadastro sem
nenhuma data fica com ano=NULL (bucket pendente/NÃO_CLASSIFICADO). A NK antiga garantia ≤1 cadastro
por (municipio, projeto_geral, plataforma), então o backfill não colide na nova NK.
`nulls_distinct=False` garante um só pendente (ano=NULL) por combinação.
"""

from django.db import migrations, models

# Ordem das etapas por workflow (FORMAR e AVALIAR); a 1ª com data define o ano-cohort.
_DATE_FIELDS = (
    "data_criacao_curso",
    "data_chaves",
    "data_instrucoes",
    "data_envio",
    "data_recebidos",
    "data_validados",
    "data_importados",
)


def backfill_ano(apps, schema_editor):
    DATCadastro = apps.get_model("core", "DATCadastro")
    updates = []
    for c in DATCadastro.objects.all().only("id", *_DATE_FIELDS):
        d = next((getattr(c, f) for f in _DATE_FIELDS if getattr(c, f) is not None), None)
        if d is not None:
            c.ano = d.year
            updates.append(c)
    if updates:
        DATCadastro.objects.bulk_update(updates, ["ano"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0092_dat_acao_ano_nk"),
    ]

    operations = [
        migrations.AddField(
            model_name="datcadastro",
            name="ano",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text="Ano-cohort do cadastro (derivado da 1ª etapa com data no import). NULL = não classificado.",
                verbose_name="Ano",
            ),
        ),
        migrations.RunPython(backfill_ano, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="datcadastro",
            name="unique_dat_cadastro_mun_proj_plat",
        ),
        migrations.AddConstraint(
            model_name="datcadastro",
            constraint=models.UniqueConstraint(
                fields=("municipio", "projeto_geral", "plataforma", "ano"),
                name="unique_dat_cadastro_mun_proj_plat_ano",
                nulls_distinct=False,
            ),
        ),
    ]
