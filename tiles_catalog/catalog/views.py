from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse
from .models import Category, Product, CustomerReview
from .forms import ContactForm


def home(request):
    """Homepage view."""
    featured_products = Product.objects.filter(
        is_available=True, 
        is_featured=True
    ).select_related('category', 'material_type')[:8]
    
    marble_textures = Product.objects.filter(
        is_available=True,
        category__slug='marble-texture'
    ).select_related('category', 'material_type')[:4]
    
    featured_categories = Category.objects.filter(
        is_active=True
    ).annotate(
        available_product_count=Count('products', filter=Q(products__is_available=True))
    )[:6]

    customer_reviews = CustomerReview.objects.filter(
        is_active=True
    )[:12]

    context = {
        'featured_products': featured_products,
        'marble_textures': marble_textures,
        'featured_categories': featured_categories,
        'customer_reviews': customer_reviews,
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
            Q(material_type__name__icontains=search_query)
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
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    valid_sorts = ['name', '-name', 'created_at', '-created_at', 'price', '-price']
    if sort in valid_sorts:
        products = products.order_by(sort)
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    current_category = None
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug).first()
    
    context = {
        'products': products,
        'search_query': search_query,
        'current_category': current_category,
        'current_material': material_slug,
        'current_finish': finish_slug,
        'current_sort': sort,
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
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    valid_sorts = ['name', '-name', 'created_at', '-created_at', 'price', '-price']
    if sort in valid_sorts:
        products = products.order_by(sort)
    
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


def product_detail(request, slug):
    """Product detail view."""
    product = get_object_or_404(
        Product.objects.select_related('category', 'material_type', 'finish'),
        slug=slug, 
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
    """Contact page with form."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('catalog:contact')
    else:
        form = ContactForm()
    
    context = {
        'form': form,
        'page_title': 'Contact Us',
    }
    return render(request, 'catalog/contact.html', context)


def api_products(request):
    """API endpoint for products (for AJAX requests)."""
    products = Product.objects.filter(is_available=True).values(
        'id', 'name', 'slug', 'category__name', 'material_type__name',
        'length_mm', 'width_mm', 'price'
    )[:20]
    return JsonResponse({'products': list(products)})


def api_search(request):
    """API endpoint for search suggestions."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    products = Product.objects.filter(
        is_available=True,
        name__icontains=query
    ).values('name', 'slug', 'category__name')[:10]
    
    return JsonResponse({'results': list(products)})
