# Generated manually for checkout and Cashfree payment flow.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_customerreview'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='subject',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=120)),
                ('phone_number', models.CharField(max_length=20)),
                ('email', models.EmailField(max_length=254)),
                ('address', models.TextField()),
                ('city', models.CharField(max_length=80)),
                ('state', models.CharField(max_length=80)),
                ('pincode', models.CharField(max_length=10)),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('new', 'New'), ('processing', 'Processing'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='new', max_length=20)),
                ('payment_status', models.CharField(choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')], db_index=True, default='PENDING', max_length=20)),
                ('cashfree_order_id', models.CharField(blank=True, max_length=45, unique=True)),
                ('cashfree_cf_order_id', models.CharField(blank=True, max_length=120)),
                ('cashfree_payment_session_id', models.CharField(blank=True, max_length=255)),
                ('cashfree_payment_id', models.CharField(blank=True, max_length=120)),
                ('payment_message', models.TextField(blank=True)),
                ('payment_completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='catalog.product')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
