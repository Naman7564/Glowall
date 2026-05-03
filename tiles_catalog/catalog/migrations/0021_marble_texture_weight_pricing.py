from decimal import Decimal

from django.db import migrations
from django.db.models import Q


MARBLE_TEXTURE_WEIGHT_OPTIONS = (
    (Decimal('30'), Decimal('2399')),
    (Decimal('25'), Decimal('1899')),
)


def sync_marble_texture_weight_pricing(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    Product = apps.get_model('catalog', 'Product')
    ProductWeight = apps.get_model('catalog', 'ProductWeight')

    marble_categories = Category.objects.filter(
        Q(slug__in=['marbels', 'marble-texture']) | Q(name__iexact='Marble Texture')
    )
    if not marble_categories.exists():
        return

    for product in Product.objects.filter(category__in=marble_categories):
        if product.price != MARBLE_TEXTURE_WEIGHT_OPTIONS[0][1]:
            product.price = MARBLE_TEXTURE_WEIGHT_OPTIONS[0][1]
            product.save(update_fields=['price'])

        existing_weights = {
            Decimal(str(weight.value_kg)): weight
            for weight in ProductWeight.objects.filter(product=product)
        }

        for order, (value_kg, price) in enumerate(MARBLE_TEXTURE_WEIGHT_OPTIONS):
            weight = existing_weights.get(value_kg)
            if weight is None:
                ProductWeight.objects.create(
                    product=product,
                    value_kg=value_kg,
                    price=price,
                    order=order,
                )
                continue

            update_fields = []
            if weight.price != price:
                weight.price = price
                update_fields.append('price')
            if weight.order != order:
                weight.order = order
                update_fields.append('order')
            if update_fields:
                weight.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0020_merge_0018_branches'),
    ]

    operations = [
        migrations.RunPython(sync_marble_texture_weight_pricing, migrations.RunPython.noop),
    ]
