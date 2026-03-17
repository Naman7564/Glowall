from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from PIL import Image, ImageOps


class Category(models.Model):
    """Product categories for tiles, marble, granite, etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category_detail', kwargs={'slug': self.slug})

    @property
    def product_count(self):
        return self.products.filter(is_available=True).count()


class MaterialType(models.Model):
    """Material types: Tile, Marble, Granite, Stone, etc."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Finish(models.Model):
    """Finish types: Glossy, Matte, Polish, etc."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        verbose_name_plural = 'Finishes'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Main product model for tiles and marble."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    material_type = models.ForeignKey(MaterialType, on_delete=models.SET_NULL, null=True, related_name='products')
    finish = models.ForeignKey(Finish, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    color = models.CharField(max_length=100, blank=True, help_text='Enter a color name manually')
    
    # Size specifications
    length_mm = models.PositiveIntegerField(help_text='Length in millimeters')
    width_mm = models.PositiveIntegerField(help_text='Width in millimeters')
    thickness_mm = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Thickness in millimeters')
    
    # Product details
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    sku = models.CharField(max_length=50, blank=True, unique=True, help_text='Stock Keeping Unit')
    
    # Status
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text='Show on homepage')
    
    # SEO fields
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        if not self.sku:
            # Generate SKU from category and material
            prefix = self.category.slug[:3].upper() if self.category else 'PRD'
            import random
            self.sku = f'{prefix}-{random.randint(10000, 99999)}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})

    @property
    def size_display(self):
        return f'{self.length_mm}x{self.width_mm} mm'

    @property
    def primary_image(self):
        """Get the primary image for the product."""
        image = self.images.filter(is_primary=True).first()
        if not image:
            image = self.images.first()
        return image

    @property
    def all_images(self):
        return self.images.all()


class ProductImage(models.Model):
    """Multiple images for a product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-is_primary', 'created_at']

    def __str__(self):
        return f'{self.product.name} - Image {self.order + 1}'

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Ensure only one primary image per product
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class Contact(models.Model):
    """Contact form submissions."""
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.subject}'


class Order(models.Model):
    """Direct checkout orders submitted from the storefront."""

    STATUS_NEW = 'new'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAYMENT_PENDING = 'PENDING'
    PAYMENT_SUCCESS = 'SUCCESS'
    PAYMENT_FAILED = 'FAILED'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_SUCCESS, 'Success'),
        (PAYMENT_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='orders',
        null=True,
        blank=True,
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='orders')
    full_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING,
        db_index=True,
    )
    cashfree_order_id = models.CharField(max_length=45, unique=True, blank=True)
    cashfree_cf_order_id = models.CharField(max_length=120, blank=True)
    cashfree_payment_session_id = models.CharField(max_length=255, blank=True)
    cashfree_payment_id = models.CharField(max_length=120, blank=True)
    payment_message = models.TextField(blank=True)
    payment_completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk or "new"} - {self.product.name}'


class CustomerReview(models.Model):
    """Customer review images and optional attribution for the homepage."""

    customer_name = models.CharField(max_length=120, blank=True)
    customer_location = models.CharField(max_length=120, blank=True)
    review_text = models.TextField(blank=True)
    review_image = models.ImageField(upload_to='reviews/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.customer_name:
            return self.customer_name
        return f'Review #{self.pk or "new"}'

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        should_optimize = update_fields is None or 'review_image' in update_fields
        super().save(*args, **kwargs)
        if should_optimize:
            self._optimize_review_image()

    def _optimize_review_image(self):
        if not self.review_image:
            return

        image_path = getattr(self.review_image, 'path', None)
        if not image_path:
            return

        with Image.open(image_path) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1600, 1600))

            image_format = (img.format or '').upper()
            save_kwargs = {'optimize': True}

            if image_format in {'JPEG', 'JPG'}:
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                save_kwargs['quality'] = 85
                save_format = 'JPEG'
            elif image_format == 'WEBP':
                if img.mode not in ('RGB', 'RGBA', 'L'):
                    img = img.convert('RGB')
                save_kwargs['quality'] = 85
                save_format = 'WEBP'
            elif image_format == 'PNG':
                save_format = 'PNG'
            else:
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                save_kwargs['quality'] = 85
                save_format = 'JPEG'

            img.save(image_path, format=save_format, **save_kwargs)
