from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication
    path('login/', views.admin_login, name='login'),
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
    
    # Material Types
    path('materials/', views.material_list, name='material_list'),
    path('materials/add/', views.material_add, name='material_add'),
    path('materials/<int:pk>/edit/', views.material_edit, name='material_edit'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    
    # Finishes
    path('finishes/', views.finish_list, name='finish_list'),
    path('finishes/add/', views.finish_add, name='finish_add'),
    path('finishes/<int:pk>/edit/', views.finish_edit, name='finish_edit'),
    path('finishes/<int:pk>/delete/', views.finish_delete, name='finish_delete'),
    
    # Messages
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/<int:pk>/delete/', views.message_delete, name='message_delete'),

    # Customer Reviews
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/add/', views.review_add, name='review_add'),
    path('reviews/<int:pk>/edit/', views.review_edit, name='review_edit'),
    path('reviews/<int:pk>/delete/', views.review_delete, name='review_delete'),
    path('reviews/<int:pk>/toggle-active/', views.review_toggle_active, name='review_toggle_active'),
]
