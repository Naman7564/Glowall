import re

with open('catalog/views.py', 'r') as f:
    content = f.read()

# 1. Replace _load_checkout_item
new_load_checkout = """def _load_checkout_items(request):
    product_id = request.GET.get('product') or request.POST.get('product_id')
    quantity_value = request.GET.get('quantity') or request.POST.get('quantity')
    weight_id = request.GET.get('weight_id') or request.POST.get('weight_id')
    
    checkout_data = request.session.get(CHECKOUT_SESSION_KEY, [])
    if isinstance(checkout_data, dict):
        checkout_data = [checkout_data]

    if product_id:
        checkout_data = [{
            'product_id': product_id,
            'quantity': _normalize_quantity(quantity_value, default=1),
            'weight_id': weight_id,
        }]
        request.session[CHECKOUT_SESSION_KEY] = checkout_data
    elif checkout_data:
        for item in checkout_data:
            item['quantity'] = _normalize_quantity(item.get('quantity'), default=1)
        request.session[CHECKOUT_SESSION_KEY] = checkout_data
    else:
        return None

    resolved_items = []
    total_order_price = 0
    all_pricing_available = True

    from .models import ProductWeight

    for item_data in checkout_data:
        product = Product.objects.filter(
            pk=item_data.get('product_id'),
            is_available=True,
        ).select_related('category').first()

        if not product:
            continue

        weight_id = item_data.get('weight_id')
        weight_obj = None
        if weight_id:
            weight_obj = ProductWeight.objects.filter(id=weight_id, product=product).first()
            
        unit_price = product.price
        if weight_obj and weight_obj.price is not None:
            unit_price = weight_obj.price

        if unit_price is None:
            all_pricing_available = False
            unit_price = 0
            
        quantity = item_data['quantity']
        total_price = unit_price * quantity
        total_order_price += total_price

        resolved_items.append({
            'product': product,
            'weight': weight_obj,
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
"""
content = re.sub(r'def _load_checkout_item\(request\):.*?return checkout_item\n', new_load_checkout, content, flags=re.DOTALL)

# 2. Update checkout_view
old_checkout_view = """def checkout_view(request):
    \"\"\"Display the checkout form and order summary.\"\"\"
    checkout_item = _load_checkout_item(request)
    if not checkout_item:
        messages.error(request, 'Select a product before proceeding to checkout.')
        return redirect('catalog:product_list')

    if not checkout_item['pricing_available']:
        messages.error(request, 'This product is not available for direct checkout yet.')
        return redirect(checkout_item['product'].get_absolute_url())

    form = OrderForm(initial=_get_checkout_form_initial(request))
    return _render_checkout(request, form, checkout_item)"""

new_checkout_view = """def checkout_view(request):
    \"\"\"Display the checkout form and order summary.\"\"\"
    checkout_data = _load_checkout_items(request)
    if not checkout_data:
        messages.error(request, 'Select a product before proceeding to checkout.')
        return redirect('catalog:product_list')

    if not checkout_data['pricing_available']:
        messages.error(request, 'One or more products are not available for direct checkout yet.')
        return redirect('catalog:cart')

    form = OrderForm(initial=_get_checkout_form_initial(request))
    return _render_checkout(request, form, checkout_data)"""
content = content.replace(old_checkout_view, new_checkout_view)

# 3. Update _render_checkout signature
old_render = "def _render_checkout(request, form, checkout_item, status=200):"
new_render = "def _render_checkout(request, form, checkout_data, status=200):"
content = content.replace(old_render, new_render)
content = content.replace("'checkout_item': checkout_item,", "'checkout_data': checkout_data,")

# 4. Update cart_checkout
old_cart_checkout = """def cart_checkout(request):
    \"\"\"Checkout from cart - redirect to checkout with first item or show cart.\"\"\"
    cart = _get_cart(request)
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('catalog:cart')
    
    # Get first item for checkout (simple approach)
    first_item = list(cart.items())[0]
    product_key, item = first_item
    quantity = item.get('quantity', 1)
    product_id = item.get('product_id', product_key.split('_')[0])
    weight_id = item.get('weight_id')
    
    # Clear cart after checkout initiation
    request.session[CHECKOUT_SESSION_KEY] = {
        'product_id': product_id,
        'quantity': quantity,
        'weight_id': weight_id,
    }
    
    return redirect('catalog:checkout')"""

new_cart_checkout = """def cart_checkout(request):
    \"\"\"Checkout from cart - redirect to checkout with all items.\"\"\"
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
            'quantity': quantity
        })
    
    request.session[CHECKOUT_SESSION_KEY] = checkout_items
    
    return redirect('catalog:checkout')"""
content = content.replace(old_cart_checkout, new_cart_checkout)

# 5. Update place_order_view
old_place_order = """def place_order_view(request):
    \"\"\"Validate checkout input, create an order, and initiate Cashfree payment.\"\"\"
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
        order.save()"""

new_place_order = """def place_order_view(request):
    \"\"\"Validate checkout input, create an order, and initiate Cashfree payment.\"\"\"
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

    try:
        from .models import OrderItem
        order = form.save(commit=False)
        if request.user.is_authenticated:
            order.user = request.user
        order.total_price = checkout_data['total_order_price']
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
            )"""
content = content.replace(old_place_order, new_place_order)

# Update return _render_checkout(request, form, checkout_item, status=400)
content = content.replace("return _render_checkout(request, form, checkout_item, status=400)", "return _render_checkout(request, form, checkout_data, status=400)")


with open('catalog/views.py', 'w') as f:
    f.write(content)
