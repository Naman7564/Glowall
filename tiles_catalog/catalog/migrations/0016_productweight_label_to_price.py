from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0015_product_weight_options'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productweight',
            name='label',
        ),
        migrations.AddField(
            model_name='productweight',
            name='price',
            field=models.DecimalField(
                blank=True,
                null=True,
                decimal_places=2,
                help_text='Price for this weight option (optional)',
                max_digits=10,
            ),
        ),
    ]
