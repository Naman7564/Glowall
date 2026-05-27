from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Discount, Order, OrderItem, Product, ProductWeight


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


class StorefrontPriceConsistencyTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Marble Texture',
            slug='marbels',
            default_price=Decimal('2299.00'),
        )
        self.product = Product.objects.create(
            name='Classic Marble Texture',
            gmt_code='310',
            category=self.category,
            description='Marble texture product',
            price=Decimal('2299.00'),
            is_available=True,
            is_featured=True,
        )
        self.weight = ProductWeight.objects.create(
            product=self.product,
            value_kg=Decimal('30.00'),
            price=Decimal('2399.00'),
            order=0,
        )

    def test_marble_weight_sync_does_not_override_configured_base_price(self):
        self.product.sync_marble_texture_weight_pricing()
        self.product.refresh_from_db()
        self.weight.refresh_from_db()

        self.assertEqual(self.product.price, Decimal('2299.00'))
        self.assertIsNone(self.weight.price)

    def test_product_detail_uses_configured_base_price_before_weight_selection(self):
        response = self.client.get(self.product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="pd-price">₹2,299.00</span>', html=True)
        self.assertNotContains(response, 'pd-weight-btn active')

    @patch('catalog.views.create_cashfree_order')
    def test_checkout_and_order_use_base_price_without_explicit_weight_selection(self, mock_create_cashfree_order):
        mock_create_cashfree_order.return_value = {
            'cashfree_order_id': 'ORD-TEST-0001',
            'cashfree_cf_order_id': 'CF-TEST-0001',
            'payment_session_id': 'session-123',
            'payment_link': 'https://example.com/pay',
        }

        session = self.client.session
        session['shopping_cart'] = {
            f'{self.product.pk}_{self.weight.pk}': {
                'product_id': str(self.product.pk),
                'weight_id': str(self.weight.pk),
                'quantity': 2,
            }
        }
        session.save()

        cart_response = self.client.get(reverse('catalog:cart'))
        self.assertEqual(cart_response.status_code, 200)
        self.assertEqual(cart_response.context['cart_items'][0]['unit_price'], Decimal('2299.00'))
        self.assertEqual(cart_response.context['cart_total'], Decimal('4598.00'))

        checkout_redirect = self.client.get(reverse('catalog:cart_checkout'))
        self.assertEqual(checkout_redirect.status_code, 302)

        checkout_response = self.client.get(reverse('catalog:checkout'))
        self.assertEqual(checkout_response.status_code, 200)
        self.assertEqual(checkout_response.context['total_order_price'], Decimal('4598.00'))
        self.assertEqual(checkout_response.context['checkout_items'][0]['unit_price'], Decimal('2299.00'))

        place_order_response = self.client.post(
            reverse('catalog:place_order'),
            {
                'full_name': 'Buyer Name',
                'phone_number': '9999999999',
                'email': 'buyer@example.com',
                'address': '1 Test Street',
                'city': 'Test City',
                'state': 'Test State',
                'pincode': '123456',
            },
        )

        self.assertEqual(place_order_response.status_code, 302)

        order = Order.objects.latest('id')
        order_item = order.items.get()
        self.assertEqual(order_item.unit_price, Decimal('2299.00'))
        self.assertEqual(order_item.total_price, Decimal('4598.00'))
        self.assertEqual(order.total_price, Decimal('4598.00'))


class DiscountCheckoutTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Premium Marble')
        self.product = Product.objects.create(
            name='White Pearl',
            gmt_code='410',
            category=self.category,
            description='Discountable product',
            price=Decimal('1000.00'),
            is_available=True,
        )
        self.discount = Discount.objects.create(
            name='Glow launch',
            code='glow10',
            discount_type=Discount.TYPE_PERCENTAGE,
            value=Decimal('10.00'),
            applies_to=Discount.APPLY_CATEGORIES,
            minimum_order_amount=Decimal('1500.00'),
            usage_limit=2,
        )
        self.discount.categories.add(self.category)

        session = self.client.session
        session['checkout_item'] = [{
            'product_id': str(self.product.pk),
            'quantity': 2,
            'weight_id': '',
            'weight_selected': False,
        }]
        session.save()

    def test_checkout_applies_valid_coupon_to_summary(self):
        response = self.client.post(reverse('catalog:apply_coupon'), {'coupon_code': 'GLOW10'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['checkout_coupon_code'], 'GLOW10')

        checkout_response = self.client.get(reverse('catalog:checkout'))
        totals = checkout_response.context['checkout_totals']
        self.assertEqual(totals['original_price'], Decimal('2000.00'))
        self.assertEqual(totals['discount_amount'], Decimal('200.00'))
        self.assertEqual(totals['final_total'], Decimal('1800.00'))

    @patch('catalog.views.create_cashfree_order')
    def test_place_order_persists_discounted_total_and_usage(self, mock_create_cashfree_order):
        mock_create_cashfree_order.return_value = {
            'cashfree_order_id': 'ORD-DISCOUNT-0001',
            'cashfree_cf_order_id': 'CF-DISCOUNT-0001',
            'payment_session_id': 'session-456',
            'payment_link': 'https://example.com/pay',
        }

        response = self.client.post(
            reverse('catalog:place_order'),
            {
                'full_name': 'Coupon Buyer',
                'phone_number': '9999999999',
                'email': 'coupon@example.com',
                'address': '10 Coupon Street',
                'city': 'Test City',
                'state': 'Test State',
                'pincode': '123456',
                'coupon_code': 'GLOW10',
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Order.objects.latest('id')
        self.assertEqual(order.original_price, Decimal('2000.00'))
        self.assertEqual(order.discount_amount, Decimal('200.00'))
        self.assertEqual(order.total_price, Decimal('1800.00'))
        self.assertEqual(order.coupon_code, 'GLOW10')

        self.discount.refresh_from_db()
        self.assertEqual(self.discount.usage_count, 1)

    def test_invalid_coupon_does_not_store_checkout_coupon(self):
        response = self.client.post(reverse('catalog:apply_coupon'), {'coupon_code': 'NOPE'})

        self.assertEqual(response.status_code, 302)
        self.assertNotIn('checkout_coupon_code', self.client.session)
