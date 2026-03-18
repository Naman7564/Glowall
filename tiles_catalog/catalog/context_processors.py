from .models import Category

CART_SESSION_KEY = 'shopping_cart'


def categories_context(request):
    """Make categories available to all templates."""
    return {
        'categories': Category.objects.filter(is_active=True)
    }


def cart_context(request):
    """Make cart count available to all templates."""
    cart = request.session.get(CART_SESSION_KEY, {})
    cart_count = sum(item.get('quantity', 0) for item in cart.values())
    return {
        'cart_count': cart_count
    }
