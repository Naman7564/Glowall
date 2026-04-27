from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication
    path('logout/', views.admin_logout, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/toggle-featured/', views.product_toggle_featured, name='product_toggle_featured'),
    path('products/<int:pk>/toggle-available/', views.product_toggle_available, name='product_toggle_available'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
        
    # Customer Reviews
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/add/', views.review_add, name='review_add'),
    path('reviews/<int:pk>/edit/', views.review_edit, name='review_edit'),
    path('reviews/<int:pk>/delete/', views.review_delete, name='review_delete'),
    path('reviews/<int:pk>/toggle-active/', views.review_toggle_active, name='review_toggle_active'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),

    # Posters
    path('posters/', views.poster_list, name='poster_list'),
    path('posters/add/', views.poster_add, name='poster_add'),
    path('posters/<int:pk>/edit/', views.poster_edit, name='poster_edit'),
    path('posters/<int:pk>/delete/', views.poster_delete, name='poster_delete'),
    path('posters/<int:pk>/toggle-active/', views.poster_toggle_active, name='poster_toggle_active'),
]
