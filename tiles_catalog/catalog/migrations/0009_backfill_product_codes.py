from django.db import migrations


def backfill_product_codes(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    existing_codes = set(
        Product.objects.exclude(code__isnull=True).values_list('code', flat=True)
    )
    next_code = max(existing_codes, default=100) + 1
    if next_code < 101:
        next_code = 101

    for product in Product.objects.filter(code__isnull=True).order_by('created_at', 'pk'):
        while next_code in existing_codes:
            next_code += 1
        product.code = next_code
        product.save(update_fields=['code'])
        existing_codes.add(next_code)
        next_code += 1


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_add_poster_model'),
    ]

    operations = [
        migrations.RunPython(backfill_product_codes, noop),
    ]
