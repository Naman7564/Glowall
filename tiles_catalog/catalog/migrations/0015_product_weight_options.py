from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0014_remove_product_material_type_and_materialtype'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductWeight',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value_kg', models.DecimalField(decimal_places=2, help_text='Weight in kilograms', max_digits=8)),
                ('label', models.CharField(blank=True, help_text='Optional label, e.g. "Per Box" or "Per Piece"', max_length=100)),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order (lower first)')),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='weights',
                    to='catalog.product',
                )),
            ],
            options={
                'ordering': ['order', 'value_kg'],
            },
        ),
    ]
