from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Enter a valid phone number (e.g. +919876543210)."
)


class UserLoginForm(AuthenticationForm):
    """Custom login form with modern styling."""
    username = forms.CharField(
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Phone Number',
            'id': 'login-username',
            'autocomplete': 'tel',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Password',
            'id': 'login-password',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'auth-checkbox',
            'id': 'remember-me',
        })
    )


class UserSignupForm(UserCreationForm):
    """Custom signup form with modern styling."""
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Full Name',
            'id': 'signup-name',
            'autocomplete': 'name',
        })
    )
    phone = forms.CharField(
        max_length=17,
        required=True,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Phone Number',
            'id': 'signup-phone',
            'autocomplete': 'tel',
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Create Password',
            'id': 'signup-password1',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    agree_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Terms & Conditions.'},
        widget=forms.CheckboxInput(attrs={
            'class': 'auth-checkbox',
            'id': 'agree-terms',
        })
    )

    class Meta:
        model = User
        fields = ('first_name', 'phone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password validation errors for password2 since we don't use it
        if 'password2' in self.errors:
            del self.errors['password2']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError('An account with this phone number already exists.')
        return phone

    def clean_password2(self):
        """Override to skip password confirmation - just return password1."""
        return self.cleaned_data.get('password1')

    def _post_clean(self):
        """Override to skip Django's password validation - accept any password."""
        # Skip the parent's password validation by calling grandparent's _post_clean
        from django.contrib.auth.forms import BaseUserCreationForm
        BaseUserCreationForm._post_clean(self)

    def save(self, commit=True):
        user = super().save(commit=False)
        name_parts = self.cleaned_data['first_name'].split(' ', 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        # Use phone number as username for login
        user.username = self.cleaned_data['phone']
        if commit:
            user.save()
        return user
