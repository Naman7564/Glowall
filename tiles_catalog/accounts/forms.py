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
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Email or Username',
            'id': 'login-username',
            'autocomplete': 'username',
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
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Email Address',
            'id': 'signup-email',
            'autocomplete': 'email',
        })
    )
    phone = forms.CharField(
        max_length=17,
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Phone Number (optional)',
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
        widget=forms.PasswordInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Confirm Password',
            'id': 'signup-password2',
            'autocomplete': 'new-password',
        })
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
        fields = ('first_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        name_parts = self.cleaned_data['first_name'].split(' ', 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        # Use email as username
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user
