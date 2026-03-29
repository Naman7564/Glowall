from django.db import migrations, models


def backfill_product_gmt_codes(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    Product.objects.filter(gmt_code='', slug__gt='').update(gmt_code=models.F('slug'))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0011_product_weight_specification'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='gmt_code',
            field=models.CharField(blank=True, db_index=True, help_text='GMT code used to group and filter products', max_length=100),
        ),
        migrations.RunPython(backfill_product_gmt_codes, noop),
    ]
