from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Product, Category, ProductImage, MaterialType, Finish, Color


class AdminLoginForm(AuthenticationForm):
    """Custom admin login form."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


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
            'name', 'slug', 'category', 'material_type', 'finish', 'color',
            'length_mm', 'width_mm', 'thickness_mm', 'description', 'price',
            'is_available', 'is_featured', 'meta_title', 'meta_description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product Name'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank for auto-generation'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'material_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'finish': forms.Select(attrs={
                'class': 'form-control'
            }),
            'color': forms.Select(attrs={
                'class': 'form-control'
            }),
            'length_mm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Length in mm'
            }),
            'width_mm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Width in mm'
            }),
            'thickness_mm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Thickness in mm',
                'step': '0.01'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Product description'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price (optional)',
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


class MaterialTypeForm(forms.ModelForm):
    """Form for adding/editing material types."""
    
    class Meta:
        model = MaterialType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Material Type Name'
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


class ColorForm(forms.ModelForm):
    """Form for adding/editing colors."""
    
    class Meta:
        model = Color
        fields = ['name', 'hex_code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Color Name'
            }),
            'hex_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '#FFFFFF',
                'type': 'color'
            }),
        }


# Formset for multiple images
ProductImageFormSet = forms.inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=3,
    can_delete=True
)
