from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0016_productweight_label_to_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='finish',
        ),
        migrations.DeleteModel(
            name='Finish',
        ),
    ]
