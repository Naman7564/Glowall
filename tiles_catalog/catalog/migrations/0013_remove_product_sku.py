from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0012_product_gmt_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='sku',
        ),
    ]
