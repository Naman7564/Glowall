from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils import timezone
from PIL import Image, ImageOps


MARBLE_TEXTURE_CATEGORY_SLUGS = {'marbels', 'marble-texture'}
MARBLE_TEXTURE_WEIGHT_OPTIONS = (
    {'value_kg': Decimal('30'), 'price': None, 'kind': 'Dry'},
    {'value_kg': Decimal('25'), 'price': Decimal('1899'), 'kind': 'Wet'},
)


def is_marble_texture_category(category):
    if not category:
        return False

    slug = (getattr(category, 'slug', '') or '').strip().lower()
    name = (getattr(category, 'name', '') or '').strip().lower()
    return slug in MARBLE_TEXTURE_CATEGORY_SLUGS or name == 'marble texture'


class Category(models.Model):
    """Product categories for marble, granite, and natural stone."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    default_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        previous_default_price = None
        if self.pk:
            previous_default_price = (
                Category.objects
                .filter(pk=self.pk)
                .values_list('default_price', flat=True)
                .first()
            )

        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

        if previous_default_price != self.default_price and self.default_price is not None:
            self.products.filter(is_available=True).update(
                price=self.default_price,
                updated_at=timezone.now(),
            )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category_detail', kwargs={'slug': self.slug})

    @property
    def product_count(self):
        return self.products.filter(is_available=True).count()


class ProductWeight(models.Model):
    """One or more weight variants for a product (e.g. 12 kg, 16 kg)."""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='weights')
    value_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Weight in kilograms'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Price for this weight option (optional)'
    )
    order = models.PositiveIntegerField(default=0, help_text='Display order (lower first)')

    class Meta:
        ordering = ['order', 'value_kg']

    def __str__(self):
        display = format(self.value_kg, 'f').rstrip('0').rstrip('.')
        if self.price is not None:
            price_text = format(self.price, 'f').rstrip('0').rstrip('.')
            return f'{display} kg — ₹{price_text}'
        return f'{display} kg'

    @property
    def compact_value_display(self):
        return f"{format(self.value_kg, 'f').rstrip('0').rstrip('.')}kg"

    @property
    def marble_texture_kind(self):
        product = getattr(self, 'product', None)
        if not product or not product.is_marble_texture:
            return ''

        weight_value = Decimal(str(self.value_kg))
        for option in MARBLE_TEXTURE_WEIGHT_OPTIONS:
            if weight_value == option['value_kg']:
                return option['kind']
        return ''

    @property
    def display_label(self):
        if self.marble_texture_kind:
            return f'{self.compact_value_display} ({self.marble_texture_kind})'
        display = format(self.value_kg, 'f').rstrip('0').rstrip('.')
        return f'{display} kg'

    @property
    def button_label(self):
        if self.marble_texture_kind:
            return f'{self.compact_value_display} {self.marble_texture_kind}'
        return self.display_label


class Product(models.Model):
    """Main product model for tiles and marble."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    code = models.PositiveIntegerField(unique=True, blank=True, null=True, help_text='Product code (101-400)')
    gmt_code = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text='GMT code used to group and filter products',
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    color = models.CharField(max_length=100, blank=True, help_text='Enter a color name manually')
    
    # Size specifications
    weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Weight in kilograms'
    )
    length_mm = models.PositiveIntegerField(blank=True, null=True, help_text='Length in millimeters')
    width_mm = models.PositiveIntegerField(blank=True, null=True, help_text='Width in millimeters')
    thickness_mm = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Thickness in millimeters')
    
    # Product details
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
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
        ordering = ['gmt_code', 'name']

    def save(self, *args, **kwargs):
        if self.price is None and self.category_id:
            used_category_default_price = False
            category_default_price = (
                getattr(self.category, 'default_price', None)
                if hasattr(self, 'category')
                else None
            )
            if category_default_price is None:
                category_default_price = (
                    Category.objects
                    .filter(pk=self.category_id)
                    .values_list('default_price', flat=True)
                    .first()
                )
            if category_default_price is not None:
                self.price = category_default_price
                used_category_default_price = True

            if used_category_default_price and kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'price'}

        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'identifier': self.slug})

    @property
    def configured_price(self):
        if self.price is not None:
            return self.price

        category = getattr(self, 'category', None)
        if category and category.default_price is not None:
            return category.default_price

        if self.category_id:
            return (
                Category.objects
                .filter(pk=self.category_id)
                .values_list('default_price', flat=True)
                .first()
            )

        return None

    def resolve_unit_price(self, weight=None, use_weight_price=False):
        if use_weight_price and weight and weight.price is not None:
            return weight.price
        return self.configured_price

    @property
    def is_marble_texture(self):
        return is_marble_texture_category(self.category)

    def sync_marble_texture_weight_pricing(self):
        if not self.pk or not self.is_marble_texture:
            return

        existing_weights = {
            Decimal(str(weight.value_kg)): weight
            for weight in self.weights.all()
        }

        for order, option in enumerate(MARBLE_TEXTURE_WEIGHT_OPTIONS):
            weight = existing_weights.get(option['value_kg'])
            if weight is None:
                self.weights.create(
                    value_kg=option['value_kg'],
                    price=option['price'],
                    order=order,
                )
                continue

            update_fields = []
            if weight.price != option['price']:
                weight.price = option['price']
                update_fields.append('price')
            if weight.order != order:
                weight.order = order
                update_fields.append('order')
            if update_fields:
                weight.save(update_fields=update_fields)

    @property
    def storefront_weight_options(self):
        weight_entries = list(self.weights.all())
        if not self.is_marble_texture:
            return weight_entries

        weight_map = {
            Decimal(str(weight.value_kg)): weight
            for weight in weight_entries
        }
        marble_weights = []
        for option in MARBLE_TEXTURE_WEIGHT_OPTIONS:
            weight = weight_map.get(option['value_kg'])
            if weight is None:
                return weight_entries
            marble_weights.append(weight)
        return marble_weights

    @property
    def default_storefront_weight(self):
        weight_options = self.storefront_weight_options
        return weight_options[0] if weight_options else None

    @property
    def size_display(self):
        if self.length_mm and self.width_mm:
            return f'{self.length_mm}x{self.width_mm} mm'
        return ''

    @property
    def weight_display(self):
        """Returns a human-friendly weight string from ProductWeight entries,
        falling back to the legacy weight_kg field."""
        try:
            weight_entries = list(self.storefront_weight_options)
        except Exception:
            weight_entries = []

        if weight_entries:
            if self.is_marble_texture:
                return ' / '.join(weight.display_label for weight in weight_entries)

            parts = []
            for w in weight_entries:
                val = format(w.value_kg, 'f').rstrip('0').rstrip('.')
                if w.price is not None:
                    price_text = format(w.price, 'f').rstrip('0').rstrip('.')
                    parts.append(f'{val} kg \u2014 \u20b9{price_text}')
                else:
                    parts.append(f'{val} kg')
            return ' / '.join(parts)

        # Fallback to legacy field
        if self.weight_kg is None:
            return ''
        weight_text = format(self.weight_kg, 'f').rstrip('0').rstrip('.')
        return f'{weight_text} kg'

    @property
    def specification_display(self):
        if self.weight_display:
            return self.weight_display
        return self.size_display

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
    full_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField(max_length=10)
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
        return f'Order #{self.pk} by {self.full_name}'

    @cached_property
    def line_items(self):
        """Materialize order items once so legacy template access stays cheap."""
        return list(self.items.all())

    @property
    def primary_item(self):
        return self.line_items[0] if self.line_items else None

    @property
    def product(self):
        item = self.primary_item
        return item.product if item else None

    @property
    def quantity(self):
        return sum(item.quantity for item in self.line_items)

    @property
    def unit_price(self):
        item = self.primary_item
        return item.unit_price if item else None

    @property
    def product_summary(self):
        if not self.line_items:
            return ''
        if len(self.line_items) == 1:
            return self.line_items[0].product.name
        return f'{self.line_items[0].product.name} +{len(self.line_items) - 1} more'


class OrderItem(models.Model):
    """Items within an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    weight = models.ForeignKey(ProductWeight, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'{self.quantity}x {self.product.name} (Order {self.order.pk})'


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


class Poster(models.Model):
    """Homepage poster/banner for hero section showcase."""

    title = models.CharField(max_length=100, blank=True)
    subtitle = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to='posters/')
    link_url = models.URLField(blank=True, help_text='Optional link when clicked')
    order = models.PositiveIntegerField(default=0, help_text='Display order (lower first)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title or f'Poster #{self.pk or "new"}'
