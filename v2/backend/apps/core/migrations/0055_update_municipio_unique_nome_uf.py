from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0054_add_municipio_referencia"),
    ]

    operations = [
        migrations.AlterField(
            model_name="municipio",
            name="nome",
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AddConstraint(
            model_name="municipio",
            constraint=models.UniqueConstraint(fields=("nome", "uf"), name="unique_municipio_nome_uf"),
        ),
    ]
