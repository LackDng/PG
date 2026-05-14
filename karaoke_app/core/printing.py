"""
In hoa don nhiet qua ESC/POS Network/TCP hoac may in Windows.
Yeu cau: python-escpos, pywin32 (Windows only)
"""

import unicodedata
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


# ── Chuyen tieng Viet sang ASCII cho may in nhiet ────────────────────────────

_VI_EXTRA = str.maketrans({
    'đ': 'd', 'Đ': 'D',
    '‘': "'", '’': "'", '“': '"', '”': '"',
})


def vi(text):
    """Chuyen ki tu tieng Viet/Unicode thanh ASCII thuan de may in nhiet hieu duoc."""
    text = str(text).translate(_VI_EXTRA)
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _t(p, text):
    """Gui text ra may in duoi dang raw ASCII bytes, bo qua escpos encoding."""
    p._raw(vi(str(text)).encode('ascii', 'replace'))


def _paper_width():
    """Tra ve so ky tu tren 1 dong theo kho giay: 80mm->42, 58mm->32."""
    from core.models import Config
    return 42 if Config.get("paper_width", "80") == "80" else 32


def _truncate(text, max_len):
    if len(text) > max_len:
        return text[:max_len - 2] + ".."
    return text


def _center_truncate(text, width):
    if len(text) > width:
        text = text[:width - 2] + ".."
    return text.center(width)


# ── Windows printer helpers ───────────────────────────────────────────────────

def get_windows_printers():
    """Tra ve danh sach ten may in dang cai tren Windows."""
    if not WIN32_AVAILABLE:
        return []
    try:
        flags = _win32print.PRINTER_ENUM_LOCAL | _win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in _win32print.EnumPrinters(flags)]
    except Exception:
        return []


def get_default_windows_printer():
    """Tra ve ten may in mac dinh cua Windows."""
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

    desc_clean = vi(description or "")[:25]
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

    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF

    return payload + f"{crc:04X}"


# ── Shared print helpers ──────────────────────────────────────────────────────

def _print_shop_header(p, W, title):
    """In tieu de chung: ten cua hang, dia chi, hotline, tieu de phieu."""
    from core.models import Config
    shop_name    = vi(Config.get("shop_name", "KARAOKE"))
    shop_address = vi(Config.get("shop_address", ""))
    shop_phone   = Config.get("shop_phone", "")

    p.set(align="center", bold=True)
    _t(p, f"{shop_name.upper()}\n")
    p.set(bold=False)
    if shop_address:
        _t(p, f"{_center_truncate(shop_address, W)}\n")
    if shop_phone:
        _t(p, f"Hotline: {shop_phone}\n")
    _t(p, "-" * W + "\n")
    p.set(bold=True)
    _t(p, f"{title.center(W)}\n")
    p.set(bold=False)


def _print_items_section(p, W, session, ref_time):
    """In phan chi tiet hang hoa theo dang bang."""
    from core.pricing import format_duration

    COL_AMT  = 10
    COL_NAME = W - COL_AMT

    p.set(bold=True)
    _t(p, f"{'TEN HANG HOA':<{COL_NAME}}{'T.TIEN':>{COL_AMT}}\n")
    p.set(bold=False)
    _t(p, "-" * W + "\n")

    for so in session.get_all_service_orders().exclude(status="cancelled"):
        end = so.ended_at or ref_time
        dur = format_duration((end - so.started_at).total_seconds() / 60)
        cost = so.calculate_cost(at_time=ref_time)
        start_str = timezone.localtime(so.started_at).strftime("%H:%M")
        end_str   = timezone.localtime(end).strftime("%H:%M")
        name = _truncate(vi(so.service_name), COL_NAME)
        amt_str = f"{cost:,}d"
        _t(p, f"{name:<{COL_NAME}}{amt_str:>{COL_AMT}}\n")
        _t(p, f"  {start_str}-{end_str} {dur}\n")

    for item in session.get_all_order_items():
        name = _truncate(vi(item.name), COL_NAME)
        amt_str = f"{item.subtotal:,}d"
        _t(p, f"{name:<{COL_NAME}}{amt_str:>{COL_AMT}}\n")
        _t(p, f"  {item.unit_price:,}d x {item.quantity}\n")


def _print_qr_section(p, W, bank_bin, bank_account, account_holder, amount, room_name):
    """In phan QR chuyen khoan (dung chung cho ca invoice va tam tinh)."""
    try:
        _t(p, "=" * W + "\n")
        p.set(align="center")
        _t(p, "QUET MA QR CHUYEN KHOAN\n")
        desc = f"TT {vi(room_name)}"
        qr_data = _make_vietqr_payload(bank_bin, account_no=bank_account,
                                       amount=amount, description=desc)
        p.qr(qr_data, native=True, size=6)
        p.set(align="left")
        if account_holder:
            _t(p, f"CTK: {vi(account_holder)}\n")
        _t(p, f"STK: {bank_account}\n")
        _t(p, f"ST : {amount:,}d\n")
    except Exception:
        pass


# ── In hoa don chinh thuc ─────────────────────────────────────────────────────

def print_invoice(invoice, ip="", port=9100, printer_name=""):
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


def _print_invoice_content(p, invoice):
    from core.models import Config

    W        = _paper_width()
    COL_AMT  = 12
    COL_NAME = W - COL_AMT

    session   = invoice.session
    room_name = session.room.name
    now       = timezone.localtime(invoice.created_at)
    opened    = timezone.localtime(session.opened_at)
    cashier   = vi(invoice.created_by.get_display_name()) if invoice.created_by else ""

    _print_shop_header(p, W, "HOA DON THANH TOAN")
    p.set(align="center")
    _t(p, f"Phong: {vi(room_name)}\n")
    _t(p, "-" * W + "\n")

    p.set(align="left")
    _t(p, f"So HD  : #{invoice.id}\n")
    _t(p, f"Gio vao: {opened.strftime('%H:%M %d/%m/%Y')}\n")
    _t(p, f"Gio ra : {now.strftime('%H:%M %d/%m/%Y')}\n")
    _t(p, f"TN     : {cashier}\n")
    _t(p, "=" * W + "\n")

    _print_items_section(p, W, session, invoice.created_at)
    _t(p, "-" * W + "\n")

    p.set(bold=True)
    _t(p, f"{'Dich vu:':<{COL_NAME}}{invoice.total_service:>{COL_AMT},}d\n")
    _t(p, f"{'Do an/uong:':<{COL_NAME}}{invoice.total_food:>{COL_AMT},}d\n")
    if invoice.total_outside > 0:
        _t(p, f"{'Mua ngoai:':<{COL_NAME}}{invoice.total_outside:>{COL_AMT},}d\n")
    _t(p, f"{'Tong cong:':<{COL_NAME}}{invoice.subtotal:>{COL_AMT},}d\n")
    if invoice.discount_percent > 0:
        label = f"Giam {invoice.discount_percent}%:"
        _t(p, f"{label:<{COL_NAME}}{-invoice.discount_amount:>{COL_AMT},}d\n")
        _t(p, f"{'Sau giam:':<{COL_NAME}}{invoice.total_after_discount:>{COL_AMT},}d\n")
    p.set(bold=False)
    if invoice.tip > 0:
        _t(p, f"{'Tip:':<{COL_NAME}}{invoice.tip:>{COL_AMT},}d\n")

    _t(p, "=" * W + "\n")
    p.set(bold=True, align="center")
    _t(p, "TONG THANH TOAN:\n")
    _t(p, f"{invoice.total_after_discount:,}d\n")
    p.set(bold=False, align="left")

    _t(p, "-" * W + "\n")
    if invoice.payment_method == "cash":
        _t(p, f"{'Tien mat:':<{COL_NAME}}{invoice.cash_amount:>{COL_AMT},}d\n")
    elif invoice.payment_method == "transfer":
        _t(p, f"{'Chuyen khoan:':<{COL_NAME}}{invoice.transfer_amount:>{COL_AMT},}d\n")
    else:
        _t(p, f"{'Tien mat:':<{COL_NAME}}{invoice.cash_amount:>{COL_AMT},}d\n")
        _t(p, f"{'Chuyen khoan:':<{COL_NAME}}{invoice.transfer_amount:>{COL_AMT},}d\n")

    bank_bin       = Config.get("bank_id", "")
    bank_account   = Config.get("bank_account", "")
    account_holder = Config.get("account_holder", "")
    if bank_bin and bank_account:
        qr_amount = invoice.transfer_amount if invoice.payment_method == "mixed" else invoice.total_after_discount
        _print_qr_section(p, W, bank_bin, bank_account, account_holder, qr_amount, room_name)

    if invoice.note:
        _t(p, "=" * W + "\n")
        p.set(align="left")
        _t(p, f"Ghi chu: {vi(invoice.note)}\n")

    _t(p, "=" * W + "\n")
    p.set(align="center")
    _t(p, "Cam on quy khach!\n")
    _t(p, "Hen gap lai!\n")
    p.ln(4)
    p.cut()


# ── In phieu kiem tra (chua thanh toan) ───────────────────────────────────────

def print_check_bill(session, ip="", port=9100, printer_name=""):
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
    from core.pricing import calculate_session_total

    W        = _paper_width()
    COL_AMT  = 12
    COL_NAME = W - COL_AMT
    now      = timezone.now()

    _print_shop_header(p, W, "PHIEU KIEM BILL")
    p.set(align="center")
    _t(p, f"Phong: {vi(session.room.name)}\n")
    _t(p, "-" * W + "\n")
    p.set(align="left")
    _t(p, f"Gio    : {timezone.localtime(now).strftime('%H:%M %d/%m/%Y')}\n")
    _t(p, "=" * W + "\n")

    _print_items_section(p, W, session, now)
    _t(p, "-" * W + "\n")

    totals = calculate_session_total(session)
    p.set(bold=True)
    _t(p, f"{'Dich vu:':<{COL_NAME}}{totals['total_service']:>{COL_AMT},}d\n")
    _t(p, f"{'Do an/uong:':<{COL_NAME}}{totals['total_food']:>{COL_AMT},}d\n")
    if totals["total_outside"] > 0:
        _t(p, f"{'Mua ngoai:':<{COL_NAME}}{totals['total_outside']:>{COL_AMT},}d\n")
    _t(p, "=" * W + "\n")
    p.set(align="center")
    _t(p, "TAM TINH:\n")
    _t(p, f"{totals['subtotal']:,}d\n")
    p.set(bold=False)
    _t(p, "=" * W + "\n")
    p.set(align="center")
    _t(p, "Vui long xac nhan va bao nhan vien\n")
    p.ln(4)
    p.cut()


# ── In phieu tam tinh (co QR) ─────────────────────────────────────────────────

def print_temp_bill(session, discount_percent=0, ip="", port=9100, printer_name=""):
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
    from core.pricing import calculate_session_total
    from core.models import Config

    W        = _paper_width()
    COL_AMT  = 12
    COL_NAME = W - COL_AMT
    now      = timezone.now()
    room_name = session.room.name
    totals   = calculate_session_total(session)
    subtotal = totals["subtotal"]
    discount_amount = int(subtotal * discount_percent / 100)
    total_after_discount = subtotal - discount_amount

    _print_shop_header(p, W, "PHIEU TAM TINH")
    p.set(align="center")
    _t(p, f"Phong: {vi(room_name)}\n")
    _t(p, "-" * W + "\n")
    p.set(align="left")
    _t(p, f"Gio    : {timezone.localtime(now).strftime('%H:%M %d/%m/%Y')}\n")
    _t(p, "=" * W + "\n")

    _t(p, f"{'Dich vu:':<{COL_NAME}}{totals['total_service']:>{COL_AMT},}d\n")
    _t(p, f"{'Do an/uong:':<{COL_NAME}}{totals['total_food']:>{COL_AMT},}d\n")
    if totals["total_outside"] > 0:
        _t(p, f"{'Mua ngoai:':<{COL_NAME}}{totals['total_outside']:>{COL_AMT},}d\n")
    _t(p, "-" * W + "\n")
    p.set(bold=True)
    _t(p, f"{'Tam tinh:':<{COL_NAME}}{subtotal:>{COL_AMT},}d\n")
    if discount_percent > 0:
        label = f"Giam {discount_percent}%:"
        _t(p, f"{label:<{COL_NAME}}{-discount_amount:>{COL_AMT},}d\n")
    _t(p, "=" * W + "\n")
    p.set(align="center")
    _t(p, "TONG THANH TOAN:\n")
    _t(p, f"{total_after_discount:,}d\n")
    p.set(bold=False, align="left")

    bank_bin       = Config.get("bank_id", "")
    bank_account   = Config.get("bank_account", "")
    account_holder = Config.get("account_holder", "")
    if bank_bin and bank_account:
        _print_qr_section(p, W, bank_bin, bank_account, account_holder,
                          total_after_discount, room_name)

    _t(p, "=" * W + "\n")
    p.set(align="center")
    _t(p, "Sau khi TT, bao nhan vien\n")
    _t(p, "de xuat hoa don chinh thuc.\n")
    p.ln(4)
    p.cut()


# ── Text preview (hien thi tren web) ─────────────────────────────────────────

def get_invoice_text(invoice):
    """Tra ve noi dung hoa don dang text (dung de xem truoc tren web)."""
    from core.pricing import format_duration

    session = invoice.session
    lines = []

    lines.append("=" * 42)
    lines.append("           HOA DON KARAOKE")
    lines.append("=" * 42)
    lines.append(f"Phong     : {session.room.name}")
    lines.append(f"Thoi gian : {timezone.localtime(invoice.created_at).strftime('%d/%m/%Y %H:%M')}")
    lines.append("-" * 42)

    service_orders = session.get_all_service_orders().exclude(status="cancelled")
    if service_orders.exists():
        lines.append("DICH VU:")
        for so in service_orders:
            end = so.ended_at or invoice.created_at
            dur = format_duration((end - so.started_at).total_seconds() / 60)
            cost = so.calculate_cost(at_time=invoice.created_at)
            lines.append(f"  {so.service_name} ({dur})")
            lines.append(f"  {'':>30}{cost:>8,}d")

    menu_items = [i for i in session.get_all_order_items() if i.item_type == "menu"]
    if menu_items:
        lines.append("DO AN/UONG:")
        for item in menu_items:
            lines.append(f"  {item.name} x{item.quantity}")
            lines.append(f"  {'':>30}{item.subtotal:>8,}d")

    outside_items = [i for i in session.get_all_order_items() if i.item_type == "outside"]
    if outside_items:
        lines.append("MUA NGOAI:")
        for item in outside_items:
            lines.append(f"  {item.name} x{item.quantity}")
            lines.append(f"  {'':>30}{item.subtotal:>8,}d")

    lines.append("-" * 42)
    lines.append(f"{'Tong cong:':<32}{invoice.subtotal:>8,}d")
    if invoice.discount_percent > 0:
        lines.append(f"{'Giam gia ' + str(invoice.discount_percent) + '%:':<32}{-invoice.discount_amount:>8,}d")
        lines.append(f"{'Sau giam gia:':<32}{invoice.total_after_discount:>8,}d")
    if invoice.tip > 0:
        lines.append(f"{'Tip:':<32}{invoice.tip:>8,}d")
    lines.append("=" * 42)
    lines.append(f"TONG THANH TOAN: {invoice.total_after_discount:,}d")
    lines.append("=" * 42)

    if invoice.payment_method == "cash":
        lines.append(f"Tien mat    : {invoice.cash_amount:,}d")
    elif invoice.payment_method == "transfer":
        lines.append(f"Chuyen khoan: {invoice.transfer_amount:,}d")
    else:
        lines.append(f"Tien mat    : {invoice.cash_amount:,}d")
        lines.append(f"Chuyen khoan: {invoice.transfer_amount:,}d")

    if invoice.note:
        lines.append(f"Ghi chu: {invoice.note}")
    lines.append("=" * 42)
    lines.append("         Cam on quy khach!")

    return "\n".join(lines)
