from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0007_add_updated_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="share",
            name="last_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=9,
                max_digits=20,
                null=True,
                verbose_name="Текущая цена",
            ),
        ),
    ]
