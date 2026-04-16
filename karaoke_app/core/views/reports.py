from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta, date
from core.models import Invoice, RoomSession, OrderItem, ServiceOrder
from core.decorators import accountant_required


@accountant_required
def daily_report(request):
    today = timezone.localdate()
    report_date_str = request.GET.get("date", today.strftime("%Y-%m-%d"))

    try:
        report_date = date.fromisoformat(report_date_str)
    except ValueError:
        report_date = today

    # Lấy các invoice trong ngày (theo giờ địa phương)
    tz = timezone.get_current_timezone()
    day_start = timezone.datetime.combine(report_date, timezone.datetime.min.time()).replace(tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    invoices = Invoice.objects.filter(
        created_at__gte=day_start,
        created_at__lt=day_end,
    ).select_related("session__room", "created_by")

    # Tổng hợp
    total_service = invoices.aggregate(s=Sum("total_service"))["s"] or 0
    total_food = invoices.aggregate(s=Sum("total_food"))["s"] or 0
    total_outside = invoices.aggregate(s=Sum("total_outside"))["s"] or 0
    total_discount = invoices.aggregate(s=Sum("discount_amount"))["s"] or 0
    total_revenue = invoices.aggregate(s=Sum("total_after_discount"))["s"] or 0
    total_tip = invoices.aggregate(s=Sum("tip"))["s"] or 0
    total_cash = invoices.aggregate(s=Sum("cash_amount"))["s"] or 0
    total_transfer = invoices.aggregate(s=Sum("transfer_amount"))["s"] or 0

    # Chi tiết từng phòng
    room_summaries = {}
    for inv in invoices:
        room_name = inv.session.room.name
        if room_name not in room_summaries:
            room_summaries[room_name] = {
                "room_name": room_name,
                "count": 0,
                "service": 0,
                "food": 0,
                "outside": 0,
                "total": 0,
            }
        room_summaries[room_name]["count"] += 1
        room_summaries[room_name]["service"] += inv.total_service
        room_summaries[room_name]["food"] += inv.total_food
        room_summaries[room_name]["outside"] += inv.total_outside
        room_summaries[room_name]["total"] += inv.total_after_discount

    room_summaries = sorted(room_summaries.values(), key=lambda x: x["total"], reverse=True)

    # Hóa đơn chi tiết
    invoice_list = invoices.order_by("-created_at")

    context = {
        "report_date": report_date,
        "report_date_str": report_date_str,
        "invoices": invoice_list,
        "total_service": total_service,
        "total_food": total_food,
        "total_outside": total_outside,
        "total_discount": total_discount,
        "total_revenue": total_revenue,
        "total_tip": total_tip,
        "total_cash": total_cash,
        "total_transfer": total_transfer,
        "room_summaries": room_summaries,
        "invoice_count": invoices.count(),
    }

    return render(request, "reports/daily.html", context)
