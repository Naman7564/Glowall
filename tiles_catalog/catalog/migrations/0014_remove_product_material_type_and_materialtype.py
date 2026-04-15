from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0013_remove_product_sku'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='material_type',
        ),
        migrations.DeleteModel(
            name='MaterialType',
        ),
    ]
