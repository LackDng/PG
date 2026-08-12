from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from core.decorators import login_required_custom


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "")
            # Chỉ cho phép redirect nội bộ, tránh open redirect
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect("dashboard")
        messages.error(request, "Tên đăng nhập hoặc mật khẩu không đúng.")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required_custom
def change_password_view(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password", "")
        new_password = request.POST.get("new_password", "").strip()
        confirm = request.POST.get("confirm_password", "").strip()

        if not request.user.check_password(old_password):
            messages.error(request, "Mật khẩu hiện tại không đúng.")
        elif len(new_password) < 6:
            messages.error(request, "Mật khẩu mới phải có ít nhất 6 ký tự.")
        elif new_password != confirm:
            messages.error(request, "Xác nhận mật khẩu không khớp.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            logout(request)
            messages.success(request, "Đổi mật khẩu thành công. Vui lòng đăng nhập lại.")
            return redirect("login")

    return render(request, "account/change_password.html")
