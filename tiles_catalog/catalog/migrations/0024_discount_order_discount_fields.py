from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


def backfill_order_original_price(apps, schema_editor):
    Order = apps.get_model('catalog', 'Order')
    Order.objects.filter(original_price=Decimal('0.00')).update(original_price=models.F('total_price'))


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0023_clear_default_marble_texture_30kg_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('code', models.CharField(db_index=True, max_length=40, unique=True)),
                ('discount_type', models.CharField(choices=[('fixed', 'Fixed amount'), ('percentage', 'Percentage')], max_length=20)),
                ('value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('usage_limit', models.PositiveIntegerField(blank=True, null=True)),
                ('usage_count', models.PositiveIntegerField(default=0)),
                ('minimum_order_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('applies_to', models.CharField(choices=[('order', 'Entire order'), ('products', 'Specific products'), ('categories', 'Specific categories')], default='order', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('categories', models.ManyToManyField(blank=True, related_name='discounts', to='catalog.category')),
                ('products', models.ManyToManyField(blank=True, related_name='discounts', to='catalog.product')),
            ],
            options={
                'ordering': ['-created_at', 'code'],
            },
        ),
        migrations.AddField(
            model_name='order',
            name='original_price',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='order',
            name='discount',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='catalog.discount'),
        ),
        migrations.AddField(
            model_name='order',
            name='coupon_code',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.RunPython(backfill_order_original_price, migrations.RunPython.noop),
    ]
