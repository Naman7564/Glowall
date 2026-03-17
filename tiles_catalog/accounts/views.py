from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import UserLoginForm, UserSignupForm


def _get_safe_redirect(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


def user_login(request):
    """User login view with modern UI."""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            remember_me = form.cleaned_data.get('remember_me', False)
            login(request, user)
            if not remember_me:
                request.session.set_expiry(0)  # Session expires on browser close
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(_get_safe_redirect(request) or 'catalog:home')
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def user_signup(request):
    """User signup view with modern UI."""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Glowall, {user.first_name}! Your account has been created.')
            return redirect('catalog:home')
    else:
        form = UserSignupForm()

    return render(request, 'accounts/signup.html', {'form': form})


@require_POST
def user_logout(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('catalog:home')
