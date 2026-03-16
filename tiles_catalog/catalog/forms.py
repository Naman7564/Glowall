from django import forms
from .models import Contact


class ContactForm(forms.ModelForm):
    """Contact form for customer inquiries."""
    
    class Meta:
        model = Contact
        fields = ['name', 'phone', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Name',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Phone Number'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Your Message',
                'rows': 5,
                'required': True
            }),
        }


class ProductSearchForm(forms.Form):
    """Product search form."""
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...'
        })
    )
    category = forms.CharField(required=False)
    material = forms.CharField(required=False)
    finish = forms.CharField(required=False)
    color = forms.CharField(required=False)
