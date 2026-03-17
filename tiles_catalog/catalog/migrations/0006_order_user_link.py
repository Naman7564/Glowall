from django.conf import settings
from django.db import migrations, models


def link_existing_orders_to_users(apps, schema_editor):
    Order = apps.get_model('catalog', 'Order')
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)

    email_to_user_id = {}
    for user in User.objects.exclude(email='').iterator():
        normalized_email = (user.email or '').strip().lower()
        if normalized_email and normalized_email not in email_to_user_id:
            email_to_user_id[normalized_email] = user.pk

    for order in Order.objects.filter(user__isnull=True).exclude(email='').iterator():
        normalized_email = (order.email or '').strip().lower()
        user_id = email_to_user_id.get(normalized_email)
        if user_id:
            Order.objects.filter(pk=order.pk, user__isnull=True).update(user_id=user_id)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalog', '0005_order_payment_flow'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='orders',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(link_existing_orders_to_users, migrations.RunPython.noop),
    ]
