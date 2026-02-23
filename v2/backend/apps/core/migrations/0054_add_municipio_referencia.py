from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0053_add_tipo_compra_dat_compra"),
    ]

    operations = [
        migrations.CreateModel(
            name="MunicipioReferencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "codigo_externo",
                    models.CharField(
                        db_index=True,
                        help_text="ID do município na fonte externa (não confundir com IBGE)",
                        max_length=20,
                    ),
                ),
                ("nome", models.CharField(max_length=100)),
                ("uf", models.CharField(max_length=2)),
                ("fonte", models.CharField(db_index=True, default="sistemasaprender", max_length=50)),
                ("ativo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Municipio Referencia",
                "verbose_name_plural": "Municipios Referencia",
                "db_table": "core_municipio_referencia",
                "ordering": ["uf", "nome"],
            },
        ),
        migrations.AddConstraint(
            model_name="municipioreferencia",
            constraint=models.UniqueConstraint(
                fields=("fonte", "codigo_externo"), name="unique_municipio_ref_codigo_fonte"
            ),
        ),
        migrations.AddConstraint(
            model_name="municipioreferencia",
            constraint=models.UniqueConstraint(
                fields=("fonte", "nome", "uf"), name="unique_municipio_ref_nome_uf_fonte"
            ),
        ),
        migrations.AddIndex(
            model_name="municipioreferencia",
            index=models.Index(fields=["nome", "uf"], name="core_municipi_nome_90d16f_idx"),
        ),
    ]
