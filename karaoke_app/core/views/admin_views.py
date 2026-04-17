from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from core.models import Room, ServiceType, MenuItem, MenuCategory, User, Config
from core.decorators import admin_required, login_required_custom


# ─── Quản lý phòng ───────────────────────────────────────────────────────────

@admin_required
def manage_rooms(request):
    rooms = Room.objects.all().order_by("sort_order", "name")
    return render(request, "admin_panel/rooms.html", {"rooms": rooms})


@admin_required
def add_room(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        sort_order = int(request.POST.get("sort_order", 0) or 0)
        if not name:
            messages.error(request, "Tên phòng không được để trống.")
        elif Room.objects.filter(name=name).exists():
            messages.error(request, f"Phòng '{name}' đã tồn tại.")
        else:
            Room.objects.create(name=name, sort_order=sort_order)
            messages.success(request, f"Đã thêm phòng '{name}'.")
    return redirect("manage_rooms")


@admin_required
def edit_room(request, room_id):
    room = get_object_or_404(Room, pk=room_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        sort_order = int(request.POST.get("sort_order", 0) or 0)
        is_active = request.POST.get("is_active") == "1"
        if name:
            room.name = name
            room.sort_order = sort_order
            room.is_active = is_active
            room.save()
            messages.success(request, f"Đã cập nhật phòng '{name}'.")
    return redirect("manage_rooms")


# ─── Quản lý dịch vụ mic ─────────────────────────────────────────────────────

@admin_required
def manage_services(request):
    services = ServiceType.objects.all().order_by("sort_order", "name")
    return render(request, "admin_panel/services.html", {"services": services})


@admin_required
def add_service(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        base_price = int(request.POST.get("base_price", 500000) or 500000)
        sort_order = int(request.POST.get("sort_order", 0) or 0)
        if not name:
            messages.error(request, "Tên dịch vụ không được để trống.")
        else:
            ServiceType.objects.create(name=name, base_price=base_price, sort_order=sort_order)
            messages.success(request, f"Đã thêm dịch vụ '{name}'.")
    return redirect("manage_services")


@admin_required
def edit_service(request, service_id):
    service = get_object_or_404(ServiceType, pk=service_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        base_price = int(request.POST.get("base_price", 500000) or 500000)
        sort_order = int(request.POST.get("sort_order", 0) or 0)
        is_active = request.POST.get("is_active") == "1"
        if name:
            service.name = name
            service.base_price = base_price
            service.sort_order = sort_order
            service.is_active = is_active
            service.save()
            messages.success(request, f"Đã cập nhật dịch vụ '{name}'.")
    return redirect("manage_services")


# ─── Quản lý menu ────────────────────────────────────────────────────────────

@admin_required
def manage_menu(request):
    categories = MenuCategory.objects.prefetch_related("items").order_by("sort_order", "name")
    all_items = MenuItem.objects.select_related("category").order_by("category__sort_order", "sort_order", "name")
    return render(request, "admin_panel/menu.html", {
        "categories": categories,
        "all_items": all_items,
    })


@admin_required
def add_category(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        sort_order = int(request.POST.get("sort_order", 0) or 0)
        if name:
            MenuCategory.objects.create(name=name, sort_order=sort_order)
            messages.success(request, f"Đã thêm danh mục '{name}'.")
        else:
            messages.error(request, "Tên danh mục không được để trống.")
    return redirect("manage_menu")


@admin_required
def add_menu_item_admin(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        price = int(request.POST.get("price", 0) or 0)
        category_id = request.POST.get("category_id")
        sort_order = int(request.POST.get("sort_order", 0) or 0)
        if not name or price <= 0:
            messages.error(request, "Vui lòng nhập đầy đủ tên và giá hợp lệ.")
        else:
            category = MenuCategory.objects.filter(pk=category_id).first() if category_id else None
            MenuItem.objects.create(name=name, price=price, category=category, sort_order=sort_order)
            messages.success(request, f"Đã thêm món '{name}'.")
    return redirect("manage_menu")


@admin_required
def edit_menu_item(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        price = int(request.POST.get("price", 0) or 0)
        category_id = request.POST.get("category_id")
        sort_order = int(request.POST.get("sort_order", 0) or 0)
        is_active = request.POST.get("is_active") == "1"
        if name and price > 0:
            item.name = name
            item.price = price
            item.category = MenuCategory.objects.filter(pk=category_id).first() if category_id else None
            item.sort_order = sort_order
            item.is_active = is_active
            item.save()
            messages.success(request, f"Đã cập nhật món '{name}'.")
    return redirect("manage_menu")


# ─── Quản lý nhân viên ───────────────────────────────────────────────────────

@admin_required
def manage_users(request):
    users = User.objects.all().order_by("role", "username")
    return render(request, "admin_panel/users.html", {"users": users})


@admin_required
def add_user(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        display_name = request.POST.get("display_name", "").strip()
        password = request.POST.get("password", "")
        role = request.POST.get("role", "staff")

        if not username or not password:
            messages.error(request, "Vui lòng nhập đầy đủ thông tin.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"Tên đăng nhập '{username}' đã tồn tại.")
        else:
            User.objects.create(
                username=username,
                display_name=display_name,
                password=make_password(password),
                role=role,
            )
            messages.success(request, f"Đã tạo tài khoản '{username}'.")
    return redirect("manage_users")


@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        display_name = request.POST.get("display_name", "").strip()
        role = request.POST.get("role", user.role)
        new_password = request.POST.get("password", "").strip()
        is_active = request.POST.get("is_active") == "1"

        user.display_name = display_name
        user.role = role
        user.is_active = is_active
        if new_password:
            user.password = make_password(new_password)
        user.save()
        messages.success(request, f"Đã cập nhật tài khoản '{user.username}'.")
    return redirect("manage_users")


# ─── Cấu hình hệ thống ───────────────────────────────────────────────────────

@admin_required
def system_config(request):
    configs = {
        "printer_ip": Config.get("printer_ip", ""),
        "printer_port": Config.get("printer_port", "9100"),
        "shop_name": Config.get("shop_name", "KARAOKE"),
        "bank_id": Config.get("bank_id", ""),
        "bank_account": Config.get("bank_account", ""),
        "account_holder": Config.get("account_holder", ""),
    }

    if request.method == "POST":
        Config.set("printer_ip", request.POST.get("printer_ip", "").strip())
        Config.set("printer_port", request.POST.get("printer_port", "9100").strip())
        Config.set("shop_name", request.POST.get("shop_name", "KARAOKE").strip())
        Config.set("bank_id", request.POST.get("bank_id", "").strip())
        Config.set("bank_account", request.POST.get("bank_account", "").strip())
        Config.set("account_holder", request.POST.get("account_holder", "").strip())
        messages.success(request, "Đã lưu cấu hình.")
        return redirect("system_config")

    return render(request, "admin_panel/config.html", {"configs": configs})
