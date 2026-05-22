from decimal import Decimal

from django.db import migrations
from django.db.models import Q


def clear_default_marble_texture_30kg_price(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    ProductWeight = apps.get_model('catalog', 'ProductWeight')

    marble_categories = Category.objects.filter(
        Q(slug__in=['marbels', 'marble-texture']) | Q(name__iexact='Marble Texture')
    )
    if not marble_categories.exists():
        return

    ProductWeight.objects.filter(
        product__category__in=marble_categories,
        value_kg=Decimal('30'),
        price=Decimal('2399'),
    ).update(price=None)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0022_category_default_price'),
    ]

    operations = [
        migrations.RunPython(clear_default_marble_texture_30kg_price, migrations.RunPython.noop),
    ]
