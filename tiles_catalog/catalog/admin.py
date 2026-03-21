from django.contrib import admin
from .models import Category, MaterialType, Finish, Product, ProductImage, Contact, Order, CustomerReview


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']


@admin.register(MaterialType)
class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Finish)
class FinishAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'material_type', 'size_display', 'is_available', 'is_featured', 'created_at']
    list_filter = ['category', 'material_type', 'finish', 'is_available', 'is_featured']
    search_fields = ['name', 'description', 'sku', 'code', 'color']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    list_editable = ['is_available', 'is_featured']
    readonly_fields = ['sku', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'code', 'category', 'material_type', 'description')
        }),
        ('Specifications', {
            'fields': ('length_mm', 'width_mm', 'thickness_mm', 'finish', 'color')
        }),
        ('Pricing & SKU', {
            'fields': ('price', 'sku')
        }),
        ('Status', {
            'fields': ('is_available', 'is_featured')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'order', 'created_at']
    list_filter = ['is_primary', 'product__category']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
    list_filter = ['is_read']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['name', 'email', 'phone', 'subject', 'message', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'product',
        'full_name',
        'phone_number',
        'quantity',
        'total_price',
        'payment_status',
        'status',
        'created_at',
    ]
    list_filter = ['payment_status', 'status', 'created_at', 'product__category']
    search_fields = [
        'full_name',
        'phone_number',
        'email',
        'user__email',
        'user__username',
        'product__name',
        'cashfree_order_id',
        'cashfree_payment_id',
    ]
    readonly_fields = [
        'product',
        'quantity',
        'unit_price',
        'total_price',
        'cashfree_order_id',
        'cashfree_cf_order_id',
        'cashfree_payment_session_id',
        'cashfree_payment_id',
        'payment_completed_at',
        'created_at',
        'updated_at',
    ]


@admin.register(CustomerReview)
class CustomerReviewAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'customer_location', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['customer_name', 'customer_location', 'review_text']
    list_editable = ['is_active']
