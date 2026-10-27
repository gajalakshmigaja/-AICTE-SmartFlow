from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def role_required(allowed_roles):
    """
    Decorator to restrict view access to specific UserProfile roles.
    Admins / superusers always have access.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, 'profile', None)
            if not profile:
                messages.error(request, 'User profile not found. Please contact administrator.')
                return redirect('dashboard')

            if profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, f'Access denied: You need one of the following roles: {", ".join(allowed_roles)}')
            return redirect('dashboard')
        return _wrapped_view
    return decorator


def institution_required(view_func):
    return role_required(['INSTITUTION'])(view_func)


def scrutiny_officer_required(view_func):
    return role_required(['OFFICER', 'ADMIN'])(view_func)


def regional_director_required(view_func):
    return role_required(['DIRECTOR', 'ADMIN'])(view_func)


def admin_required(view_func):
    return role_required(['ADMIN'])(view_func)
