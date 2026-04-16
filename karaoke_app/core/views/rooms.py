from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from core.models import Room, RoomSession, ServiceOrder, OrderItem, ServiceType, MenuItem, MenuCategory
from core.decorators import login_required_custom, staff_required
from core.pricing import calculate_session_total, get_cost_breakdown


@login_required_custom
def dashboard(request):
    rooms = Room.objects.filter(is_active=True)
    room_data = []
    for room in rooms:
        session = room.get_active_session()
        room_data.append({
            "room": room,
            "session": session,
        })

    # Sessions đang mở (để gộp bàn)
    open_sessions = RoomSession.objects.filter(status="open", merged_into__isnull=True)

    return render(request, "rooms/dashboard.html", {
        "room_data": room_data,
        "open_sessions": open_sessions,
    })


@login_required_custom
def room_detail(request, room_id):
    room = get_object_or_404(Room, pk=room_id, is_active=True)
    session = room.get_active_session()

    if not session:
        return redirect("dashboard")

    # Resolve merged sessions
    merged_sessions = session.merged_sessions.all()

    # Service orders
    service_orders = session.get_all_service_orders().order_by("started_at")

    # Order items
    order_items_menu = session.get_all_order_items().filter(item_type="menu")
    order_items_outside = session.get_all_order_items().filter(item_type="outside")

    # Tạm tính
    totals = calculate_session_total(session)

    # Dịch vụ có thể gọi thêm
    service_types = ServiceType.objects.filter(is_active=True)

    # Menu đồ ăn/uống
    categories = MenuCategory.objects.prefetch_related("items").all()
    menu_items = MenuItem.objects.filter(is_active=True).order_by("category__sort_order", "sort_order", "name")

    # Breakdown từng dịch vụ mic
    now = timezone.now()
    service_breakdowns = []
    for so in service_orders:
        end = so.ended_at or now
        bd = get_cost_breakdown(so.started_at, end, so.base_price)
        bd["order"] = so
        service_breakdowns.append(bd)

    return render(request, "rooms/room_detail.html", {
        "room": room,
        "session": session,
        "merged_sessions": merged_sessions,
        "service_orders": service_orders,
        "service_breakdowns": service_breakdowns,
        "order_items_menu": order_items_menu,
        "order_items_outside": order_items_outside,
        "totals": totals,
        "service_types": service_types,
        "categories": categories,
        "menu_items": menu_items,
        "now": now,
    })


@staff_required
def open_room(request, room_id):
    room = get_object_or_404(Room, pk=room_id, is_active=True)

    if room.status != Room.STATUS_AVAILABLE:
        messages.error(request, f"Phòng {room.name} không ở trạng thái trống.")
        return redirect("dashboard")

    session = RoomSession.objects.create(room=room, opened_by=request.user)
    room.status = Room.STATUS_OCCUPIED
    room.save()

    messages.success(request, f"Đã mở phòng {room.name}.")
    return redirect("room_detail", room_id=room.id)


@staff_required
def set_room_cleaning(request, room_id):
    room = get_object_or_404(Room, pk=room_id, is_active=True)

    if room.status not in (Room.STATUS_AVAILABLE,):
        messages.error(request, "Chỉ phòng trống mới có thể chuyển sang trạng thái dọn.")
        return redirect("dashboard")

    room.status = Room.STATUS_CLEANING
    room.save()
    messages.success(request, f"Phòng {room.name} đang dọn dẹp.")
    return redirect("dashboard")


@staff_required
def set_room_available(request, room_id):
    room = get_object_or_404(Room, pk=room_id, is_active=True)

    if room.status != Room.STATUS_CLEANING:
        messages.error(request, "Chỉ phòng đang dọn mới có thể chuyển sang trống.")
        return redirect("dashboard")

    room.status = Room.STATUS_AVAILABLE
    room.save()
    messages.success(request, f"Phòng {room.name} đã sẵn sàng.")
    return redirect("dashboard")


@login_required_custom
def api_room_status(request, room_id):
    """API endpoint để frontend cập nhật giá tạm tính real-time."""
    room = get_object_or_404(Room, pk=room_id)
    session = room.get_active_session()
    if not session:
        return JsonResponse({"error": "Không có session đang mở."}, status=404)

    totals = calculate_session_total(session)
    now = timezone.now()

    service_data = []
    for so in session.get_all_service_orders():
        end = so.ended_at or now
        bd = get_cost_breakdown(so.started_at, end, so.base_price)
        elapsed_sec = int((end - so.started_at).total_seconds())
        service_data.append({
            "id": so.id,
            "name": so.service_name,
            "elapsed_seconds": elapsed_sec,
            "started_at_iso": so.started_at.isoformat(),
            "cost": bd["total"],
            "status": so.status,
            "overtime_status": bd["status"],
        })

    return JsonResponse({
        "total_service": totals["total_service"],
        "total_food": totals["total_food"],
        "total_outside": totals["total_outside"],
        "subtotal": totals["subtotal"],
        "services": service_data,
    })


@staff_required
def add_service_order(request, session_id):
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    if request.method == "POST":
        service_type_id = request.POST.get("service_type_id")
        service_type = get_object_or_404(ServiceType, pk=service_type_id, is_active=True)

        ServiceOrder.objects.create(
            session=session,
            service_type=service_type,
            service_name=service_type.name,
            base_price=service_type.base_price,
            started_by=request.user,
        )
        messages.success(request, f"Đã thêm {service_type.name}.")

    return redirect("room_detail", room_id=session.room_id)


@staff_required
def stop_service_order(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, status="running")
    order.status = ServiceOrder.STATUS_STOPPED
    order.ended_at = timezone.now()
    order.save()
    messages.success(request, f"Đã dừng {order.service_name}.")
    return redirect("room_detail", room_id=order.session.room_id)


@staff_required
def add_menu_item(request, session_id):
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    if request.method == "POST":
        menu_item_id = request.POST.get("menu_item_id")
        quantity = int(request.POST.get("quantity", 1))

        menu_item = get_object_or_404(MenuItem, pk=menu_item_id, is_active=True)

        OrderItem.objects.create(
            session=session,
            item_type=OrderItem.TYPE_MENU,
            menu_item=menu_item,
            name=menu_item.name,
            quantity=quantity,
            unit_price=menu_item.price,
            created_by=request.user,
        )
        messages.success(request, f"Đã thêm {quantity}x {menu_item.name}.")

    return redirect("room_detail", room_id=session.room_id)


@staff_required
def add_outside_item(request, session_id):
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        quantity = int(request.POST.get("quantity", 1))
        unit_price = int(request.POST.get("unit_price", 0))

        if name and unit_price > 0:
            OrderItem.objects.create(
                session=session,
                item_type=OrderItem.TYPE_OUTSIDE,
                name=name,
                quantity=quantity,
                unit_price=unit_price,
                created_by=request.user,
            )
            messages.success(request, f"Đã thêm dịch vụ ngoài: {name}.")
        else:
            messages.error(request, "Vui lòng nhập đầy đủ tên và giá.")

    return redirect("room_detail", room_id=session.room_id)


@staff_required
def remove_order_item(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    room_id = item.session.room_id
    item.delete()
    messages.success(request, "Đã xóa món.")
    return redirect("room_detail", room_id=room_id)


@staff_required
def merge_table(request):
    """Gộp 2 session vào nhau."""
    if request.method == "POST":
        primary_session_id = request.POST.get("primary_session_id")
        secondary_session_id = request.POST.get("secondary_session_id")

        if primary_session_id == secondary_session_id:
            messages.error(request, "Không thể gộp phòng với chính nó.")
            return redirect("dashboard")

        primary = get_object_or_404(RoomSession, pk=primary_session_id, status="open")
        secondary = get_object_or_404(RoomSession, pk=secondary_session_id, status="open")

        # Kiểm tra secondary chưa được gộp vào đâu khác
        if secondary.merged_into is not None:
            messages.error(request, f"Phòng {secondary.room.name} đã được gộp với phòng khác.")
            return redirect("dashboard")

        if primary.merged_into is not None:
            messages.error(request, f"Phòng {primary.room.name} đã được gộp với phòng khác.")
            return redirect("dashboard")

        secondary.merged_into = primary
        secondary.save()

        messages.success(request, f"Đã gộp phòng {secondary.room.name} vào phòng {primary.room.name}.")
        return redirect("room_detail", room_id=primary.room_id)

    return redirect("dashboard")


@staff_required
def unmerge_table(request, session_id):
    """Hủy gộp bàn."""
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    if session.merged_into is None:
        messages.error(request, "Session này chưa được gộp với phòng nào.")
        return redirect("dashboard")

    primary = session.merged_into
    session.merged_into = None
    session.save()

    messages.success(request, f"Đã tách phòng {session.room.name} ra khỏi phòng {primary.room.name}.")
    return redirect("room_detail", room_id=primary.room_id)
