from django import forms
from django.forms import inlineformset_factory
from catalog.models import Product, Category, ProductImage, ProductWeight, Finish, CustomerReview, Order, Poster


class CategoryForm(forms.ModelForm):
    """Form for adding/editing categories."""
    
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'image', 'is_active']
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
        }


class ProductForm(forms.ModelForm):
    """Form for adding/editing products."""
    
    class Meta:
        model = Product
        fields = [
            'name', 'gmt_code', 'category', 'weight_kg', 'color',
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
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. White, Beige Marble, Dark Grey'
            }),
            'weight_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Weight in kg',
                'step': '0.01',
                'min': '0'
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
        fields = ['image', 'alt_text', 'is_primary', 'order']
        widgets = {
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alt text for image'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '0'
            }),
        }


class FinishForm(forms.ModelForm):
    """Form for adding/editing finishes."""
    
    class Meta:
        model = Finish
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Finish Name'
            }),
        }


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
