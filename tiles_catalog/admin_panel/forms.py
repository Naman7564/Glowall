from django import forms
from django.forms import inlineformset_factory
from catalog.models import Product, Category, ProductImage, ProductWeight, CustomerReview, Order, Poster, Discount


class CategoryForm(forms.ModelForm):
    """Form for adding/editing categories."""
    
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'default_price', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category Name'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank for auto-generation'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Category description'
            }),
            'default_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Default price in INR',
                'step': '0.01',
                'min': '0',
            }),
        }


class ProductForm(forms.ModelForm):
    """Form for adding/editing products."""
    
    class Meta:
        model = Product
        fields = [
            'name', 'gmt_code', 'category',
            'description', 'price', 'is_available', 'is_featured',
            'meta_title', 'meta_description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product Name'
            }),
            'gmt_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter GMT code for product filtering'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Product description'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price in INR (optional)',
                'step': '0.01'
            }),
            'meta_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO Title (optional)'
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'SEO Description (optional)'
            }),
        }


class ProductImageForm(forms.ModelForm):
    """Form for adding product images."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].widget.attrs.update({
            'accept': 'image/*'
        })
    
    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary', 'order']
        widgets = {
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '0'
            }),
        }


class DiscountForm(forms.ModelForm):
    """Form for creating and editing coupon discounts."""

    class Meta:
        model = Discount
        fields = [
            'name', 'code', 'discount_type', 'value', 'is_active',
            'expiry_date', 'usage_limit', 'minimum_order_amount',
            'applies_to', 'products', 'categories',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Festive sale, Marble offer, etc.',
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'GLOW10',
            }),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '10 or 500',
                'step': '0.01',
                'min': '0',
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'usage_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank for unlimited',
                'min': '1',
            }),
            'minimum_order_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'applies_to': forms.Select(attrs={'class': 'form-control'}),
            'products': forms.SelectMultiple(attrs={
                'class': 'form-control discount-multi-select',
                'size': 8,
            }),
            'categories': forms.SelectMultiple(attrs={
                'class': 'form-control discount-multi-select',
                'size': 8,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['products'].queryset = Product.objects.select_related('category').order_by('name')
        self.fields['categories'].queryset = Category.objects.order_by('name')

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        value = cleaned_data.get('value')
        applies_to = cleaned_data.get('applies_to')
        products = cleaned_data.get('products')
        categories = cleaned_data.get('categories')

        if value is not None and value <= 0:
            self.add_error('value', 'Enter a discount value greater than zero.')
        if discount_type == Discount.TYPE_PERCENTAGE and value is not None and value > 100:
            self.add_error('value', 'Percentage discounts cannot be more than 100.')
        if applies_to == Discount.APPLY_PRODUCTS and not products:
            self.add_error('products', 'Select at least one product for this discount.')
        if applies_to == Discount.APPLY_CATEGORIES and not categories:
            self.add_error('categories', 'Select at least one category for this discount.')
        return cleaned_data


class CustomerReviewForm(forms.ModelForm):
    """Form for adding/editing customer reviews."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['review_image'].widget.attrs.update({
            'accept': 'image/*',
            'class': 'file-upload-input',
        })

    class Meta:
        model = CustomerReview
        fields = [
            'customer_name', 'customer_location', 'review_text',
            'review_image', 'is_active'
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer name'
            }),
            'customer_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City, State or Country'
            }),
            'review_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Short review text (optional)'
            }),
        }
class OrderStatusForm(forms.ModelForm):
    """Form for updating order status."""

    class Meta:
        model = Order
        fields = ['status', 'payment_status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'payment_status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }


class PosterForm(forms.ModelForm):
    """Form for adding/editing homepage posters."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].widget.attrs.update({
            'accept': 'image/*',
            'class': 'file-upload-input',
        })

    class Meta:
        model = Poster
        fields = ['title', 'subtitle', 'image', 'link_url', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Poster title (optional)'
            }),
            'subtitle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Poster subtitle (optional)'
            }),
            'link_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com (optional)'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '0'
            }),
        }


# Formset for multiple images
ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=0,
    max_num=12,
    validate_max=True,
    can_delete=True
)


class ProductWeightForm(forms.ModelForm):
    """Form for a single weight option entry."""

    class Meta:
        model = ProductWeight
        fields = ['value_kg', 'price', 'order']
        widgets = {
            'value_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Weight in kg',
                'step': '0.01',
                'min': '0',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price in ₹ (optional)',
                'step': '0.01',
                'min': '0',
            }),
            'order': forms.HiddenInput(),
        }


# Formset for multiple weight entries
ProductWeightFormSet = inlineformset_factory(
    Product,
    ProductWeight,
    form=ProductWeightForm,
    extra=0,
    can_delete=True,
)
