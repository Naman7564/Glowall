from django import forms
from .models import Order


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
    color = forms.CharField(required=False)


class OrderForm(forms.ModelForm):
    """Checkout form for direct product orders."""

    REQUIRED_FIELDS = ('full_name', 'phone_number', 'email', 'address', 'city', 'state', 'pincode')

    class Meta:
        model = Order
        fields = ['full_name', 'phone_number', 'email', 'address', 'city', 'state', 'pincode']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Full Name',
                'autocomplete': 'name',
                'required': True,
                'minlength': 3,
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Phone Number',
                'autocomplete': 'tel',
                'inputmode': 'tel',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Email Address',
                'autocomplete': 'email',
                'required': True,
            }),
            'address': forms.Textarea(attrs={
                'class': 'checkout-input checkout-textarea',
                'placeholder': 'Street address, area, landmark',
                'rows': 4,
                'autocomplete': 'street-address',
                'required': True,
            }),
            'city': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'City',
                'autocomplete': 'address-level2',
                'required': True,
            }),
            'state': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'State',
                'autocomplete': 'address-level1',
                'required': True,
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'checkout-input',
                'placeholder': 'Pincode',
                'autocomplete': 'postal-code',
                'inputmode': 'numeric',
                'required': True,
                'pattern': '[0-9]{6}',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.REQUIRED_FIELDS:
            self.fields[field_name].required = True
            self.fields[field_name].widget.attrs['required'] = True

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self.REQUIRED_FIELDS:
            value = cleaned_data.get(field_name)
            if isinstance(value, str):
                cleaned_data[field_name] = value.strip()
        return cleaned_data

    def clean_full_name(self):
        full_name = self.cleaned_data['full_name'].strip()
        if len(full_name) < 3:
            raise forms.ValidationError('Enter the customer full name.')
        return full_name

    def clean_address(self):
        address = self.cleaned_data['address'].strip()
        if len(address) < 10:
            raise forms.ValidationError('Enter a complete delivery address.')
        return address

    def clean_city(self):
        city = self.cleaned_data['city'].strip()
        if len(city) < 2:
            raise forms.ValidationError('Enter a valid city.')
        return city

    def clean_state(self):
        state = self.cleaned_data['state'].strip()
        if len(state) < 2:
            raise forms.ValidationError('Enter a valid state.')
        return state

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
