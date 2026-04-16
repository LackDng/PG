from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """Decorator yêu cầu user có role trong danh sách."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.role not in roles and not request.user.is_superuser:
                messages.error(request, "Bạn không có quyền thực hiện thao tác này.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    return role_required("admin")(view_func)


def cashier_required(view_func):
    return role_required("admin", "cashier")(view_func)


def staff_required(view_func):
    return role_required("admin", "staff", "cashier")(view_func)


def accountant_required(view_func):
    return role_required("admin", "accountant")(view_func)


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper
