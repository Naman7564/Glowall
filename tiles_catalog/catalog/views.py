import logging
import re
import traceback
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, IntegerField, F
from django.db.models.functions import Cast, Trim
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Category, Product, CustomerReview, Order, Poster, Discount
from .forms import OrderForm
from .payments import (
    CashfreeGatewayError,
    CashfreeWebhookError,
    create_cashfree_order,
    fetch_cashfree_order,
    map_payment_status,
    parse_cashfree_timestamp,
    parse_webhook_payload,
    verify_webhook_signature,
)


logger = logging.getLogger(__name__)


CHECKOUT_SESSION_KEY = 'checkout_item'
CART_SESSION_KEY = 'shopping_cart'
CHECKOUT_COUPON_SESSION_KEY = 'checkout_coupon_code'


def _parse_gmt_code_filter(value):
    """Parse a single GMT code or numeric range into inclusive bounds."""
    match = re.fullmatch(r"\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*", value or "")
    if not match:
        return None

    lower_bound = int(match.group(1))
    upper_bound = int(match.group(2) or match.group(1))
    if lower_bound > upper_bound:
        lower_bound, upper_bound = upper_bound, lower_bound
    return lower_bound, upper_bound


def _filter_products_by_gmt_code(queryset, value):
    """Filter products by GMT code, supporting exact values and ranges."""
    bounds = _parse_gmt_code_filter(value)
    if not bounds:
        return queryset

    lower_bound, upper_bound = bounds
    queryset = queryset.filter(gmt_code__regex=r"^\s*\d+\s*$").annotate(
        gmt_code_number=Cast(Trim("gmt_code"), IntegerField())
    )
    if lower_bound == upper_bound:
        return queryset.filter(gmt_code_number=lower_bound)
    return queryset.filter(gmt_code_number__gte=lower_bound, gmt_code_number__lte=upper_bound)


def _normalize_quantity(value, default=1):
    """Return a safe positive quantity for checkout."""
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, quantity)


def _normalize_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _print_checkout_exception(label, exc):
    print(f'{label}: {exc.__class__.__name__}: {exc}')
    traceback.print_exc()


def _resolve_item_pricing(product, weight_id=None, weight_selected=False):
    weight_obj = None
    use_weight_price = _normalize_bool(weight_selected)

    if use_weight_price and weight_id:
        from .models import ProductWeight

        weight_obj = (
            ProductWeight.objects.select_related('product__category')
            .filter(id=weight_id, product=product)
            .first()
        )

    unit_price = product.resolve_unit_price(weight=weight_obj, use_weight_price=use_weight_price)
    return weight_obj, unit_price


def _load_checkout_items(request):
    product_id = request.GET.get('product') or request.POST.get('product_id')
    quantity_value = request.GET.get('quantity') or request.POST.get('quantity')
    weight_id = request.GET.get('weight_id') or request.POST.get('weight_id')
    weight_selected = request.GET.get('weight_selected') or request.POST.get('weight_selected')
    
    checkout_data = request.session.get(CHECKOUT_SESSION_KEY, [])
    if isinstance(checkout_data, dict):
        checkout_data = [checkout_data]

    if product_id:
        checkout_data = [{
            'product_id': product_id,
            'quantity': _normalize_quantity(quantity_value, default=1),
            'weight_id': weight_id,
            'weight_selected': _normalize_bool(weight_selected),
        }]
        request.session[CHECKOUT_SESSION_KEY] = checkout_data
    elif checkout_data:
        for item in checkout_data:
            item['quantity'] = _normalize_quantity(item.get('quantity'), default=1)
            item['weight_selected'] = _normalize_bool(item.get('weight_selected'))
        request.session[CHECKOUT_SESSION_KEY] = checkout_data
    else:
        return None

    resolved_items = []
    total_order_price = 0
    all_pricing_available = True

    for item_data in checkout_data:
        product = Product.objects.filter(
            pk=item_data.get('product_id'),
            is_available=True,
        ).select_related('category').first()

        if not product:
            continue

        weight_obj, unit_price = _resolve_item_pricing(
            product,
            weight_id=item_data.get('weight_id'),
            weight_selected=item_data.get('weight_selected'),
        )

        if unit_price is None:
            all_pricing_available = False
            unit_price = 0
            
        quantity = item_data['quantity']
        total_price = unit_price * quantity
        total_order_price += total_price

        resolved_items.append({
            'product': product,
            'weight': weight_obj,
            'weight_selected': _normalize_bool(item_data.get('weight_selected')),
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_price,
        })

    if not resolved_items:
        request.session.pop(CHECKOUT_SESSION_KEY, None)
        return None

    return {
        'items': resolved_items,
        'total_order_price': total_order_price,
        'pricing_available': all_pricing_available,
    }


def _normalize_coupon_code(value):
    return (value or '').strip().upper()


def _calculate_checkout_totals(checkout_data, coupon_code=''):
    subtotal = Decimal(checkout_data['total_order_price'] or 0)
    coupon_code = _normalize_coupon_code(coupon_code)
    discount = None
    discount_amount = Decimal('0.00')
    coupon_error = ''

    if coupon_code:
        discount = (
            Discount.objects
            .prefetch_related('products', 'categories')
            .filter(code=coupon_code)
            .first()
        )
        if discount:
            is_valid, coupon_error = discount.validate_for_items(checkout_data['items'], subtotal)
            if is_valid:
                discount_amount = discount.calculate_discount(checkout_data['items'], subtotal)
            else:
                discount = None
        else:
            coupon_error = 'Invalid coupon code.'

    final_total = max(subtotal - discount_amount, Decimal('0.00'))
    return {
        'original_price': subtotal,
        'discount': discount,
        'coupon_code': coupon_code if discount else '',
        'coupon_error': coupon_error,
        'discount_amount': discount_amount,
        'final_total': final_total,
    }


def _get_checkout_form_initial(request):
    initial = {}
    if request.user.is_authenticated:
        full_name = ' '.join(part for part in [request.user.first_name, request.user.last_name] if part).strip()
        if full_name:
            initial['full_name'] = full_name
        if request.user.email:
            initial['email'] = request.user.email
        recent_order = (
            Order.objects.filter(user=request.user)
            .only('phone_number', 'address', 'city', 'state', 'pincode')
            .order_by('-created_at')
            .first()
        )
        if recent_order:
            initial.setdefault('phone_number', recent_order.phone_number)
            initial.setdefault('address', recent_order.address)
            initial.setdefault('city', recent_order.city)
            initial.setdefault('state', recent_order.state)
            initial.setdefault('pincode', recent_order.pincode)
    return initial


def _get_profile_snapshot(user):
    latest_order = (
        Order.objects.filter(user=user)
        .only(
            'full_name',
            'email',
            'phone_number',
            'address',
            'city',
            'state',
            'pincode',
            'created_at',
        )
        .order_by('-created_at')
        .first()
    )

    address_lines = []
    if latest_order:
        if latest_order.address:
            address_lines.append(latest_order.address)
        location_line = ', '.join(part for part in [latest_order.city, latest_order.state] if part)
        if latest_order.pincode:
            location_line = f'{location_line} - {latest_order.pincode}' if location_line else latest_order.pincode
        if location_line:
            address_lines.append(location_line)

    name = user.get_full_name() or (latest_order.full_name if latest_order else '') or user.username
    email = user.email or (latest_order.email if latest_order else '')
    phone = latest_order.phone_number if latest_order else ''

    return {
        'name': name,
        'email': email,
        'phone': phone,
        'address_lines': address_lines,
        'latest_order': latest_order,
    }


def _render_checkout(request, form, checkout_data, status=200, coupon_code=None, coupon_error=''):
    if coupon_code is None:
        coupon_code = request.session.get(CHECKOUT_COUPON_SESSION_KEY, '')
    totals = _calculate_checkout_totals(checkout_data, coupon_code)
    if coupon_error:
        totals['coupon_error'] = coupon_error
    context = {
        'form': form,
        'checkout_items': checkout_data['items'],
        'total_order_price': checkout_data['total_order_price'],
        'checkout_totals': totals,
        'applied_coupon': totals['discount'],
        'coupon_code': coupon_code or totals['coupon_code'],
        'page_title': 'Checkout',
    }
    return render(request, 'catalog/checkout.html', context, status=status)


def _update_order_payment_state(order, payment_status, payment_message='', cashfree_payment_id='', payment_time=None):
    update_fields = ['payment_status', 'payment_message', 'updated_at']

    if payment_status:
        order.payment_status = payment_status
    if payment_message is not None:
        order.payment_message = payment_message
    if cashfree_payment_id:
        order.cashfree_payment_id = cashfree_payment_id
        update_fields.append('cashfree_payment_id')
    if payment_time:
        order.payment_completed_at = payment_time
        update_fields.append('payment_completed_at')
    if payment_status == Order.PAYMENT_SUCCESS and order.status == Order.STATUS_NEW:
        order.status = Order.STATUS_PROCESSING
        update_fields.append('status')

    order.save(update_fields=list(dict.fromkeys(update_fields)))


def _sync_order_from_cashfree(order):
    gateway_order = fetch_cashfree_order(order)
    payments = sorted(
        gateway_order.get('payments') or [],
        key=lambda payment: payment.get('payment_completion_time') or payment.get('payment_time') or '',
    )
    latest_payment = payments[-1] if payments else {}
    payment_status = map_payment_status(
        gateway_order.get('order_status', ''),
        latest_payment.get('payment_status', ''),
    )
    payment_time = parse_cashfree_timestamp(
        latest_payment.get('payment_completion_time') or latest_payment.get('payment_time')
    )
    _update_order_payment_state(
        order,
        payment_status,
        payment_message=latest_payment.get('payment_message', ''),
        cashfree_payment_id=latest_payment.get('cf_payment_id', ''),
        payment_time=payment_time,
    )
    if gateway_order.get('payment_session_id') and order.cashfree_payment_session_id != gateway_order['payment_session_id']:
        order.cashfree_payment_session_id = gateway_order['payment_session_id']
        order.save(update_fields=['cashfree_payment_session_id', 'updated_at'])


def _build_cashfree_urls(request):
    scheme = 'https' if request.is_secure() or settings.CASHFREE_ENV == 'PRODUCTION' else 'http'
    payment_return_url = request.build_absolute_uri(reverse('catalog:payment_return'))
    notify_url = request.build_absolute_uri(reverse('catalog:payment_webhook'))
    if scheme == 'https':
        payment_return_url = payment_return_url.replace('http://', 'https://', 1)
        notify_url = notify_url.replace('http://', 'https://', 1)
    return {
        'payment_return_url': payment_return_url,
        'cashfree_return_url': f'{payment_return_url}?order_id={{order_id}}',
        'notify_url': notify_url,
    }


def home(request):
    """Homepage view."""
    featured_products = Product.objects.filter(
        is_available=True, 
        is_featured=True
    ).select_related('category').prefetch_related('weights')[:8]
    
    marble_textures = Product.objects.filter(
        is_available=True,
        category__slug='marbels'
    ).select_related('category').prefetch_related('weights')[:4]
    
    featured_categories = Category.objects.filter(
        is_active=True
    ).annotate(
        available_product_count=Count('products', filter=Q(products__is_available=True))
    )[:6]

    customer_reviews = CustomerReview.objects.filter(
        is_active=True
    )[:12]

    posters = Poster.objects.filter(is_active=True)[:5]

    context = {
        'featured_products': featured_products,
        'marble_textures': marble_textures,
        'featured_categories': featured_categories,
        'customer_reviews': customer_reviews,
        'posters': posters,
        'page_title': 'Premium Marble & Stone Showroom',
    }
    return render(request, 'catalog/home.html', context)


def product_list(request):
    """Product listing with filters and search."""
    products = Product.objects.filter(is_available=True).select_related('category').prefetch_related('weights')
    
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(gmt_code__icontains=search_query)
        ).distinct()
    
    # Filter by category
    category_slug = request.GET.get('category', '')
    if category_slug:
        products = products.filter(category__slug=category_slug)
        
    # Filter by color
    color_name = request.GET.get('color', '')
    if color_name:
        products = products.filter(color__icontains=color_name)
    
    # Filter by availability
    availability = request.GET.get('availability', '')
    if availability == 'available':
        products = products.filter(is_available=True)
    
    # GMT code filtering accepts exact values like 111 and ranges like 111-120.
    gmt_code_filter = request.GET.get('gmt_code', '').strip()
    if gmt_code_filter:
        products = _filter_products_by_gmt_code(products, gmt_code_filter)

    products = products.order_by('gmt_code', 'name')
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Get all filter options for sidebar
    all_categories = Category.objects.filter(is_active=True).order_by('name')
    context = {
        'products': products,
        'search_query': search_query,
        'current_category': category_slug,
        'current_gmt_code': gmt_code_filter,
        'all_categories': all_categories,
        'page_title': 'Product Catalog',
    }
    return render(request, 'catalog/product_list.html', context)


def category_detail(request, slug):
    """Category detail view showing products in a category."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Get products in this category
    products = Product.objects.filter(
        category=category,
        is_available=True
    ).select_related('category').prefetch_related('weights')
    
    # GMT code filtering accepts exact values like 111 and ranges like 111-120.
    gmt_code_filter = request.GET.get('gmt_code', '').strip()
    if gmt_code_filter:
        products = _filter_products_by_gmt_code(products, gmt_code_filter)

    products = products.order_by('gmt_code', 'name')
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    context = {
        'category': category,
        'products': products,
        'current_gmt_code': gmt_code_filter,
        'page_title': f'{category.name} - Products',
    }
    return render(request, 'catalog/category_detail.html', context)


def product_detail(request, identifier):
    """Product detail view."""
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('weights', 'images'),
        slug=identifier,
        is_available=True
    )
    
    # Get related products from same category
    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(pk=product.pk).select_related('category').prefetch_related('weights', 'images')[:4]
    
    context = {
        'product': product,
        'images': product.images.all(),
        'related_products': related_products,
        'page_title': f'{product.name} - {product.category.name}',
        'meta_title': product.meta_title or product.name,
        'meta_description': product.meta_description or product.description[:160],
    }
    return render(request, 'catalog/product_detail.html', context)


def about(request):
    """About page."""
    context = {
        'page_title': 'About Us',
    }
    return render(request, 'catalog/about.html', context)


def contact(request):
    """Contact page."""
    context = {
        'page_title': 'Contact Us',
    }
    return render(request, 'catalog/contact.html', context)


@login_required
def profile(request):
    """Profile page for authenticated customers."""
    user_orders = Order.objects.filter(user=request.user)
    context = {
        'profile_data': _get_profile_snapshot(request.user),
        'order_count': user_orders.count(),
        'page_title': 'My Profile',
    }
    return render(request, 'catalog/profile.html', context)


@login_required
def orders(request):
    """Order history for the authenticated customer."""
    user_orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related('items__product__category', 'items__weight')
        .order_by('-created_at')
    )
    context = {
        'orders': user_orders,
        'page_title': 'My Orders',
    }
    return render(request, 'catalog/orders.html', context)


def checkout_view(request):
    """Checkout page for direct product purchases."""
    if request.method == 'POST':
        return place_order_view(request)

    checkout_data = _load_checkout_items(request)
    if not checkout_data:
        messages.error(request, 'Select a product before proceeding to checkout.')
        return redirect('catalog:product_list')

    if not checkout_data['pricing_available']:
        messages.error(request, 'One or more products are not available for direct checkout yet.')
        return redirect('catalog:cart')

    form = OrderForm(initial=_get_checkout_form_initial(request))
    return _render_checkout(request, form, checkout_data)


@require_POST
def apply_coupon_view(request):
    """Validate a coupon against the current checkout selection."""
    checkout_data = _load_checkout_items(request)
    if not checkout_data:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Select a product before applying a coupon.'}, status=400)
        messages.error(request, 'Select a product before applying a coupon.')
        return redirect('catalog:product_list')

    coupon_code = _normalize_coupon_code(request.POST.get('coupon_code'))

    if not coupon_code:
        request.session.pop(CHECKOUT_COUPON_SESSION_KEY, None)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            totals = _calculate_checkout_totals(checkout_data, '')
            return JsonResponse({
                'success': True,
                'message': 'Coupon removed.',
                'coupon_removed': True,
                'coupon_code': '',
                'discount_amount': '0.00',
                'original_price': str(totals['original_price']),
                'final_total': str(totals['final_total']),
            })
        messages.info(request, 'Coupon removed from this checkout.')
        return redirect('catalog:checkout')

    totals = _calculate_checkout_totals(checkout_data, coupon_code)
    if totals['discount']:
        request.session[CHECKOUT_COUPON_SESSION_KEY] = coupon_code
        request.session.modified = True
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Coupon {coupon_code} applied successfully!',
                'coupon_code': totals['coupon_code'],
                'discount_amount': str(totals['discount_amount']),
                'original_price': str(totals['original_price']),
                'final_total': str(totals['final_total']),
                'discount_name': totals['discount'].code if totals['discount'] else '',
            })
        messages.success(request, f'Coupon {coupon_code} applied successfully.')
    else:
        request.session.pop(CHECKOUT_COUPON_SESSION_KEY, None)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': totals['coupon_error'] or 'Invalid coupon code.',
                'coupon_code': '',
                'discount_amount': '0.00',
                'original_price': str(totals['original_price']),
                'final_total': str(totals['final_total']),
            })
        messages.error(request, totals['coupon_error'] or 'Invalid coupon code.')

    return redirect('catalog:checkout')


@require_POST
def place_order_view(request):
    """Validate checkout input, create an order, and initiate Cashfree payment."""
    checkout_data = _load_checkout_items(request)
    if not checkout_data:
        messages.error(request, 'Select a product before proceeding to checkout.')
        return redirect('catalog:product_list')

    if not checkout_data['pricing_available']:
        messages.error(request, 'Some products are not available for checkout.')
        return redirect('catalog:cart')

    form = OrderForm(request.POST)
    missing_fields = [
        field_name for field_name in OrderForm.REQUIRED_FIELDS if not request.POST.get(field_name, '').strip()
    ]
    if missing_fields:
        for field_name in missing_fields:
            if field_name not in form.errors:
                form.add_error(field_name, 'This field is required.')

    if form.errors or not form.is_valid():
        messages.error(request, 'Enter all required checkout details before continuing to payment.')
        return _render_checkout(request, form, checkout_data, status=400)

    coupon_code = _normalize_coupon_code(
        request.POST.get('coupon_code') or request.session.get(CHECKOUT_COUPON_SESSION_KEY, '')
    )
    preview_totals = _calculate_checkout_totals(checkout_data, coupon_code)
    if coupon_code and not preview_totals['discount']:
        messages.error(request, preview_totals['coupon_error'] or 'Invalid coupon code.')
        return _render_checkout(request, form, checkout_data, status=400, coupon_code=coupon_code)

    try:
        from .models import OrderItem

        with transaction.atomic():
            discount = None
            discount_amount = Decimal('0.00')
            original_price = Decimal(checkout_data['total_order_price'] or 0)

            if coupon_code:
                discount = (
                    Discount.objects
                    .select_for_update()
                    .prefetch_related('products', 'categories')
                    .filter(code=coupon_code)
                    .first()
                )
                if not discount:
                    messages.error(request, 'Invalid coupon code.')
                    return _render_checkout(request, form, checkout_data, status=400, coupon_code=coupon_code)

                is_valid, coupon_error = discount.validate_for_items(checkout_data['items'], original_price)
                if not is_valid:
                    messages.error(request, coupon_error or 'Invalid coupon code.')
                    return _render_checkout(
                        request,
                        form,
                        checkout_data,
                        status=400,
                        coupon_code=coupon_code,
                        coupon_error=coupon_error,
                    )
                discount_amount = discount.calculate_discount(checkout_data['items'], original_price)

            final_total = max(original_price - discount_amount, Decimal('0.00'))

            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.original_price = original_price
            order.discount = discount
            order.coupon_code = coupon_code if discount else ''
            order.discount_amount = discount_amount
            order.total_price = final_total
            order.payment_status = Order.PAYMENT_PENDING
            order.cashfree_order_id = f'TMP-{uuid.uuid4().hex[:32].upper()}'
            order.save()

            for item in checkout_data['items']:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    weight=item['weight'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    total_price=item['total_price']
                )

            if discount:
                Discount.objects.filter(pk=discount.pk).update(usage_count=F('usage_count') + 1)

            if order.total_price <= 0:
                order.payment_status = Order.PAYMENT_SUCCESS
                order.status = Order.STATUS_PROCESSING

            order.cashfree_order_id = f'ORD-{order.pk:06d}'
            order.save(update_fields=['cashfree_order_id', 'payment_status', 'status', 'updated_at'])

        if order.total_price <= 0:
            request.session.pop(CHECKOUT_SESSION_KEY, None)
            request.session.pop(CHECKOUT_COUPON_SESSION_KEY, None)
            return redirect('catalog:checkout_success', order_id=order.pk)

        cashfree_urls = _build_cashfree_urls(request)
        gateway_order = create_cashfree_order(
            order,
            return_url=cashfree_urls['cashfree_return_url'],
            notify_url=cashfree_urls['notify_url'],
        )

        order.cashfree_order_id = gateway_order['cashfree_order_id']
        order.cashfree_cf_order_id = gateway_order['cashfree_cf_order_id']
        order.cashfree_payment_session_id = gateway_order['payment_session_id']
        order.payment_status = Order.PAYMENT_PENDING
        order.payment_message = ''
        order.save(
            update_fields=[
                'cashfree_order_id',
                'cashfree_cf_order_id',
                'cashfree_payment_session_id',
                'payment_status',
                'payment_message',
                'updated_at',
            ]
        )

        request.session.pop(CHECKOUT_SESSION_KEY, None)
        request.session.pop(CHECKOUT_COUPON_SESSION_KEY, None)
        if gateway_order.get('payment_link'):
            return redirect(gateway_order['payment_link'])

        return render(
            request,
            'catalog/payment_redirect.html',
            {
                'order': order,
                'payment_session_id': order.cashfree_payment_session_id,
                'payment_return_url': cashfree_urls['payment_return_url'],
                'cashfree_mode': 'production'
                if settings.CASHFREE_ENV == 'PRODUCTION'
                else 'sandbox',
                'page_title': 'Redirecting to Payment',
            },
        )
    except CashfreeGatewayError as exc:
        _print_checkout_exception('Cashfree Error', exc)
        logger.error('Cashfree Error: %s', str(exc), exc_info=True)
        if 'order' in locals():
            _update_order_payment_state(order, Order.PAYMENT_FAILED, payment_message=str(exc))
        messages.error(request, 'Payment gateway error. Please try again later.')
        return _render_checkout(request, form, checkout_data, status=200)
    except Exception as exc:
        _print_checkout_exception('Place order error', exc)
        logger.exception('Unexpected checkout error while creating order.')
        if 'order' in locals():
            _update_order_payment_state(order, Order.PAYMENT_FAILED, payment_message=str(exc))
        messages.error(request, 'Something went wrong while creating your order. Please try again.')
        return _render_checkout(request, form, checkout_data, status=200)


def checkout_success(request, order_id):
    """Status page for an order after payment is attempted."""
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__product',
            'items__product__category',
            'items__weight__product__category',
        ),
        pk=order_id,
    )
    context = {
        'order': order,
        'page_title': 'Order Status',
    }
    return render(request, 'catalog/checkout_success.html', context)


def payment_return_view(request):
    """Sync order status after Cashfree redirects the customer back."""
    cashfree_order_id = (request.GET.get('order_id') or '').strip()
    if not cashfree_order_id:
        messages.error(request, 'Payment response was incomplete. Please contact support if money was debited.')
        return redirect('catalog:product_list')

    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__product',
            'items__product__category',
            'items__weight__product__category',
        ),
        cashfree_order_id=cashfree_order_id,
    )

    try:
        _sync_order_from_cashfree(order)
    except CashfreeGatewayError as exc:
        logger.error('Cashfree return sync failed for order %s: %s', order.pk, str(exc), exc_info=True)
        messages.warning(
            request,
            'We received your order, but payment verification is still pending. Please refresh this page shortly.',
        )
    except Exception as exc:
        logger.exception('Unexpected payment return sync error for order %s.', order.pk)
        messages.warning(
            request,
            'We received your order, but payment verification is still pending. Please refresh this page shortly.',
        )

    return redirect('catalog:checkout_success', order_id=order.pk)


@csrf_exempt
@require_POST
def payment_webhook_view(request):
    """Receive Cashfree webhook events and update the order payment state."""
    raw_body = request.body.decode('utf-8')

    try:
        verify_webhook_signature(
            raw_body,
            request.headers.get('x-webhook-signature', ''),
            request.headers.get('x-webhook-timestamp', ''),
        )
        webhook_data = parse_webhook_payload(raw_body)
        order = Order.objects.filter(cashfree_order_id=webhook_data['cashfree_order_id']).first()
        if not order:
            return JsonResponse({'status': 'ignored', 'message': 'Order not found.'}, status=200)

        payment_status = map_payment_status(payment_status=webhook_data['payment_status'])
        payment_time = parse_cashfree_timestamp(webhook_data['payment_time'])
        _update_order_payment_state(
            order,
            payment_status,
            payment_message=webhook_data['payment_message'],
            cashfree_payment_id=webhook_data['cf_payment_id'],
            payment_time=payment_time,
        )
        return JsonResponse({'status': 'ok'})
    except CashfreeWebhookError as exc:
        logger.error('Cashfree webhook rejected: %s', str(exc), exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)
    except Exception as exc:
        logger.exception('Unexpected Cashfree webhook processing error.')
        return JsonResponse({'status': 'error', 'message': 'Unable to process webhook.'}, status=500)


def api_products(request):
    """API endpoint for products (for AJAX requests)."""
    products = Product.objects.filter(is_available=True).values(
        'id', 'name', 'slug', 'gmt_code', 'category__name',
        'length_mm', 'width_mm', 'price'
    )[:20]
    return JsonResponse({'products': list(products)})


def api_search(request):
    """API endpoint for search suggestions."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(
        is_available=True
    ).filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__name__icontains=query) |
        Q(gmt_code__icontains=query)
    ).select_related('category').distinct()[:8]

    results = [
        {
            'name': product.name,
            'category': product.category.name if product.category else '',
            'gmt_code': product.gmt_code,
            'url': product.get_absolute_url(),
        }
        for product in products
    ]

    return JsonResponse({'results': results})


# Cart Functions
def _get_cart(request):
    """Get the cart from session."""
    return request.session.get(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    """Save the cart to session."""
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def cart_view(request):
    """View the shopping cart."""
    cart = _get_cart(request)
    cart_items = []
    total = 0
    
    for product_key, item in cart.items():
        product_id = item.get('product_id', product_key.split('_')[0])
        product = Product.objects.filter(pk=product_id, is_available=True).first()
        if product:
            quantity = item.get('quantity', 1)
            weight_obj, unit_price = _resolve_item_pricing(
                product,
                weight_id=item.get('weight_id'),
                weight_selected=item.get('weight_selected'),
            )
            if unit_price is None:
                unit_price = 0
            
            item_total = unit_price * quantity
            cart_items.append({
                'key': product_key,
                'product': product,
                'weight': weight_obj,
                'weight_selected': _normalize_bool(item.get('weight_selected')),
                'quantity': quantity,
                'unit_price': unit_price,
                'item_total': item_total,
            })
            total += item_total
    
    context = {
        'cart_items': cart_items,
        'cart_total': total,
        'page_title': 'Shopping Cart',
    }
    return render(request, 'catalog/cart.html', context)


@require_POST
def add_to_cart(request):
    """Add a product to the cart."""
    product_id = request.POST.get('product_id')
    weight_id = request.POST.get('weight_id')
    weight_selected = _normalize_bool(request.POST.get('weight_selected'))
    quantity = _normalize_quantity(request.POST.get('quantity'), default=1)
    
    product = Product.objects.filter(pk=product_id, is_available=True).first()
    if not product:
        messages.error(request, 'Product not found or unavailable.')
        return redirect('catalog:product_list')
    
    cart = _get_cart(request)
    product_key = f"{product_id}_{weight_id}" if weight_selected and weight_id else str(product_id)
    
    if product_key in cart:
        cart[product_key]['quantity'] += quantity
    else:
        cart[product_key] = {
            'quantity': quantity,
            'product_id': product_id,
            'weight_id': weight_id if weight_selected else '',
            'weight_selected': weight_selected,
        }
    
    _save_cart(request, cart)
    messages.success(request, f'{product.name} added to cart!')
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item.get('quantity', 0) for item in cart.values())
        return JsonResponse({'success': True, 'cart_count': cart_count, 'message': f'{product.name} added to cart!'})
    
    return redirect('catalog:cart')


@require_POST
def update_cart(request):
    """Update cart item quantity."""
    product_key = request.POST.get('product_key') or request.POST.get('product_id')
    quantity = _normalize_quantity(request.POST.get('quantity'), default=1)
    
    cart = _get_cart(request)
    
    if product_key in cart:
        if quantity > 0:
            cart[product_key]['quantity'] = quantity
        else:
            del cart[product_key]
        _save_cart(request, cart)
        messages.success(request, 'Cart updated.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item.get('quantity', 0) for item in cart.values())
        return JsonResponse({'success': True, 'cart_count': cart_count})
    
    return redirect('catalog:cart')


@require_POST
def remove_from_cart(request):
    """Remove a product from the cart."""
    product_key = request.POST.get('product_key') or request.POST.get('product_id')
    
    cart = _get_cart(request)
    
    if product_key in cart:
        del cart[product_key]
        _save_cart(request, cart)
        messages.success(request, 'Item removed from cart.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item.get('quantity', 0) for item in cart.values())
        return JsonResponse({'success': True, 'cart_count': cart_count})
    
    return redirect('catalog:cart')


def cart_checkout(request):
    """Checkout from cart - redirect to checkout with all items."""
    cart = _get_cart(request)
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('catalog:cart')
    
    checkout_items = []
    for product_key, item in cart.items():
        product_id = item.get('product_id', product_key.split('_')[0])
        weight_id = item.get('weight_id')
        quantity = item.get('quantity', 1)
        checkout_items.append({
            'product_id': product_id,
            'weight_id': weight_id,
            'weight_selected': _normalize_bool(item.get('weight_selected')),
            'quantity': quantity
        })
    
    request.session[CHECKOUT_SESSION_KEY] = checkout_items
    
    return redirect('catalog:checkout')
