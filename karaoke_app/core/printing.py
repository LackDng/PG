"""
In hoa don nhiet qua ESC/POS Network/TCP hoac may in Windows.
Yeu cau: python-escpos, pywin32 (Windows only)
"""

from django.utils import timezone

try:
    from escpos.printer import Network as EscPosNetwork
    from escpos.printer import Dummy as EscPosDummy
    ESCPOS_AVAILABLE = True
except Exception:
    ESCPOS_AVAILABLE = False
    EscPosNetwork = None
    EscPosDummy = None

WIN32_AVAILABLE = False
try:
    import win32print as _win32print
    WIN32_AVAILABLE = True
except ImportError:
    _win32print = None


def get_windows_printers():
    """Tra ve danh sach ten may in dang cai tren Windows. [] neu khong ho tro."""
    if not WIN32_AVAILABLE:
        return []
    try:
        flags = _win32print.PRINTER_ENUM_LOCAL | _win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in _win32print.EnumPrinters(flags)]
    except Exception:
        return []


def get_default_windows_printer():
    """Tra ve ten may in mac dinh cua Windows, hoac '' neu khong ho tro."""
    if not WIN32_AVAILABLE:
        return ""
    try:
        return _win32print.GetDefaultPrinter()
    except Exception:
        return ""


def _send_raw_to_windows_printer(printer_name, raw_bytes):
    hprinter = _win32print.OpenPrinter(printer_name)
    try:
        _win32print.StartDocPrinter(hprinter, 1, ("Receipt", None, "RAW"))
        try:
            _win32print.StartPagePrinter(hprinter)
            _win32print.WritePrinter(hprinter, raw_bytes)
            _win32print.EndPagePrinter(hprinter)
        finally:
            _win32print.EndDocPrinter(hprinter)
    finally:
        _win32print.ClosePrinter(hprinter)


# ── VietQR EMVCo payload generator ───────────────────────────────────────────

def _make_vietqr_payload(bank_bin, account_no, amount=0, description=""):
    """Tao VietQR EMVCo payload chuan de in QR code ngan hang."""

    def tlv(tag, value):
        v = str(value)
        return f"{int(tag):02d}{len(v):02d}{v}"

    acq_value = f"0006{bank_bin}01{len(account_no):02d}{account_no}"
    mai_inner = tlv(0, "A000000727") + tlv(1, acq_value) + tlv(2, "QRIBFTTA")

    desc_clean = (description or "")[:25]
    add_data = tlv(8, desc_clean) if desc_clean else ""

    payload = (
        tlv(0, "01") +
        tlv(1, "12") +
        tlv(38, mai_inner) +
        tlv(53, "704") +
        (tlv(54, str(int(amount))) if amount > 0 else "") +
        tlv(58, "VN") +
        (tlv(62, add_data) if add_data else "") +
        "6304"
    )

    # CRC-16/CCITT-FALSE
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF

    return payload + f"{crc:04X}"


# ── In hoa don chinh thuc ─────────────────────────────────────────────────────

def print_invoice(invoice, ip="", port=9100, printer_name=""):
    """In hoa don. printer_name -> Windows printer; ip -> Network ESC/POS."""
    if not ESCPOS_AVAILABLE:
        return False, "Thu vien python-escpos chua duoc cai dat."
    try:
        if printer_name:
            if not WIN32_AVAILABLE:
                return False, "win32print khong co san (chi chay tren Windows)."
            d = EscPosDummy()
            _print_invoice_content(d, invoice)
            _send_raw_to_windows_printer(printer_name, d.output)
        else:
            p = EscPosNetwork(ip, port, timeout=5)
            _print_invoice_content(p, invoice)
            p.close()
        return True, "In thanh cong."
    except ConnectionRefusedError:
        return False, f"Khong the ket noi may in tai {ip}:{port}."
    except Exception as e:
        return False, f"Loi may in: {str(e)}"


def _print_shop_header(p, W, title):
    """In phan tieu de chung: ten cua hang, dia chi, hotline, tieu de phieu."""
    from core.models import Config
    shop_name = Config.get("shop_name", "KARAOKE")
    shop_address = Config.get("shop_address", "")
    shop_phone = Config.get("shop_phone", "")

    p.set(align="center", bold=True)
    p.text(f"{shop_name.upper()}\n")
    p.set(bold=False)
    if shop_address:
        p.text(f"{_center_truncate(shop_address, W)}\n")
    if shop_phone:
        p.text(f"Hotline: {shop_phone}\n")
    p.text("-" * W + "\n")
    p.set(bold=True)
    p.text(f"{title.center(W)}\n")
    p.set(bold=False)


def _center_truncate(text, width):
    if len(text) > width:
        text = text[:width - 2] + ".."
    return text.center(width)


def _print_items_section(p, W, session, ref_time):
    """In phan chi tiet hang hoa theo dang bang."""
    from core.pricing import format_duration

    p.set(bold=True)
    p.text(f"{'TEN HANG HOA':<{W-10}}{'T.TIEN':>10}\n")
    p.set(bold=False)
    p.text("-" * W + "\n")

    service_orders = session.get_all_service_orders()
    if service_orders.exists():
        for so in service_orders:
            end = so.ended_at or ref_time
            dur = format_duration((end - so.started_at).total_seconds() / 60)
            cost = so.calculate_cost(at_time=ref_time)
            start_str = timezone.localtime(so.started_at).strftime("%H:%M")
            end_str = timezone.localtime(end).strftime("%H:%M")
            name = _truncate(so.service_name, W - 10)
            p.text(f"{name:<{W-10}}{cost:>10,}d\n")
            p.text(f"  {start_str}-{end_str} {dur}\n")

    menu_items = [i for i in session.get_all_order_items() if i.item_type == "menu"]
    outside_items = [i for i in session.get_all_order_items() if i.item_type == "outside"]
    for item in list(menu_items) + list(outside_items):
        name = _truncate(item.name, W - 10)
        p.text(f"{name:<{W-10}}{item.subtotal:>10,}d\n")
        p.text(f"  {item.unit_price:,}d x {item.quantity}\n")


def _print_invoice_content(p, invoice):
    from core.models import Config

    W = 30
    session = invoice.session
    room_name = session.room.name
    now = timezone.localtime(invoice.created_at)
    opened = timezone.localtime(session.opened_at)

    _print_shop_header(p, W, "HOA DON THANH TOAN")
    p.text(f"{'Phong: ' + room_name:^{W}}\n")
    p.text("-" * W + "\n")

    p.set(align="left")
    p.text(f"So HD  : #{invoice.id}\n")
    p.text(f"Gio vao: {opened.strftime('%H:%M %d/%m/%Y')}\n")
    p.text(f"Gio ra : {now.strftime('%H:%M %d/%m/%Y')}\n")
    p.text(f"TN     : {invoice.created_by.get_display_name() if invoice.created_by else ''}\n")
    p.text("=" * W + "\n")

    _print_items_section(p, W, session, invoice.created_at)
    p.text("-" * W + "\n")

    # Tong tien
    p.set(bold=True)
    p.text(f"{'Dich vu:':<{W-12}}{invoice.total_service:>12,}d\n")
    p.text(f"{'Do an/uong:':<{W-12}}{invoice.total_food:>12,}d\n")
    if invoice.total_outside > 0:
        p.text(f"{'Mua ngoai:':<{W-12}}{invoice.total_outside:>12,}d\n")
    p.text(f"{'Tong cong:':<{W-12}}{invoice.subtotal:>12,}d\n")
    if invoice.discount_percent > 0:
        label = f"Giam gia {invoice.discount_percent}%:"
        p.text(f"{label:<{W-12}}{-invoice.discount_amount:>12,}d\n")
        p.text(f"{'Sau giam gia:':<{W-12}}{invoice.total_after_discount:>12,}d\n")
    p.set(bold=False)
    if invoice.tip > 0:
        p.text(f"{'Tip:':<{W-12}}{invoice.tip:>12,}d\n")

    p.text("=" * W + "\n")
    p.set(bold=True)
    p.text("TONG THANH TOAN:\n")
    p.text(f"{invoice.total_after_discount:>{W-1},}d\n")
    p.set(bold=False)

    p.text("-" * W + "\n")
    if invoice.payment_method == "cash":
        p.text(f"{'Tien mat:':<{W-12}}{invoice.cash_amount:>12,}d\n")
    elif invoice.payment_method == "transfer":
        p.text(f"{'Chuyen khoan:':<{W-12}}{invoice.transfer_amount:>12,}d\n")
    else:
        p.text(f"{'Tien mat:':<{W-12}}{invoice.cash_amount:>12,}d\n")
        p.text(f"{'Chuyen khoan:':<{W-12}}{invoice.transfer_amount:>12,}d\n")

    # QR chuyen khoan
    bank_bin = Config.get("bank_id", "")
    bank_account = Config.get("bank_account", "")
    account_holder = Config.get("account_holder", "")
    if bank_bin and bank_account and invoice.payment_method in ("transfer", "mixed"):
        try:
            p.text("=" * W + "\n")
            p.set(align="center")
            p.text("MA QR CHUYEN KHOAN\n")
            desc = f"TT {room_name}"
            transfer_amt = invoice.transfer_amount if invoice.payment_method == "mixed" else invoice.total_after_discount
            qr_data = _make_vietqr_payload(bank_bin, bank_account, transfer_amt, desc)
            p.qr(qr_data, native=True, size=6)
            p.set(align="left")
            if account_holder:
                p.text(f"CTK: {account_holder}\n")
            p.text(f"STK: {bank_account}\n")
            p.text(f"ST : {transfer_amt:,}d\n")
        except Exception:
            pass

    p.text("=" * W + "\n")
    p.set(align="center")
    p.text("Cam on quy khach!\n")
    p.text("Hen gap lai!\n")
    p.ln(4)
    p.cut()


# ── In phieu kiem tra (chua thanh toan) ───────────────────────────────────────

def print_check_bill(session, ip="", port=9100, printer_name=""):
    """In phieu kiem tra. printer_name -> Windows; ip -> Network."""
    if not ESCPOS_AVAILABLE:
        return False, "Thu vien python-escpos chua duoc cai dat."
    try:
        if printer_name:
            if not WIN32_AVAILABLE:
                return False, "win32print khong co san (chi chay tren Windows)."
            d = EscPosDummy()
            _print_check_content(d, session)
            _send_raw_to_windows_printer(printer_name, d.output)
        else:
            p = EscPosNetwork(ip, port, timeout=5)
            _print_check_content(p, session)
            p.close()
        return True, "In phieu kiem tra thanh cong."
    except ConnectionRefusedError:
        return False, f"Khong the ket noi may in tai {ip}:{port}."
    except Exception as e:
        return False, f"Loi may in: {str(e)}"


def _print_check_content(p, session):
    """Buoc 1 — PHIEU KIEM BILL: liet ke chi tiet, khach xac nhan, khong co QR."""
    from core.pricing import calculate_session_total

    W = 30
    now = timezone.now()
    room_name = session.room.name

    _print_shop_header(p, W, "PHIEU KIEM BILL")
    p.text(f"{'Phong: ' + room_name:^{W}}\n")
    p.text("-" * W + "\n")
    p.set(align="left")
    p.text(f"Gio    : {timezone.localtime(now).strftime('%H:%M %d/%m/%Y')}\n")
    p.text("=" * W + "\n")

    _print_items_section(p, W, session, now)
    p.text("-" * W + "\n")

    totals = calculate_session_total(session)
    p.set(bold=True)
    p.text(f"{'Dich vu:':<{W-12}}{totals['total_service']:>12,}d\n")
    p.text(f"{'Do an/uong:':<{W-12}}{totals['total_food']:>12,}d\n")
    if totals["total_outside"] > 0:
        p.text(f"{'Mua ngoai:':<{W-12}}{totals['total_outside']:>12,}d\n")
    p.text("=" * W + "\n")
    p.text("TAM TINH:\n")
    p.text(f"{totals['subtotal']:>{W-1},}d\n")
    p.set(bold=False)
    p.text("=" * W + "\n")
    p.set(align="center")
    p.text("Vui long xac nhan va bao nhan vien\n")
    p.ln(4)
    p.cut()


# ── In phieu tam tinh (co QR) ─────────────────────────────────────────────────

def print_temp_bill(session, discount_percent=0, ip="", port=9100, printer_name=""):
    """In phieu tam tinh + QR. printer_name -> Windows; ip -> Network."""
    if not ESCPOS_AVAILABLE:
        return False, "Thu vien python-escpos chua duoc cai dat."
    try:
        if printer_name:
            if not WIN32_AVAILABLE:
                return False, "win32print khong co san (chi chay tren Windows)."
            d = EscPosDummy()
            _print_temp_content(d, session, discount_percent)
            _send_raw_to_windows_printer(printer_name, d.output)
        else:
            p = EscPosNetwork(ip, port, timeout=5)
            _print_temp_content(p, session, discount_percent)
            p.close()
        return True, "In phieu tam tinh thanh cong."
    except ConnectionRefusedError:
        return False, f"Khong the ket noi may in tai {ip}:{port}."
    except Exception as e:
        return False, f"Loi may in: {str(e)}"


def _print_temp_content(p, session, discount_percent=0):
    """Buoc 2 — PHIEU TAM TINH: tong + giam gia + QR chuyen khoan."""
    from core.pricing import calculate_session_total
    from core.models import Config

    W = 30
    now = timezone.now()
    room_name = session.room.name
    totals = calculate_session_total(session)
    subtotal = totals["subtotal"]
    discount_amount = int(subtotal * discount_percent / 100)
    total_after_discount = subtotal - discount_amount

    _print_shop_header(p, W, "PHIEU TAM TINH")
    p.text(f"{'Phong: ' + room_name:^{W}}\n")
    p.text("-" * W + "\n")
    p.set(align="left")
    p.text(f"Gio    : {timezone.localtime(now).strftime('%H:%M %d/%m/%Y')}\n")
    p.text("=" * W + "\n")

    p.set(bold=False)
    p.text(f"{'Dich vu:':<{W-12}}{totals['total_service']:>12,}d\n")
    p.text(f"{'Do an/uong:':<{W-12}}{totals['total_food']:>12,}d\n")
    if totals["total_outside"] > 0:
        p.text(f"{'Mua ngoai:':<{W-12}}{totals['total_outside']:>12,}d\n")
    p.text("-" * W + "\n")
    p.set(bold=True)
    p.text(f"{'Tam tinh:':<{W-12}}{subtotal:>12,}d\n")
    if discount_percent > 0:
        label = f"Giam gia {discount_percent}%:"
        p.text(f"{label:<{W-12}}{-discount_amount:>12,}d\n")
    p.text("=" * W + "\n")
    p.text("TONG THANH TOAN:\n")
    p.text(f"{total_after_discount:>{W-1},}d\n")
    p.set(bold=False)

    bank_bin = Config.get("bank_id", "")
    bank_account = Config.get("bank_account", "")
    account_holder = Config.get("account_holder", "")
    if bank_bin and bank_account:
        try:
            p.text("=" * W + "\n")
            p.set(align="center")
            p.text("QUET MA QR CHUYEN KHOAN\n")
            desc = f"TT {room_name}"
            qr_data = _make_vietqr_payload(bank_bin, bank_account, total_after_discount, desc)
            p.qr(qr_data, native=True, size=6)
            p.set(align="left")
            if account_holder:
                p.text(f"CTK: {account_holder}\n")
            p.text(f"STK: {bank_account}\n")
            p.text(f"ST : {total_after_discount:,}d\n")
        except Exception:
            pass

    p.text("=" * W + "\n")
    p.set(align="center")
    p.text("Sau khi TT, bao nhan vien\n")
    p.text("de xuat hoa don chinh thuc.\n")
    p.ln(4)
    p.cut()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate(text, max_len):
    if len(text) > max_len:
        return text[:max_len - 2] + ".."
    return text


def get_invoice_text(invoice):
    """Tra ve noi dung hoa don dang text (dung de xem truoc tren web)."""
    from core.pricing import format_duration

    session = invoice.session
    lines = []

    lines.append("=" * 40)
    lines.append("           HOA DON KARAOKE")
    lines.append("=" * 40)
    lines.append(f"Phong     : {session.room.name}")
    lines.append(f"Thoi gian : {timezone.localtime(invoice.created_at).strftime('%d/%m/%Y %H:%M')}")
    lines.append("-" * 40)

    service_orders = session.get_all_service_orders()
    if service_orders.exists():
        lines.append("DICH VU:")
        for so in service_orders:
            end = so.ended_at or invoice.created_at
            dur = format_duration((end - so.started_at).total_seconds() / 60)
            cost = so.calculate_cost(at_time=invoice.created_at)
            lines.append(f"  {so.service_name} ({dur})")
            lines.append(f"  {'':>28}{cost:>8,}d")

    menu_items = [i for i in session.get_all_order_items() if i.item_type == "menu"]
    if menu_items:
        lines.append("DO AN/UONG:")
        for item in menu_items:
            lines.append(f"  {item.name} x{item.quantity}")
            lines.append(f"  {'':>28}{item.subtotal:>8,}d")

    outside_items = [i for i in session.get_all_order_items() if i.item_type == "outside"]
    if outside_items:
        lines.append("MUA NGOAI:")
        for item in outside_items:
            lines.append(f"  {item.name} x{item.quantity}")
            lines.append(f"  {'':>28}{item.subtotal:>8,}d")

    lines.append("-" * 40)
    lines.append(f"{'Tong cong:':<30}{invoice.subtotal:>8,}d")
    if invoice.discount_percent > 0:
        lines.append(f"{'Giam gia ' + str(invoice.discount_percent) + '%:':<30}{-invoice.discount_amount:>8,}d")
        lines.append(f"{'Sau giam gia:':<30}{invoice.total_after_discount:>8,}d")
    if invoice.tip > 0:
        lines.append(f"{'Tip:':<30}{invoice.tip:>8,}d")
    lines.append("=" * 40)
    lines.append(f"TONG THANH TOAN: {invoice.total_after_discount:>20,}d")
    lines.append("=" * 40)

    if invoice.payment_method == "cash":
        lines.append(f"Tien mat    : {invoice.cash_amount:,}d")
    elif invoice.payment_method == "transfer":
        lines.append(f"Chuyen khoan: {invoice.transfer_amount:,}d")
    else:
        lines.append(f"Tien mat    : {invoice.cash_amount:,}d")
        lines.append(f"Chuyen khoan: {invoice.transfer_amount:,}d")

    lines.append("=" * 40)
    lines.append("         Cam on quy khach!")

    return "\n".join(lines)
