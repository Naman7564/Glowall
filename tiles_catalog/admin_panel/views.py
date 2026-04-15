import re

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.db import transaction
from django.db.models import Count, Q, IntegerField
from django.db.models.functions import Cast, Trim
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from catalog.models import Product, Category, ProductImage, Finish, CustomerReview, Order, Poster
from .forms import (
    ProductForm, CategoryForm, ProductImageFormSet,
    FinishForm, CustomerReviewForm, OrderStatusForm, PosterForm
)


def is_staff(user):
    """Check if user is staff."""
    return user.is_staff


def _parse_gmt_code_range(value):
    """Parse a single code or a numeric range into inclusive bounds."""
    match = re.fullmatch(r"\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*", value or "")
    if not match:
        return None

    lower_bound = int(match.group(1))
    upper_bound = int(match.group(2) or match.group(1))
    if lower_bound > upper_bound:
        lower_bound, upper_bound = upper_bound, lower_bound
    return lower_bound, upper_bound


def _filter_products_by_gmt_range(queryset, value):
    bounds = _parse_gmt_code_range(value)
    if not bounds:
        return queryset

    lower_bound, upper_bound = bounds
    queryset = queryset.filter(gmt_code__regex=r"^\s*\d+\s*$").annotate(
        gmt_code_number=Cast(Trim("gmt_code"), IntegerField())
    )
    if lower_bound == upper_bound:
        return queryset.filter(gmt_code_number=lower_bound)
    return queryset.filter(gmt_code_number__gte=lower_bound, gmt_code_number__lte=upper_bound)


@login_required
@user_passes_test(is_staff)
@require_POST
def admin_logout(request):
    """Admin logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('catalog:home')


@login_required
@user_passes_test(is_staff)
def dashboard(request):
    """Admin dashboard view."""
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    available_products = Product.objects.filter(is_available=True).count()
    featured_products = Product.objects.filter(is_featured=True).count()
    total_orders = Order.objects.count()
    recent_products = Product.objects.select_related('category')[:5]
    
    # Products by category
    categories_with_count = Category.objects.annotate(
        total_product_count=Count('products')
    ).order_by('-total_product_count')[:5]
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'available_products': available_products,
        'featured_products': featured_products,
        'total_orders': total_orders,
        'recent_products': recent_products,
        'categories_with_count': categories_with_count,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# Product Management
@login_required
@user_passes_test(is_staff)
def product_list(request):
    """Admin product list view."""
    products = Product.objects.select_related('category').all()
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filter by availability
    availability = request.GET.get('availability')
    if availability == 'available':
        products = products.filter(is_available=True)
    elif availability == 'unavailable':
        products = products.filter(is_available=False)

    # Filter by GMT code range (e.g. 111-120 or 111–120)
    gmt_code = request.GET.get('gmt_code', '').strip()
    if gmt_code:
        products = _filter_products_by_gmt_range(products, gmt_code)

    # Search
    search = request.GET.get('q', '').strip()
    if search:
        search_filters = (
            Q(name__icontains=search)
            | Q(gmt_code__icontains=search)
        )
        products = products.filter(search_filters)

    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'current_category': category_id,
        'current_availability': availability,
        'current_gmt_code': gmt_code,
        'search_query': search,
    }
    return render(request, 'admin_panel/product_list.html', context)


@login_required
@user_passes_test(is_staff)
def product_add(request):
    """Add new product view."""
    if request.method == 'POST':
        product = Product()
        form = ProductForm(request.POST, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                product = form.save()
                formset.instance = product
                formset.save()
            messages.success(request, f'Product "{product.name}" has been created.')
            return redirect('admin_panel:product_list')
    else:
        product = Product()
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)

    marble_category_ids = list(Category.objects.filter(Q(name__icontains='marble') | Q(name__icontains='marbel') | Q(slug__icontains='marble') | Q(slug__icontains='marbel')).values_list('id', flat=True))

    context = {
        'form': form,
        'formset': formset,
        'title': 'Add New Product',
        'marble_category_ids': marble_category_ids,
    }
    return render(request, 'admin_panel/product_form.html', context)


@login_required
@user_passes_test(is_staff)
def product_edit(request, pk):
    """Edit product view."""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                product = form.save()
                formset.instance = product
                formset.save()
            messages.success(request, f'Product "{product.name}" has been updated.')
            return redirect('admin_panel:product_list')
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)

    marble_category_ids = list(Category.objects.filter(Q(name__icontains='marble') | Q(name__icontains='marbel') | Q(slug__icontains='marble') | Q(slug__icontains='marbel')).values_list('id', flat=True))

    context = {
        'form': form,
        'formset': formset,
        'product': product,
        'title': f'Edit Product: {product.name}',
        'marble_category_ids': marble_category_ids,
    }
    return render(request, 'admin_panel/product_form.html', context)


@login_required
@user_passes_test(is_staff)
def product_delete(request, pk):
    """Delete product view."""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" has been deleted.')
        return redirect('admin_panel:product_list')
    
    context = {'product': product}
    return render(request, 'admin_panel/product_confirm_delete.html', context)


@login_required
@user_passes_test(is_staff)
@require_POST
def product_toggle_featured(request, pk):
    """Toggle product featured status."""
    product = get_object_or_404(Product, pk=pk)
    product.is_featured = not product.is_featured
    product.save()
    return JsonResponse({
        'success': True,
        'is_featured': product.is_featured
    })


@login_required
@user_passes_test(is_staff)
@require_POST
def product_toggle_available(request, pk):
    """Toggle product availability."""
    product = get_object_or_404(Product, pk=pk)
    product.is_available = not product.is_available
    product.save()
    return JsonResponse({
        'success': True,
        'is_available': product.is_available
    })


# Category Management
@login_required
@user_passes_test(is_staff)
def category_list(request):
    """Admin category list view."""
    categories = Category.objects.annotate(
        total_product_count=Count('products')
    ).all()
    
    context = {'categories': categories}
    return render(request, 'admin_panel/category_list.html', context)


@login_required
@user_passes_test(is_staff)
def category_add(request):
    """Add new category view."""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" has been created.')
            return redirect('admin_panel:category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': 'Add New Category',
    }
    return render(request, 'admin_panel/category_form.html', context)


@login_required
@user_passes_test(is_staff)
def category_edit(request, pk):
    """Edit category view."""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" has been updated.')
            return redirect('admin_panel:category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}',
    }
    return render(request, 'admin_panel/category_form.html', context)


@login_required
@user_passes_test(is_staff)
def category_delete(request, pk):
    """Delete category view."""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" has been deleted.')
        return redirect('admin_panel:category_list')
    
    context = {'category': category}
    return render(request, 'admin_panel/category_confirm_delete.html', context)


# Finish Management
@login_required
@user_passes_test(is_staff)
def finish_list(request):
    """Finish list view."""
    finishes = Finish.objects.annotate(
        product_count=Count('products')
    ).all()
    context = {'finishes': finishes}
    return render(request, 'admin_panel/finish_list.html', context)


@login_required
@user_passes_test(is_staff)
def finish_add(request):
    """Add new finish."""
    if request.method == 'POST':
        form = FinishForm(request.POST)
        if form.is_valid():
            finish = form.save()
            messages.success(request, f'Finish "{finish.name}" has been created.')
            return redirect('admin_panel:finish_list')
    else:
        form = FinishForm()
    
    context = {'form': form, 'title': 'Add New Finish'}
    return render(request, 'admin_panel/finish_form.html', context)


@login_required
@user_passes_test(is_staff)
def finish_edit(request, pk):
    """Edit finish."""
    finish = get_object_or_404(Finish, pk=pk)
    
    if request.method == 'POST':
        form = FinishForm(request.POST, instance=finish)
        if form.is_valid():
            form.save()
            messages.success(request, f'Finish "{finish.name}" has been updated.')
            return redirect('admin_panel:finish_list')
    else:
        form = FinishForm(instance=finish)
    
    context = {'form': form, 'finish': finish, 'title': f'Edit Finish: {finish.name}'}
    return render(request, 'admin_panel/finish_form.html', context)


@login_required
@user_passes_test(is_staff)
def finish_delete(request, pk):
    """Delete finish."""
    finish = get_object_or_404(Finish, pk=pk)
    
    if request.method == 'POST':
        name = finish.name
        finish.delete()
        messages.success(request, f'Finish "{name}" has been deleted.')
        return redirect('admin_panel:finish_list')
    
    context = {'finish': finish}
    return render(request, 'admin_panel/finish_confirm_delete.html', context)

# Customer Reviews
@login_required
@user_passes_test(is_staff)
def review_list(request):
    """Customer review list view."""
    reviews = CustomerReview.objects.all()

    active_status = request.GET.get('status')
    if active_status == 'active':
        reviews = reviews.filter(is_active=True)
    elif active_status == 'inactive':
        reviews = reviews.filter(is_active=False)

    search = request.GET.get('q', '')
    if search:
        reviews = reviews.filter(
            Q(customer_name__icontains=search) |
            Q(customer_location__icontains=search) |
            Q(review_text__icontains=search)
        )

    context = {
        'reviews': reviews,
        'current_status': active_status,
        'search_query': search,
    }
    return render(request, 'admin_panel/review_list.html', context)


@login_required
@user_passes_test(is_staff)
def review_add(request):
    """Add a customer review."""
    if request.method == 'POST':
        form = CustomerReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save()
            messages.success(request, f'Customer review "{review}" has been created.')
            return redirect('admin_panel:review_list')
    else:
        form = CustomerReviewForm()

    context = {
        'form': form,
        'title': 'Add Customer Review',
    }
    return render(request, 'admin_panel/review_form.html', context)


@login_required
@user_passes_test(is_staff)
def review_edit(request, pk):
    """Edit a customer review."""
    review = get_object_or_404(CustomerReview, pk=pk)

    if request.method == 'POST':
        form = CustomerReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            review = form.save()
            messages.success(request, f'Customer review "{review}" has been updated.')
            return redirect('admin_panel:review_list')
    else:
        form = CustomerReviewForm(instance=review)

    context = {
        'form': form,
        'review': review,
        'title': 'Edit Customer Review',
    }
    return render(request, 'admin_panel/review_form.html', context)


@login_required
@user_passes_test(is_staff)
def review_delete(request, pk):
    """Delete a customer review."""
    review = get_object_or_404(CustomerReview, pk=pk)

    if request.method == 'POST':
        review_label = str(review)
        review.delete()
        messages.success(request, f'Customer review "{review_label}" has been deleted.')
        return redirect('admin_panel:review_list')

    context = {'review': review}
    return render(request, 'admin_panel/review_confirm_delete.html', context)


@login_required
@user_passes_test(is_staff)
@require_POST
def review_toggle_active(request, pk):
    """Toggle review active status."""
    review = get_object_or_404(CustomerReview, pk=pk)
    review.is_active = not review.is_active
    review.save(update_fields=['is_active'])
    return JsonResponse({
        'success': True,
        'is_active': review.is_active,
    })


# Order Management
@login_required
@user_passes_test(is_staff)
def order_list(request):
    """Admin order list view."""
    orders = Order.objects.select_related('product', 'user').all()
    
    # Calculate order statistics
    total_orders = Order.objects.count()
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today).count()
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    # Filter by payment status
    payment_status = request.GET.get('payment')
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Search by customer name, email, phone, or order ID
    search = request.GET.get('q', '')
    if search:
        orders = orders.filter(
            Q(full_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(pk__icontains=search) |
            Q(product__name__icontains=search)
        )
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'today_orders': today_orders,
        'current_status': status,
        'current_payment': payment_status,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search,
        'status_choices': Order.STATUS_CHOICES,
        'payment_choices': Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, 'admin_panel/order_list.html', context)


@login_required
@user_passes_test(is_staff)
def order_detail(request, pk):
    """View order detail."""
    order = get_object_or_404(Order.objects.select_related('product', 'user'), pk=pk)
    
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Order #{order.pk} status has been updated.')
            return redirect('admin_panel:order_detail', pk=order.pk)
    else:
        form = OrderStatusForm(instance=order)
    
    context = {
        'order': order,
        'form': form,
    }
    return render(request, 'admin_panel/order_detail.html', context)


# Poster Management
@login_required
@user_passes_test(is_staff)
def poster_list(request):
    """Poster list view."""
    posters = Poster.objects.all()

    active_status = request.GET.get('status')
    if active_status == 'active':
        posters = posters.filter(is_active=True)
    elif active_status == 'inactive':
        posters = posters.filter(is_active=False)

    context = {
        'posters': posters,
        'current_status': active_status,
    }
    return render(request, 'admin_panel/poster_list.html', context)


@login_required
@user_passes_test(is_staff)
def poster_add(request):
    """Add a new poster."""
    if request.method == 'POST':
        form = PosterForm(request.POST, request.FILES)
        if form.is_valid():
            poster = form.save()
            messages.success(request, f'Poster "{poster}" has been created.')
            return redirect('admin_panel:poster_list')
    else:
        form = PosterForm()

    context = {
        'form': form,
        'title': 'Add New Poster',
    }
    return render(request, 'admin_panel/poster_form.html', context)


@login_required
@user_passes_test(is_staff)
def poster_edit(request, pk):
    """Edit a poster."""
    poster = get_object_or_404(Poster, pk=pk)

    if request.method == 'POST':
        form = PosterForm(request.POST, request.FILES, instance=poster)
        if form.is_valid():
            poster = form.save()
            messages.success(request, f'Poster "{poster}" has been updated.')
            return redirect('admin_panel:poster_list')
    else:
        form = PosterForm(instance=poster)

    context = {
        'form': form,
        'poster': poster,
        'title': 'Edit Poster',
    }
    return render(request, 'admin_panel/poster_form.html', context)


@login_required
@user_passes_test(is_staff)
def poster_delete(request, pk):
    """Delete a poster."""
    poster = get_object_or_404(Poster, pk=pk)

    if request.method == 'POST':
        poster_label = str(poster)
        poster.delete()
        messages.success(request, f'Poster "{poster_label}" has been deleted.')
        return redirect('admin_panel:poster_list')

    context = {'poster': poster}
    return render(request, 'admin_panel/poster_confirm_delete.html', context)


@login_required
@user_passes_test(is_staff)
@require_POST
def poster_toggle_active(request, pk):
    """Toggle poster active status."""
    poster = get_object_or_404(Poster, pk=pk)
    poster.is_active = not poster.is_active
    poster.save(update_fields=['is_active'])
    return JsonResponse({
        'success': True,
        'is_active': poster.is_active,
    })
