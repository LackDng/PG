from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from core.models import RoomSession, Invoice, Config
from core.decorators import login_required_custom, cashier_required
from core.pricing import calculate_session_total
from core.printing import print_invoice, get_invoice_text


@login_required_custom
def checkout_view(request, session_id):
    session = get_object_or_404(RoomSession, pk=session_id, status="open")

    # Kiểm tra session không phải là session con (đã gộp vào session khác)
    if session.merged_into is not None:
        primary = session.merged_into
        messages.info(request, f"Phòng này đang gộp với phòng {primary.room.name}. Thanh toán từ phòng chính.")
        return redirect("room_detail", room_id=primary.room_id)

    totals = calculate_session_total(session)
    now = timezone.now()

    # Tính toán dịch vụ mic cho hiển thị
    service_orders = session.get_all_service_orders()
    order_items = session.get_all_order_items()
    merged_sessions = session.merged_sessions.all()

    discount_choices = Invoice.DISCOUNT_CHOICES

    # Lấy cấu hình máy in
    printer_ip = Config.get("printer_ip", "")
    printer_port = Config.get("printer_port", "9100")

    if request.method == "POST" and request.user.can_checkout():
        discount_percent = int(request.POST.get("discount_percent", 0))
        tip = int(request.POST.get("tip", 0) or 0)
        payment_method = request.POST.get("payment_method", "cash")
        cash_amount = int(request.POST.get("cash_amount", 0) or 0)
        transfer_amount = int(request.POST.get("transfer_amount", 0) or 0)
        do_print = request.POST.get("do_print") == "1"
        custom_printer_ip = request.POST.get("printer_ip", "").strip() or printer_ip
        custom_printer_port = int(request.POST.get("printer_port", printer_port) or 9100)

        subtotal = totals["subtotal"]
        discount_amount = int(subtotal * discount_percent / 100)
        total_after_discount = subtotal - discount_amount

        # Xác nhận số tiền hợp lệ
        if payment_method == "cash":
            cash_amount = total_after_discount
            transfer_amount = 0
        elif payment_method == "transfer":
            transfer_amount = total_after_discount
            cash_amount = 0
        # mixed: dùng giá trị từ form

        # Dừng tất cả dịch vụ mic đang chạy
        for so in session.get_all_service_orders().filter(status="running"):
            so.status = "stopped"
            so.ended_at = now
            so.save()

        # Tạo invoice
        invoice = Invoice.objects.create(
            session=session,
            total_service=totals["total_service"],
            total_food=totals["total_food"],
            total_outside=totals["total_outside"],
            subtotal=subtotal,
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            total_after_discount=total_after_discount,
            tip=tip,
            payment_method=payment_method,
            cash_amount=cash_amount,
            transfer_amount=transfer_amount,
            created_by=request.user,
        )

        # Đóng session chính và các session gộp
        session.status = RoomSession.STATUS_PAID
        session.closed_at = now
        session.save()

        for merged in session.merged_sessions.all():
            merged.status = RoomSession.STATUS_PAID
            merged.closed_at = now
            merged.save()
            merged.room.status = "cleaning"
            merged.room.save()

        session.room.status = "cleaning"
        session.room.save()

        # In hóa đơn nếu được yêu cầu
        if do_print and custom_printer_ip:
            success, msg = print_invoice(invoice, custom_printer_ip, custom_printer_port)
            if success:
                invoice.printed = True
                invoice.printer_ip = custom_printer_ip
                invoice.printer_port = custom_printer_port
                invoice.save()
                messages.success(request, "In hóa đơn thành công.")
            else:
                messages.warning(request, f"Thanh toán thành công nhưng in thất bại: {msg}")

        messages.success(request, f"Thanh toán thành công! Tổng: {total_after_discount:,}đ")
        return redirect("invoice_detail", invoice_id=invoice.id)

    elif request.method == "POST" and not request.user.can_checkout():
        messages.error(request, "Bạn không có quyền thanh toán.")

    return render(request, "payment/checkout.html", {
        "session": session,
        "merged_sessions": merged_sessions,
        "service_orders": service_orders,
        "order_items": order_items,
        "totals": totals,
        "discount_choices": discount_choices,
        "printer_ip": printer_ip,
        "printer_port": printer_port,
        "now": now,
    })


@login_required_custom
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    invoice_text = get_invoice_text(invoice)

    printer_ip = Config.get("printer_ip", "")
    printer_port = Config.get("printer_port", "9100")

    return render(request, "payment/invoice_detail.html", {
        "invoice": invoice,
        "invoice_text": invoice_text,
        "printer_ip": printer_ip,
        "printer_port": printer_port,
    })


@cashier_required
def reprint_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    printer_ip = request.POST.get("printer_ip", "").strip() or Config.get("printer_ip", "")
    printer_port = int(request.POST.get("printer_port", Config.get("printer_port", "9100")) or 9100)

    if not printer_ip:
        messages.error(request, "Chưa cấu hình IP máy in.")
        return redirect("invoice_detail", invoice_id=invoice_id)

    success, msg = print_invoice(invoice, printer_ip, printer_port)
    if success:
        invoice.printed = True
        invoice.save()
        messages.success(request, "In lại hóa đơn thành công.")
    else:
        messages.error(request, f"Lỗi: {msg}")

    return redirect("invoice_detail", invoice_id=invoice_id)
