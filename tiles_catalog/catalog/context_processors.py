from .models import Category


def categories_context(request):
    """Make categories available to all templates."""
    return {
        'categories': Category.objects.filter(is_active=True)
    }
