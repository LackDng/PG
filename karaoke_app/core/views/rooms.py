from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from core.models import Room, RoomSession, ServiceOrder, OrderItem, ServiceType, MenuItem, MenuCategory, ActivityLog, Config, Invoice
from core.decorators import login_required_custom, staff_required, admin_required
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
        elapsed_min = (now - so.started_at).total_seconds() / 60
        bd["can_cancel"] = (so.status == ServiceOrder.STATUS_RUNNING and elapsed_min <= 30)
        service_breakdowns.append(bd)

    # Service types currently running in any room (for uniqueness check in UI)
    running_service_type_ids = set(
        ServiceOrder.objects.filter(status=ServiceOrder.STATUS_RUNNING)
        .values_list("service_type_id", flat=True)
    )

    # Lịch sử hoạt động của session (và các session đã gộp)
    all_session_ids = [session.pk] + list(session.merged_sessions.values_list("pk", flat=True))
    activity_logs = ActivityLog.objects.filter(session_id__in=all_session_ids).select_related("user")[:50]

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
        "running_service_type_ids": running_service_type_ids,
        "categories": categories,
        "menu_items": menu_items,
        "activity_logs": activity_logs,
        "now": now,
        "printer_ip": Config.get("printer_ip", ""),
        "printer_port": Config.get("printer_port", "9100"),
        "discount_choices": Invoice.DISCOUNT_CHOICES,
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

    ActivityLog.log(ActivityLog.ACTION_OPEN_ROOM, request.user,
                    f"Mở phòng {room.name}", session=session)
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

        conflict = ServiceOrder.objects.filter(
            service_type=service_type, status=ServiceOrder.STATUS_RUNNING
        ).select_related("session__room").first()
        if conflict:
            room_name = conflict.session.room.name
            messages.error(request, f"Dịch vụ '{service_type.name}' đang được sử dụng tại {room_name}.")
            return redirect("room_detail", room_id=session.room_id)

        ServiceOrder.objects.create(
            session=session,
            service_type=service_type,
            service_name=service_type.name,
            base_price=service_type.base_price,
            started_by=request.user,
        )
        ActivityLog.log(ActivityLog.ACTION_ADD_SERVICE, request.user,
                        f"Thêm dịch vụ '{service_type.name}' vào phòng {session.room.name}", session=session)
        messages.success(request, f"Đã thêm {service_type.name}.")

    return redirect("room_detail", room_id=session.room_id)


@staff_required
def cancel_service_order(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, status=ServiceOrder.STATUS_RUNNING)

    elapsed_min = (timezone.now() - order.started_at).total_seconds() / 60
    if elapsed_min > 30:
        messages.error(request, "Chỉ được hủy dịch vụ trong vòng 30 phút đầu.")
        return redirect("room_detail", room_id=order.session.room_id)

    reason = request.POST.get("cancel_reason", "").strip()
    if not reason:
        messages.error(request, "Vui lòng nhập lý do hủy.")
        return redirect("room_detail", room_id=order.session.room_id)

    order.status = ServiceOrder.STATUS_CANCELLED
    order.ended_at = timezone.now()
    order.cancel_reason = reason
    order.save()

    ActivityLog.log(
        ActivityLog.ACTION_CANCEL_SERVICE,
        request.user,
        f"Hủy dịch vụ '{order.service_name}' tại {order.session.room.name}. Lý do: {reason}",
        session=order.session,
    )
    messages.success(request, f"Đã hủy dịch vụ {order.service_name}.")
    return redirect("room_detail", room_id=order.session.room_id)


@require_POST
@staff_required
def stop_service_order(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, status="running")
    order.status = ServiceOrder.STATUS_STOPPED
    order.ended_at = timezone.now()
    order.save()
    ActivityLog.log(ActivityLog.ACTION_STOP_SERVICE, request.user,
                    f"Dừng dịch vụ '{order.service_name}' tại phòng {order.session.room.name}",
                    session=order.session)
    messages.success(request, f"Đã dừng {order.service_name}.")
    return redirect("room_detail", room_id=order.session.room_id)


@staff_required
def add_menu_item(request, session_id):
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    if request.method == "POST":
        menu_item_id = request.POST.get("menu_item_id")
        quantity = int(request.POST.get("quantity", 1) or 1)
        if quantity <= 0:
            quantity = 1

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
        ActivityLog.log(ActivityLog.ACTION_ADD_FOOD, request.user,
                        f"Gọi {quantity}x '{menu_item.name}' vào phòng {session.room.name}",
                        session=session)
        messages.success(request, f"Đã thêm {quantity}x {menu_item.name}.")

    return redirect("room_detail", room_id=session.room_id)


@staff_required
def add_outside_item(request, session_id):
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        quantity = max(1, int(request.POST.get("quantity", 1) or 1))
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
            ActivityLog.log(ActivityLog.ACTION_ADD_OUTSIDE, request.user,
                            f"Thêm mua ngoài {quantity}x '{name}' vào phòng {session.room.name}",
                            session=session)
            messages.success(request, f"Đã thêm dịch vụ ngoài: {name}.")
        else:
            messages.error(request, "Vui lòng nhập đầy đủ tên và giá.")

    return redirect("room_detail", room_id=session.room_id)


@staff_required
def remove_order_item(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    room_id = item.session.room_id
    session = item.session
    if session.status != "open":
        messages.error(request, "Không thể xóa món của phòng đã đóng/hủy.")
        return redirect("room_detail", room_id=room_id)
    ActivityLog.log(ActivityLog.ACTION_REMOVE_ITEM, request.user,
                    f"Xóa '{item.name}' x{item.quantity} khỏi phòng {session.room.name}",
                    session=session)
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

        ActivityLog.log(ActivityLog.ACTION_MERGE_TABLE, request.user,
                        f"Gộp phòng {secondary.room.name} vào phòng {primary.room.name}",
                        session=primary)
        messages.success(request, f"Đã gộp phòng {secondary.room.name} vào phòng {primary.room.name}.")
        return redirect("room_detail", room_id=primary.room_id)

    return redirect("dashboard")


@admin_required
def cancel_room(request, session_id):
    """Admin hủy phòng (không tính tiền, không xuất hóa đơn). Yêu cầu lý do."""
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    reason = request.POST.get("cancel_reason", "").strip()
    if not reason:
        messages.error(request, "Vui lòng nhập lý do hủy phòng.")
        return redirect("room_detail", room_id=session.room_id)

    # Stop all running services before cancelling
    session.get_all_service_orders().filter(status=ServiceOrder.STATUS_RUNNING).update(
        status=ServiceOrder.STATUS_STOPPED, ended_at=timezone.now()
    )

    room = session.room
    session.status = RoomSession.STATUS_CANCELLED
    session.closed_at = timezone.now()
    session.save()

    room.status = Room.STATUS_AVAILABLE
    room.save()

    ActivityLog.log(
        ActivityLog.ACTION_CANCEL_ROOM,
        request.user,
        f"Hủy phòng {room.name}. Lý do: {reason}",
        session=session,
    )
    messages.success(request, f"Đã hủy phòng {room.name}. Phòng sẵn sàng cho khách mới.")
    return redirect("dashboard")


@require_POST
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

    ActivityLog.log(ActivityLog.ACTION_UNMERGE_TABLE, request.user,
                    f"Hủy gộp phòng {session.room.name} khỏi phòng {primary.room.name}",
                    session=primary)
    messages.success(request, f"Đã tách phòng {session.room.name} ra khỏi phòng {primary.room.name}.")
    return redirect("room_detail", room_id=primary.room_id)
