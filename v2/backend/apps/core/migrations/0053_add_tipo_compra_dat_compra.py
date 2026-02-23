from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0052_add_colecao_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="datcompra",
            name="tipo_compra",
            field=models.CharField(
                blank=True,
                null=True,
                choices=[
                    ("primeira", "Primeira compra"),
                    ("adicional_1", "Compra adicional 1"),
                    ("adicional_2", "Compra adicional 2"),
                    ("adicional_3", "Compra adicional 3"),
                ],
                help_text="Primeira compra ou compras adicionais",
                max_length=20,
                verbose_name="Tipo de Compra",
            ),
        ),
    ]
