"""
In hóa đơn nhiệt qua ESC/POS Network/TCP.
Yêu cầu: python-escpos
"""

from django.utils import timezone

try:
    from escpos.printer import Network as EscPosNetwork
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False


def print_invoice(invoice, ip, port=9100):
    """
    In hóa đơn ra máy in nhiệt.
    Trả về (success: bool, message: str)
    """
    if not ESCPOS_AVAILABLE:
        return False, "Thư viện python-escpos chưa được cài đặt."

    try:
        p = EscPosNetwork(ip, port, timeout=5)
        _print_invoice_content(p, invoice)
        p.close()
        return True, "In thành công."
    except ConnectionRefusedError:
        return False, f"Không thể kết nối máy in tại {ip}:{port}."
    except Exception as e:
        return False, f"Lỗi máy in: {str(e)}"


def _print_invoice_content(p, invoice):
    """Ghi nội dung hóa đơn vào máy in."""
    from core.pricing import format_duration

    session = invoice.session
    room_name = session.room.name
    now = timezone.localtime(invoice.created_at)

    # Tiêu đề
    p.set(align="center", bold=True, double_height=True, double_width=True)
    p.text("HOA DON\n")
    p.set(align="center", bold=False, double_height=False, double_width=False)
    p.text("DICH VU KARAOKE\n")
    p.text("-" * 32 + "\n")

    # Thông tin phòng
    p.set(align="left")
    p.text(f"Phong : {room_name}\n")
    p.text(f"Thoi gian: {now.strftime('%d/%m/%Y %H:%M')}\n")
    p.text(f"Thu ngan : {invoice.created_by.get_display_name() if invoice.created_by else ''}\n")
    p.text("=" * 32 + "\n")

    # Dịch vụ
    service_orders = session.get_all_service_orders()
    if service_orders.exists():
        p.set(bold=True)
        p.text("DICH VU:\n")
        p.set(bold=False)
        for so in service_orders:
            end = so.ended_at or invoice.created_at
            dur = format_duration((end - so.started_at).total_seconds() / 60)
            cost = so.calculate_cost(at_time=invoice.created_at)
            name = _truncate(so.service_name, 16)
            p.text(f"{name} {dur}\n")
            p.text(f"{'':>20}{cost:>10,}d\n")

    # Đồ ăn/uống
    menu_items = [i for i in session.get_all_order_items() if i.item_type == "menu"]
    if menu_items:
        p.set(bold=True)
        p.text("DO AN/UONG:\n")
        p.set(bold=False)
        for item in menu_items:
            name = _truncate(item.name, 16)
            p.text(f"{name} x{item.quantity}\n")
            p.text(f"{'':>20}{item.subtotal:>10,}d\n")

    # Mua ngoài
    outside_items = [i for i in session.get_all_order_items() if i.item_type == "outside"]
    if outside_items:
        p.set(bold=True)
        p.text("MUA NGOAI:\n")
        p.set(bold=False)
        for item in outside_items:
            name = _truncate(item.name, 16)
            p.text(f"{name} x{item.quantity}\n")
            p.text(f"{'':>20}{item.subtotal:>10,}d\n")

    p.text("-" * 32 + "\n")

    # Tổng
    p.set(bold=True)
    p.text(f"{'Tong cong:':20}{invoice.subtotal:>10,}d\n")

    if invoice.discount_percent > 0:
        p.text(f"{'Giam gia ' + str(invoice.discount_percent) + '%:':20}{-invoice.discount_amount:>10,}d\n")
        p.text(f"{'Sau giam gia:':20}{invoice.total_after_discount:>10,}d\n")

    p.set(bold=False)

    if invoice.tip > 0:
        p.text(f"{'Tip:':20}{invoice.tip:>10,}d\n")

    p.text("=" * 32 + "\n")
    p.set(bold=True, double_height=True)
    p.text(f"TONG THANH TOAN:\n")
    p.text(f"{invoice.total_after_discount:>30,}d\n")
    p.set(bold=False, double_height=False)

    # Hình thức thanh toán
    p.text("-" * 32 + "\n")
    if invoice.payment_method == "cash":
        p.text(f"Tien mat: {invoice.cash_amount:>20,}d\n")
    elif invoice.payment_method == "transfer":
        p.text(f"Chuyen khoan: {invoice.transfer_amount:>16,}d\n")
    else:
        p.text(f"Tien mat: {invoice.cash_amount:>20,}d\n")
        p.text(f"Chuyen khoan: {invoice.transfer_amount:>16,}d\n")

    p.text("=" * 32 + "\n")
    p.set(align="center")
    p.text("Cam on quy khach!\n")
    p.text("Hen gap lai!\n")
    p.ln(4)
    p.cut()


def _truncate(text, max_len):
    if len(text) > max_len:
        return text[:max_len - 2] + ".."
    return text


def get_invoice_text(invoice):
    """Trả về nội dung hóa đơn dạng text (dùng để xem trước)."""
    from core.pricing import format_duration

    session = invoice.session
    lines = []

    lines.append("=" * 40)
    lines.append("           HÓA ĐƠN KARAOKE")
    lines.append("=" * 40)
    lines.append(f"Phòng     : {session.room.name}")
    lines.append(f"Thời gian : {timezone.localtime(invoice.created_at).strftime('%d/%m/%Y %H:%M')}")
    lines.append("-" * 40)

    service_orders = session.get_all_service_orders()
    if service_orders.exists():
        lines.append("DỊCH VỤ:")
        for so in service_orders:
            end = so.ended_at or invoice.created_at
            dur = format_duration((end - so.started_at).total_seconds() / 60)
            cost = so.calculate_cost(at_time=invoice.created_at)
            lines.append(f"  {so.service_name} ({dur})")
            lines.append(f"  {'':>28}{cost:>8,}đ")

    menu_items = [i for i in session.get_all_order_items() if i.item_type == "menu"]
    if menu_items:
        lines.append("ĐỒ ĂN/UỐNG:")
        for item in menu_items:
            lines.append(f"  {item.name} x{item.quantity}")
            lines.append(f"  {'':>28}{item.subtotal:>8,}đ")

    outside_items = [i for i in session.get_all_order_items() if i.item_type == "outside"]
    if outside_items:
        lines.append("MUA NGOÀI:")
        for item in outside_items:
            lines.append(f"  {item.name} x{item.quantity}")
            lines.append(f"  {'':>28}{item.subtotal:>8,}đ")

    lines.append("-" * 40)
    lines.append(f"{'Tổng cộng:':<30}{invoice.subtotal:>8,}đ")
    if invoice.discount_percent > 0:
        lines.append(f"{'Giảm giá ' + str(invoice.discount_percent) + '%:':<30}{-invoice.discount_amount:>8,}đ")
        lines.append(f"{'Sau giảm giá:':<30}{invoice.total_after_discount:>8,}đ")
    if invoice.tip > 0:
        lines.append(f"{'Tip:':<30}{invoice.tip:>8,}đ")
    lines.append("=" * 40)
    lines.append(f"TỔNG THANH TOÁN: {invoice.total_after_discount:>20,}đ")
    lines.append("=" * 40)

    if invoice.payment_method == "cash":
        lines.append(f"Tiền mặt: {invoice.cash_amount:,}đ")
    elif invoice.payment_method == "transfer":
        lines.append(f"Chuyển khoản: {invoice.transfer_amount:,}đ")
    else:
        lines.append(f"Tiền mặt    : {invoice.cash_amount:,}đ")
        lines.append(f"Chuyển khoản: {invoice.transfer_amount:,}đ")

    lines.append("=" * 40)
    lines.append("         Cảm ơn quý khách!")

    return "\n".join(lines)
