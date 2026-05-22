from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Order, OrderItem, Product, ProductWeight


class OrderViewsRegressionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='password',
            is_staff=True,
        )
        self.customer = user_model.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='password',
        )

        self.category = Category.objects.create(name='Marble')
        self.product = Product.objects.create(
            name='Silver Mist',
            gmt_code='111',
            category=self.category,
            description='Primary product',
            price=Decimal('1200.00'),
        )
        self.second_product = Product.objects.create(
            name='Granite Black',
            gmt_code='112',
            category=self.category,
            description='Secondary product',
            price=Decimal('800.00'),
        )
        self.weight = ProductWeight.objects.create(
            product=self.product,
            value_kg=Decimal('25.00'),
            price=Decimal('1200.00'),
            order=0,
        )

        self.order = Order.objects.create(
            user=self.customer,
            full_name='Test Customer',
            phone_number='9999999999',
            email='customer@example.com',
            address='1 Test Street',
            city='Test City',
            state='Test State',
            pincode='123456',
            total_price=Decimal('3200.00'),
            payment_status=Order.PAYMENT_PENDING,
            cashfree_order_id='ORD-000001',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            weight=self.weight,
            quantity=2,
            unit_price=Decimal('1200.00'),
            total_price=Decimal('2400.00'),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.second_product,
            quantity=1,
            unit_price=Decimal('800.00'),
            total_price=Decimal('800.00'),
        )

    def test_admin_order_list_handles_order_items_schema(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin_panel:order_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Silver Mist +1 more')
        self.assertEqual(response.context['orders'][0].quantity, 3)

    def test_admin_order_list_searches_by_order_item_product_name(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin_panel:order_list'), {'q': 'Granite'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')

    def test_admin_order_detail_renders_order_items(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin_panel:order_detail', args=[self.order.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Silver Mist')
        self.assertContains(response, 'Granite Black')
        self.assertContains(response, '25 kg')

    def test_customer_orders_page_uses_order_items(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse('catalog:orders'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Silver Mist')
        self.assertEqual(response.context['orders'][0].quantity, 3)


class CategoryDefaultPriceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username='category-staff',
            email='category-staff@example.com',
            password='password',
            is_staff=True,
        )

        self.category = Category.objects.create(
            name='Porcelain',
            default_price=Decimal('950.00'),
        )
        self.available_product = Product.objects.create(
            name='Porcelain Prime',
            gmt_code='210',
            category=self.category,
            description='Available product',
            price=Decimal('700.00'),
            is_available=True,
        )
        self.unavailable_product = Product.objects.create(
            name='Porcelain Hidden',
            gmt_code='211',
            category=self.category,
            description='Unavailable product',
            price=Decimal('650.00'),
            is_available=False,
        )

    def test_editing_category_default_price_updates_available_products(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin_panel:category_edit', args=[self.category.pk]),
            {
                'name': self.category.name,
                'slug': self.category.slug,
                'description': self.category.description,
                'default_price': '1250.00',
                'is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)

        self.available_product.refresh_from_db()
        self.unavailable_product.refresh_from_db()
        self.category.refresh_from_db()

        self.assertEqual(self.category.default_price, Decimal('1250.00'))
        self.assertEqual(self.available_product.price, Decimal('1250.00'))
        self.assertEqual(self.unavailable_product.price, Decimal('650.00'))

    def test_blank_product_price_inherits_category_default(self):
        product = Product.objects.create(
            name='Porcelain Defaulted',
            gmt_code='212',
            category=self.category,
            description='No explicit price provided',
            price=None,
        )

        self.assertEqual(product.price, Decimal('950.00'))
