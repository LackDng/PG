"""
Logic tính tiền dịch vụ mic:

  0  – 30  phút : MIỄN PHÍ
  31 – 120 phút : base_price (gói chuẩn, ví dụ 500.000đ)
  121 – 135 phút: +0đ (15 phút grace)
  Mỗi 25 phút tiếp theo (sau grace): +100.000đ
    0  – 25  phút billable overtime: +100.000đ
    26 – 50  phút: +200.000đ
    51 – 75  phút: +300.000đ
    76 – 100 phút: +400.000đ
    101– 120 phút: +500.000đ (≈ gói mới)
    và tiếp tục cho overtime dài hơn...
"""

import math
from django.utils import timezone

FREE_MINUTES = 30          # 0-30 phút: miễn phí
PACKAGE_MINUTES = 120      # gói chuẩn kết thúc lúc 120 phút
GRACE_MINUTES = 15         # grace period sau khi hết gói chuẩn
OVERTIME_BLOCK = 25        # mỗi block = 25 phút
OVERTIME_BLOCK_PRICE = 100_000  # mỗi block = 100k


def calculate_service_cost(started_at, ended_at, base_price=500_000):
    """Tính tiền 1 dịch vụ mic từ started_at đến ended_at."""
    duration_seconds = max(0, (ended_at - started_at).total_seconds())
    duration_minutes = duration_seconds / 60

    if duration_minutes <= FREE_MINUTES:
        return 0

    if duration_minutes <= PACKAGE_MINUTES:
        return base_price

    # Quá 120 phút
    overtime_minutes = duration_minutes - PACKAGE_MINUTES

    if overtime_minutes <= GRACE_MINUTES:
        return base_price

    # Tính phát sinh sau 15 phút grace
    billable_overtime = overtime_minutes - GRACE_MINUTES
    blocks = math.ceil(billable_overtime / OVERTIME_BLOCK)
    overtime_charge = blocks * OVERTIME_BLOCK_PRICE

    return base_price + overtime_charge


def get_cost_breakdown(started_at, ended_at, base_price=500_000):
    """Trả về chi tiết tính tiền để hiển thị trên hóa đơn."""
    duration_seconds = max(0, (ended_at - started_at).total_seconds())
    duration_minutes = duration_seconds / 60

    breakdown = {
        "duration_minutes": int(duration_minutes),
        "duration_str": format_duration(duration_minutes),
        "base_price": base_price,
        "overtime_charge": 0,
        "total": 0,
        "status": "",
    }

    if duration_minutes <= FREE_MINUTES:
        breakdown["status"] = "free"
        breakdown["total"] = 0
        return breakdown

    if duration_minutes <= PACKAGE_MINUTES:
        breakdown["status"] = "package"
        breakdown["total"] = base_price
        return breakdown

    overtime_minutes = duration_minutes - PACKAGE_MINUTES

    if overtime_minutes <= GRACE_MINUTES:
        breakdown["status"] = "grace"
        breakdown["overtime_minutes"] = int(overtime_minutes)
        breakdown["grace_remaining"] = int(GRACE_MINUTES - overtime_minutes)
        breakdown["total"] = base_price
        return breakdown

    billable_overtime = overtime_minutes - GRACE_MINUTES
    blocks = math.ceil(billable_overtime / OVERTIME_BLOCK)
    overtime_charge = blocks * OVERTIME_BLOCK_PRICE

    breakdown["status"] = "overtime"
    breakdown["overtime_minutes"] = int(overtime_minutes)
    breakdown["billable_overtime"] = int(billable_overtime)
    breakdown["overtime_blocks"] = blocks
    breakdown["overtime_charge"] = overtime_charge
    breakdown["total"] = base_price + overtime_charge
    return breakdown


def format_duration(minutes):
    """Định dạng số phút thành chuỗi dễ đọc."""
    h = int(minutes) // 60
    m = int(minutes) % 60
    if h > 0:
        return f"{h}h{m:02d}p"
    return f"{m}p"


def calculate_session_total(session):
    """Tính tổng tiền cho 1 session (bao gồm cả merged sessions)."""
    now = timezone.now()

    # Tổng tiền dịch vụ mic
    service_orders = session.get_all_service_orders()
    total_service = sum(
        so.calculate_cost(at_time=now) for so in service_orders
    )

    # Tổng tiền đồ ăn/uống
    order_items = session.get_all_order_items()
    total_food = sum(
        item.subtotal for item in order_items if item.item_type == "menu"
    )
    total_outside = sum(
        item.subtotal for item in order_items if item.item_type == "outside"
    )

    return {
        "total_service": total_service,
        "total_food": total_food,
        "total_outside": total_outside,
        "subtotal": total_service + total_food + total_outside,
    }
