from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0021_marble_texture_weight_pricing'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='default_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
