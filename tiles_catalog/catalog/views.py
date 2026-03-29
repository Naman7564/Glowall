import logging
import re
import traceback
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, IntegerField
from django.db.models.functions import Cast, Trim
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Category, Product, CustomerReview, Order, MaterialType, Finish, Poster
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


def _print_checkout_exception(label, exc):
    print(f'{label}: {exc.__class__.__name__}: {exc}')
    traceback.print_exc()


def _load_checkout_item(request):
    """Resolve the active checkout product and quantity from request/session."""
    product_id = request.GET.get('product') or request.POST.get('product_id')
    quantity_value = request.GET.get('quantity') or request.POST.get('quantity')
    checkout_data = request.session.get(CHECKOUT_SESSION_KEY, {})

    if product_id:
        checkout_data = {
            'product_id': product_id,
            'quantity': _normalize_quantity(quantity_value, default=1),
        }
        request.session[CHECKOUT_SESSION_KEY] = checkout_data
    elif checkout_data:
        checkout_data['quantity'] = _normalize_quantity(checkout_data.get('quantity'), default=1)
        request.session[CHECKOUT_SESSION_KEY] = checkout_data
    else:
        return None

    product = Product.objects.filter(
        pk=checkout_data.get('product_id'),
        is_available=True,
    ).select_related('category', 'material_type', 'finish').first()

    if not product:
        request.session.pop(CHECKOUT_SESSION_KEY, None)
        return None

    if product.price is None:
        request.session.pop(CHECKOUT_SESSION_KEY, None)
        return {
            'product': product,
            'quantity': checkout_data['quantity'],
            'pricing_available': False,
        }

    quantity = checkout_data['quantity']
    unit_price = product.price
    total_price = unit_price * quantity

    checkout_item = {
        'product': product,
        'quantity': quantity,
        'unit_price': unit_price,
        'total_price': total_price,
        'pricing_available': True,
    }

    request.session[CHECKOUT_SESSION_KEY] = {
        'product_id': product.pk,
        'quantity': quantity,
    }
    return checkout_item


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


def _render_checkout(request, form, checkout_item, status=200):
    context = {
        'form': form,
        'checkout_item': checkout_item,
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
    ).select_related('category', 'material_type')[:8]
    
    marble_textures = Product.objects.filter(
        is_available=True,
        category__slug='marbels'
    ).select_related('category', 'material_type')[:4]
    
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
        'page_title': 'Premium Tiles & Marble Showroom',
    }
    return render(request, 'catalog/home.html', context)


def product_list(request):
    """Product listing with filters and search."""
    products = Product.objects.filter(is_available=True).select_related('category', 'material_type', 'finish')
    
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(material_type__name__icontains=search_query) |
            Q(gmt_code__icontains=search_query)
        ).distinct()
    
    # Filter by category
    category_slug = request.GET.get('category', '')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Filter by material type
    material_slug = request.GET.get('material', '')
    if material_slug:
        products = products.filter(material_type__slug=material_slug)
    
    # Filter by finish
    finish_slug = request.GET.get('finish', '')
    if finish_slug:
        products = products.filter(finish__slug=finish_slug)
    
    # Filter by color
    color_name = request.GET.get('color', '')
    if color_name:
        products = products.filter(color__icontains=color_name)
    
    # Filter by availability
    availability = request.GET.get('availability', '')
    if availability == 'available':
        products = products.filter(is_available=True)
    
    # GMT code filtering accepts exact values like 111 and ranges like 111-120.
    sort = request.GET.get('sort', 'code')
    if sort and sort != 'code':
        products = _filter_products_by_gmt_code(products, sort)
    
    # Always order by code
    products = products.order_by('code')
    
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
    all_materials = MaterialType.objects.all().order_by('name')
    all_finishes = Finish.objects.all().order_by('name')
    
    context = {
        'products': products,
        'search_query': search_query,
        'current_category': category_slug,
        'current_material': material_slug,
        'current_finish': finish_slug,
        'current_sort': sort,
        'all_categories': all_categories,
        'all_materials': all_materials,
        'all_finishes': all_finishes,
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
    ).select_related('category', 'material_type')
    
    # GMT code filtering accepts exact values like 111 and ranges like 111-120.
    sort = request.GET.get('sort', 'code')
    if sort and sort != 'code':
        products = _filter_products_by_gmt_code(products, sort)
    
    # Always order by code
    products = products.order_by('code')
    
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
        'current_sort': sort,
        'page_title': f'{category.name} - Products',
    }
    return render(request, 'catalog/category_detail.html', context)


def product_detail(request, identifier):
    """Product detail view."""
    product_lookup = {'slug': identifier}
    if str(identifier).isdigit():
        product_lookup = {'code': int(identifier)}

    product = get_object_or_404(
        Product.objects.select_related('category', 'material_type', 'finish'),
        **product_lookup,
        is_available=True
    )
    
    # Get related products from same category
    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(pk=product.pk).select_related('category')[:4]
    
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
        .select_related('product', 'product__category')
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

    checkout_item = _load_checkout_item(request)
    if not checkout_item:
        messages.error(request, 'Select a product before proceeding to checkout.')
        return redirect('catalog:product_list')

    if not checkout_item['pricing_available']:
        messages.error(request, 'This product is not available for direct checkout yet.')
        return redirect(checkout_item['product'].get_absolute_url())

    form = OrderForm(initial=_get_checkout_form_initial(request))
    return _render_checkout(request, form, checkout_item)


@require_POST
def place_order_view(request):
    """Validate checkout input, create an order, and initiate Cashfree payment."""
    checkout_item = _load_checkout_item(request)
    if not checkout_item:
        messages.error(request, 'Select a product before proceeding to checkout.')
        return redirect('catalog:product_list')

    if not checkout_item['pricing_available']:
        messages.error(request, 'This product is not available for direct checkout yet.')
        return redirect(checkout_item['product'].get_absolute_url())

    form = OrderForm(request.POST)
    missing_fields = [
        field_name for field_name in OrderForm.REQUIRED_FIELDS if not request.POST.get(field_name, '').strip()
    ]
    if missing_fields:
        for field_name in missing_fields:
            if field_name not in form.errors:
                form.add_error(field_name, 'This field is required.')

    missing_checkout_fields = [
        field_name for field_name in ('product_id', 'quantity') if not request.POST.get(field_name, '').strip()
    ]
    invalid_checkout_fields = []
    product_id = (request.POST.get('product_id') or '').strip()
    quantity = (request.POST.get('quantity') or '').strip()

    if product_id and not product_id.isdigit():
        invalid_checkout_fields.append('product_id')

    if quantity:
        try:
            if int(quantity) < 1:
                invalid_checkout_fields.append('quantity')
        except (TypeError, ValueError):
            invalid_checkout_fields.append('quantity')

    if missing_checkout_fields or invalid_checkout_fields:
        logger.error(
            'Incomplete checkout POST data. Missing=%s Invalid=%s',
            missing_checkout_fields,
            invalid_checkout_fields,
        )
        print(
            'Place order validation error: '
            f'missing={missing_checkout_fields} invalid={invalid_checkout_fields}'
        )
        form.add_error(None, 'Checkout request data is incomplete. Please refresh the page and try again.')
        messages.error(request, 'Checkout request is incomplete. Please review your details and try again.')
        return _render_checkout(request, form, checkout_item, status=400)

    if form.errors or not form.is_valid():
        messages.error(request, 'Enter all required checkout details before continuing to payment.')
        return _render_checkout(request, form, checkout_item, status=400)

    try:
        order = form.save(commit=False)
        if request.user.is_authenticated:
            order.user = request.user
        order.product = checkout_item['product']
        order.quantity = checkout_item['quantity']
        order.unit_price = checkout_item['unit_price']
        order.total_price = checkout_item['total_price']
        order.payment_status = Order.PAYMENT_PENDING
        # Reserve a unique placeholder before the first save to avoid unique-key collisions on blank values.
        order.cashfree_order_id = f'TMP-{uuid.uuid4().hex[:32].upper()}'
        order.save()

        order.cashfree_order_id = f'ORD-{order.pk:06d}'
        order.save(update_fields=['cashfree_order_id', 'updated_at'])

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
        return _render_checkout(request, form, checkout_item, status=200)
    except Exception as exc:
        _print_checkout_exception('Place order error', exc)
        logger.exception('Unexpected checkout error while creating order.')
        if 'order' in locals():
            _update_order_payment_state(order, Order.PAYMENT_FAILED, payment_message=str(exc))
        messages.error(request, 'Something went wrong while creating your order. Please try again.')
        return _render_checkout(request, form, checkout_item, status=200)


def checkout_success(request, order_id):
    """Status page for an order after payment is attempted."""
    order = get_object_or_404(
        Order.objects.select_related('product', 'product__category', 'product__material_type'),
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
        Order.objects.select_related('product', 'product__category', 'product__material_type'),
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
        'id', 'name', 'slug', 'gmt_code', 'category__name', 'material_type__name',
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
        Q(material_type__name__icontains=query) |
        Q(gmt_code__icontains=query)
    ).select_related('category', 'material_type').distinct()[:8]

    results = [
        {
            'name': product.name,
            'code': product.code,
            'category': product.category.name if product.category else '',
            'material': product.material_type.name if product.material_type else '',
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
    
    for product_id, item in cart.items():
        product = Product.objects.filter(pk=product_id, is_available=True).first()
        if product:
            quantity = item.get('quantity', 1)
            item_total = (product.price or 0) * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
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
    quantity = _normalize_quantity(request.POST.get('quantity'), default=1)
    
    product = Product.objects.filter(pk=product_id, is_available=True).first()
    if not product:
        messages.error(request, 'Product not found or unavailable.')
        return redirect('catalog:product_list')
    
    cart = _get_cart(request)
    product_key = str(product_id)
    
    if product_key in cart:
        cart[product_key]['quantity'] += quantity
    else:
        cart[product_key] = {'quantity': quantity}
    
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
    product_id = request.POST.get('product_id')
    quantity = _normalize_quantity(request.POST.get('quantity'), default=1)
    
    cart = _get_cart(request)
    product_key = str(product_id)
    
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
    product_id = request.POST.get('product_id')
    
    cart = _get_cart(request)
    product_key = str(product_id)
    
    if product_key in cart:
        del cart[product_key]
        _save_cart(request, cart)
        messages.success(request, 'Item removed from cart.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item.get('quantity', 0) for item in cart.values())
        return JsonResponse({'success': True, 'cart_count': cart_count})
    
    return redirect('catalog:cart')


def cart_checkout(request):
    """Checkout from cart - redirect to checkout with first item or show cart."""
    cart = _get_cart(request)
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('catalog:cart')
    
    # Get first item for checkout (simple approach)
    first_item = list(cart.items())[0]
    product_id, item = first_item
    quantity = item.get('quantity', 1)
    
    # Clear cart after checkout initiation
    request.session[CHECKOUT_SESSION_KEY] = {
        'product_id': product_id,
        'quantity': quantity,
    }
    
    return redirect('catalog:checkout')
