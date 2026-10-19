from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMIN = "admin"
RECEPTION = "reception"
CLEANING = "cleaning"


def allowed(user, *roles):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or user.role in roles))


def roles_required(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not allowed(request.user, *roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
