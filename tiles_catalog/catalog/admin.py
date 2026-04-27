from django.contrib import admin
from .models import Category, Product, ProductImage, ProductWeight, Order, CustomerReview


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'order']


class ProductWeightInline(admin.TabularInline):
    model = ProductWeight
    extra = 1
    fields = ['value_kg', 'price', 'order']


class GMTCodeFilter(admin.SimpleListFilter):
    title = 'GMT Code'
    parameter_name = 'gmt_code'

    def lookups(self, request, model_admin):
        codes = (
            Product.objects.exclude(gmt_code='')
            .order_by('gmt_code')
            .values_list('gmt_code', flat=True)
            .distinct()
        )
        return [(code, code) for code in codes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gmt_code=self.value())
        return queryset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['gmt_code', 'name', 'category', 'specification_display', 'is_available', 'is_featured', 'created_at']
    list_filter = [GMTCodeFilter, 'category', 'is_available', 'is_featured']
    search_fields = ['name', 'description', 'color', 'gmt_code']
    inlines = [ProductImageInline, ProductWeightInline]
    list_editable = ['is_available', 'is_featured']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'gmt_code', 'category', 'description')
        }),
        ('Specifications', {
            'fields': ('weight_kg', 'color', 'length_mm', 'width_mm', 'thickness_mm')
        }),
        ('Pricing', {
            'fields': ('price',)
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
