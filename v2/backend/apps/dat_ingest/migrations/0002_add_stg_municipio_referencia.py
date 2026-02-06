from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dat_ingest", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StgMunicipioReferencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_externo", models.CharField(blank=True, default="", max_length=20)),
                ("nome", models.CharField(max_length=100)),
                ("uf", models.CharField(max_length=2)),
                ("fonte", models.CharField(default="sistemasaprender", max_length=50)),
                ("src", models.CharField(max_length=100)),
                ("rownum", models.IntegerField()),
            ],
            options={
                "verbose_name": "Staging Municipio Referencia",
                "verbose_name_plural": "Staging Municipios Referencia",
                "db_table": "stg_municipio_ref",
            },
        ),
        migrations.AddIndex(
            model_name="stgmunicipioreferencia",
            index=models.Index(fields=["fonte", "codigo_externo"], name="stg_municipio_ref_fonte_codigo_idx"),
        ),
        migrations.AddIndex(
            model_name="stgmunicipioreferencia",
            index=models.Index(fields=["nome", "uf"], name="stg_municipio_ref_nome_uf_idx"),
        ),
    ]
