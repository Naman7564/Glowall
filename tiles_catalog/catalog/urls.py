from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('orders/', views.orders, name='orders'),
    path('products/', views.product_list, name='product_list'),
    path('products/category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('products/<int:code>/', views.product_detail, name='product_detail'),
    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', views.cart_checkout, name='cart_checkout'),
    # Checkout
    path('checkout/', views.checkout_view, name='checkout'),
    path('place-order/', views.place_order_view, name='place_order'),
    path('checkout/success/<int:order_id>/', views.checkout_success, name='checkout_success'),
    path('payment-success/', views.payment_return_view, name='payment_return'),
    path('payment-webhook/', views.payment_webhook_view, name='payment_webhook'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    # API endpoints
    path('api/products/', views.api_products, name='api_products'),
    path('api/search/', views.api_search, name='api_search'),
]
