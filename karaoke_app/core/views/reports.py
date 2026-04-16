from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum
from django.contrib import messages
from datetime import timedelta, date
from core.models import Invoice, RoomSession, ServiceOrder, OrderItem
from core.decorators import accountant_required, admin_required
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def _get_report_data(report_date):
    """Lấy dữ liệu báo cáo cho 1 ngày. Trả về dict."""
    tz = timezone.get_current_timezone()
    day_start = timezone.datetime.combine(report_date, timezone.datetime.min.time()).replace(tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    invoices = Invoice.objects.filter(
        created_at__gte=day_start,
        created_at__lt=day_end,
    ).select_related("session__room", "created_by").order_by("-created_at")

    total_service  = invoices.aggregate(s=Sum("total_service"))["s"] or 0
    total_food     = invoices.aggregate(s=Sum("total_food"))["s"] or 0
    total_outside  = invoices.aggregate(s=Sum("total_outside"))["s"] or 0
    total_discount = invoices.aggregate(s=Sum("discount_amount"))["s"] or 0
    total_revenue  = invoices.aggregate(s=Sum("total_after_discount"))["s"] or 0
    total_tip      = invoices.aggregate(s=Sum("tip"))["s"] or 0
    total_cash     = invoices.aggregate(s=Sum("cash_amount"))["s"] or 0
    total_transfer = invoices.aggregate(s=Sum("transfer_amount"))["s"] or 0

    room_summaries = {}
    for inv in invoices:
        rname = inv.session.room.name
        if rname not in room_summaries:
            room_summaries[rname] = {"room_name": rname, "count": 0, "service": 0, "food": 0, "outside": 0, "total": 0}
        room_summaries[rname]["count"]   += 1
        room_summaries[rname]["service"] += inv.total_service
        room_summaries[rname]["food"]    += inv.total_food
        room_summaries[rname]["outside"] += inv.total_outside
        room_summaries[rname]["total"]   += inv.total_after_discount

    room_summaries = sorted(room_summaries.values(), key=lambda x: x["total"], reverse=True)

    return {
        "invoices":       invoices,
        "total_service":  total_service,
        "total_food":     total_food,
        "total_outside":  total_outside,
        "total_discount": total_discount,
        "total_revenue":  total_revenue,
        "total_tip":      total_tip,
        "total_cash":     total_cash,
        "total_transfer": total_transfer,
        "room_summaries": room_summaries,
        "invoice_count":  invoices.count(),
    }


@accountant_required
def daily_report(request):
    today = timezone.localdate()
    report_date_str = request.GET.get("date", today.strftime("%Y-%m-%d"))
    try:
        report_date = date.fromisoformat(report_date_str)
    except ValueError:
        report_date = today

    data = _get_report_data(report_date)
    return render(request, "reports/daily.html", {
        "report_date":     report_date,
        "report_date_str": report_date_str,
        **data,
    })


@accountant_required
def export_excel(request):
    """Xuất báo cáo ngày ra file Excel."""
    today = timezone.localdate()
    report_date_str = request.GET.get("date", today.strftime("%Y-%m-%d"))
    try:
        report_date = date.fromisoformat(report_date_str)
    except ValueError:
        report_date = today

    data = _get_report_data(report_date)
    wb = _build_excel(report_date, data)

    filename = f"baocao_{report_date.strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def _build_excel(report_date, data):
    """Tạo workbook Excel từ dữ liệu báo cáo."""
    wb = openpyxl.Workbook()

    # ─── Sheet 1: Tổng quan ───────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Tổng quan"

    header_font   = Font(bold=True, size=12)
    title_font    = Font(bold=True, size=14)
    header_fill   = PatternFill("solid", fgColor="1F3864")
    subheader_fill = PatternFill("solid", fgColor="2E75B6")
    white_font    = Font(bold=True, color="FFFFFF", size=11)
    center        = Alignment(horizontal="center", vertical="center")
    right         = Alignment(horizontal="right", vertical="center")
    thin          = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    # Tiêu đề
    ws1.merge_cells("A1:F1")
    ws1["A1"] = f"BÁO CÁO DOANH THU NGÀY {report_date.strftime('%d/%m/%Y')}"
    ws1["A1"].font  = Font(bold=True, size=16, color="1F3864")
    ws1["A1"].alignment = center

    ws1.merge_cells("A2:F2")
    ws1["A2"] = f"Tổng số hóa đơn: {data['invoice_count']}"
    ws1["A2"].alignment = center

    # Bảng tổng hợp
    ws1["A4"] = "CHỈ TIÊU"
    ws1["B4"] = "GIÁ TRỊ (VNĐ)"
    for cell in [ws1["A4"], ws1["B4"]]:
        cell.font = white_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin

    summary_rows = [
        ("Tổng doanh thu",       data["total_revenue"]),
        ("Dịch vụ",              data["total_service"]),
        ("Đồ ăn/uống",           data["total_food"]),
        ("Mua ngoài",            data["total_outside"]),
        ("Tổng giảm giá",        -data["total_discount"]),
        ("Tip",                  data["total_tip"]),
        ("",                     None),
        ("Tiền mặt",             data["total_cash"]),
        ("Chuyển khoản",         data["total_transfer"]),
    ]
    for i, (label, val) in enumerate(summary_rows, start=5):
        ws1.cell(row=i, column=1, value=label).border = thin
        cell = ws1.cell(row=i, column=2, value=val)
        cell.border = thin
        cell.alignment = right
        if val is not None:
            cell.number_format = '#,##0'
        if label == "Tổng doanh thu":
            ws1.cell(row=i, column=1).font = Font(bold=True)
            cell.font = Font(bold=True)

    # Bảng theo phòng
    row = 5 + len(summary_rows) + 2
    ws1.cell(row=row, column=1, value="DOANH THU THEO PHÒNG").font = header_font
    row += 1
    room_headers = ["Phòng", "Số lần", "Dịch vụ", "Đồ ăn/uống", "Mua ngoài", "Tổng"]
    for c, h in enumerate(room_headers, 1):
        cell = ws1.cell(row=row, column=c, value=h)
        cell.font = white_font
        cell.fill = subheader_fill
        cell.alignment = center
        cell.border = thin
    row += 1
    for rs in data["room_summaries"]:
        vals = [rs["room_name"], rs["count"], rs["service"], rs["food"], rs["outside"], rs["total"]]
        for c, v in enumerate(vals, 1):
            cell = ws1.cell(row=row, column=c, value=v)
            cell.border = thin
            if c >= 3:
                cell.number_format = '#,##0'
                cell.alignment = right
        row += 1

    ws1.column_dimensions["A"].width = 25
    ws1.column_dimensions["B"].width = 18
    for col in "CDEF":
        ws1.column_dimensions[col].width = 18

    # ─── Sheet 2: Chi tiết hóa đơn ────────────────────────────────────────────
    ws2 = wb.create_sheet("Chi tiết hóa đơn")

    detail_headers = [
        "#", "Phòng", "Giờ thanh toán",
        "Dịch vụ (đ)", "Đồ ăn (đ)", "Mua ngoài (đ)",
        "Giảm giá %", "Giảm giá (đ)", "Sau giảm giá",
        "Tip (đ)", "Tổng (đ)", "Hình thức TT",
        "Tiền mặt (đ)", "Chuyển khoản (đ)", "Thu ngân",
    ]
    for c, h in enumerate(detail_headers, 1):
        cell = ws2.cell(row=1, column=c, value=h)
        cell.font = white_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin

    pm_labels = {"cash": "Tiền mặt", "transfer": "Chuyển khoản", "mixed": "Kết hợp"}
    for r, inv in enumerate(data["invoices"], start=2):
        row_data = [
            inv.id,
            inv.session.room.name,
            timezone.localtime(inv.created_at).strftime("%d/%m/%Y %H:%M"),
            inv.total_service,
            inv.total_food,
            inv.total_outside,
            inv.discount_percent,
            inv.discount_amount,
            inv.total_after_discount,
            inv.tip,
            inv.total_after_discount,
            pm_labels.get(inv.payment_method, inv.payment_method),
            inv.cash_amount,
            inv.transfer_amount,
            inv.created_by.get_display_name() if inv.created_by else "",
        ]
        money_cols = {4, 5, 6, 8, 9, 10, 11, 13, 14}
        for c, v in enumerate(row_data, 1):
            cell = ws2.cell(row=r, column=c, value=v)
            cell.border = thin
            if c in money_cols and isinstance(v, (int, float)):
                cell.number_format = '#,##0'
                cell.alignment = right

    col_widths = [6, 15, 20, 15, 15, 15, 12, 15, 15, 12, 15, 16, 16, 18, 18]
    for i, w in enumerate(col_widths, 1):
        ws2.column_dimensions[ws2.cell(row=1, column=i).column_letter].width = w

    return wb


@admin_required
def delete_revenue(request):
    """Xóa dữ liệu doanh thu theo khoảng thời gian (admin only)."""
    if request.method == "POST":
        date_from_str = request.POST.get("date_from", "")
        date_to_str   = request.POST.get("date_to", "")
        confirm       = request.POST.get("confirm") == "yes"

        if not confirm:
            messages.error(request, "Vui lòng tick xác nhận trước khi xóa.")
            return redirect("delete_revenue")

        try:
            date_from = date.fromisoformat(date_from_str)
            date_to   = date.fromisoformat(date_to_str)
        except ValueError:
            messages.error(request, "Ngày không hợp lệ.")
            return redirect("delete_revenue")

        if date_from > date_to:
            messages.error(request, "Ngày bắt đầu phải trước ngày kết thúc.")
            return redirect("delete_revenue")

        tz = timezone.get_current_timezone()
        dt_from = timezone.datetime.combine(date_from, timezone.datetime.min.time()).replace(tzinfo=tz)
        dt_to   = timezone.datetime.combine(date_to, timezone.datetime.max.time()).replace(tzinfo=tz)

        invoices = Invoice.objects.filter(created_at__gte=dt_from, created_at__lte=dt_to)
        count = invoices.count()
        # Xóa invoice trước (cascade sẽ không xóa session), chỉ xóa invoice
        invoices.delete()

        messages.success(request, f"Đã xóa {count} hóa đơn từ {date_from_str} đến {date_to_str}.")
        return redirect("delete_revenue")

    return render(request, "reports/delete_revenue.html")
