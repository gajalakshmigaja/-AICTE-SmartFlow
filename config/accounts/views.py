from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import UserProfile
from .forms import InstitutionRegistrationForm, UserProfileUpdateForm


def get_role_redirect_url(user):
    """Determine where user lands after logging in."""
    if user.is_superuser:
        return 'dashboard'

    profile = getattr(user, 'profile', None)
    if not profile:
        return 'dashboard'

    if profile.role == 'OFFICER':
        return 'officer_dashboard'
    elif profile.role == 'DIRECTOR':
        return 'director_dashboard'
    elif profile.role == 'ADMIN':
        return 'director_dashboard'
    else:
        return 'dashboard'


def custom_login(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect_url(request.user))

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')

            from audit.services import log_activity
            log_activity(
                actor=user,
                action='LOGIN',
                target_model='User',
                target_id=str(user.id),
                summary=f'User {user.username} logged in successfully',
                request=request
            )

            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect(get_role_redirect_url(user))
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def register_institution(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect_url(request.user))

    if request.method == 'POST':
        form = InstitutionRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()

                profile = getattr(user, 'profile', None)
                if not profile:
                    profile = UserProfile.objects.create(user=user)

                profile.role = 'INSTITUTION'
                profile.phone = form.cleaned_data.get('contact_phone', '')
                profile.regional_office = form.cleaned_data.get('regional_office', 'HQ')
                profile.save()

                from institutions.models import Institution
                Institution.objects.create(
                    user=user,
                    name=form.cleaned_data['institution_name'],
                    contact_email=user.email,
                    contact_phone=profile.phone,
                )

            login(request, user)
            messages.success(request, 'Registration successful! Welcome to the AICTE SmartFlow Portal.')
            return redirect('dashboard')
    else:
        form = InstitutionRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            form.save()
            messages.success(request, 'Profile details updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileUpdateForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'form': form,
    })


@require_POST
def custom_logout(request):
    if request.user.is_authenticated:
        from audit.services import log_activity
        log_activity(
            actor=request.user,
            action='LOGOUT',
            target_model='User',
            target_id=str(request.user.id),
            summary=f'User {request.user.username} logged out',
            request=request
        )
        logout(request)
        messages.info(request, 'You have been safely logged out.')
    return redirect('login')
