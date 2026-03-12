from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('gallery/', views.gallery, name='gallery'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    # API endpoints
    path('api/products/', views.api_products, name='api_products'),
    path('api/search/', views.api_search, name='api_search'),
    
    # Payment endpoints
    path('checkout/<int:product_id>/', views.create_checkout_session, name='create_checkout_session'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
]
