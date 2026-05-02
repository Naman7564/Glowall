from django.db import migrations


def drop_productimage_alt_text(apps, schema_editor):
    """Remove the legacy ProductImage.alt_text column when it still exists."""
    connection = schema_editor.connection
    table_name = 'catalog_productimage'

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    if 'alt_text' not in columns:
        return

    quote_name = connection.ops.quote_name
    schema_editor.execute(
        f"ALTER TABLE {quote_name(table_name)} DROP COLUMN {quote_name('alt_text')}"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0017_remove_product_finish_and_finish_model'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='product',
            options={'ordering': ['gmt_code', 'name']},
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_productimage_alt_text, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='productimage',
                    name='alt_text',
                ),
            ],
        ),
    ]
