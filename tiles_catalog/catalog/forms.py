from django import forms
from .models import Contact, Order


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


class OrderForm(forms.ModelForm):
    """Checkout form for direct product orders."""

    class Meta:
        model = Order
        fields = ['full_name', 'phone_number', 'email', 'address', 'city', 'state', 'pincode']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Full Name',
                'autocomplete': 'name',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Phone Number',
                'autocomplete': 'tel',
                'inputmode': 'tel',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Email Address',
                'autocomplete': 'email',
            }),
            'address': forms.Textarea(attrs={
                'class': 'checkout-input checkout-textarea',
                'placeholder': 'Street address, area, landmark',
                'rows': 4,
                'autocomplete': 'street-address',
            }),
            'city': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'City',
                'autocomplete': 'address-level2',
            }),
            'state': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'State',
                'autocomplete': 'address-level1',
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Pincode',
                'autocomplete': 'postal-code',
                'inputmode': 'numeric',
            }),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data['full_name'].strip()
        if len(full_name) < 3:
            raise forms.ValidationError('Enter the customer full name.')
        return full_name

    def clean_phone_number(self):
        phone_number = ''.join(ch for ch in self.cleaned_data['phone_number'] if ch.isdigit() or ch == '+')
        digits_only = ''.join(ch for ch in phone_number if ch.isdigit())
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise forms.ValidationError('Enter a valid phone number.')
        return phone_number

    def clean_pincode(self):
        pincode = ''.join(ch for ch in self.cleaned_data['pincode'] if ch.isdigit())
        if len(pincode) != 6:
            raise forms.ValidationError('Enter a valid 6-digit pincode.')
        return pincode
