from django.db import migrations, models


def copy_color_names_to_text_field(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')

    for product in Product.objects.select_related('color').all().iterator():
        product.color_text = product.color.name if product.color else ''
        product.save(update_fields=['color_text'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_remove_category_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='color_text',
            field=models.CharField(blank=True, default='', help_text='Enter a color name manually', max_length=100),
            preserve_default=False,
        ),
        migrations.RunPython(copy_color_names_to_text_field, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='product',
            name='color',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='color_text',
            new_name='color',
        ),
        migrations.DeleteModel(
            name='Color',
        ),
    ]
