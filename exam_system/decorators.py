from django.shortcuts import redirect
from django.contrib import messages
from .models import Profile
from django.http import JsonResponse


def role_required(role):
    """
    Reusable decorator for role-based access control.
    Usage: @role_required('instructor') or @role_required('student')
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Profile not found.'}, status=403)
                messages.error(request, "Profile not found.")
                return redirect('login')

            if profile.role != role:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': f'Access denied: {role.capitalize()} only.'}, status=403)
                messages.error(request, f"Access denied: {role.capitalize()} only.")
                return redirect('home')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def instructor_required(view_func):
    """Decorator to restrict access to instructors only."""
    return role_required('instructor')(view_func)


def student_required(view_func):
    """Decorator to restrict access to students only."""
    return role_required('student')(view_func)