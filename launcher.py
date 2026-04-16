"""
Launcher cho Karaoke Manager Windows EXE.
Được đóng gói bằng PyInstaller.

Server lắng nghe trên 0.0.0.0 → các máy khác trong LAN có thể truy cập
qua địa chỉ IP của máy chủ, ví dụ: http://192.168.1.100:8000
"""
import sys
import os
import threading
import webbrowser
import time
import socket

# ─── Xác định đường dẫn ─────────────────────────────────────────────────────
IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    BUNDLE_DIR = sys._MEIPASS
    EXE_DIR    = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR    = BUNDLE_DIR

# Lưu DB vào %APPDATA%\KaraokeManager\
APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "KaraokeManager"
)
os.makedirs(APP_DATA_DIR, exist_ok=True)

# ─── Cấu hình Django ─────────────────────────────────────────────────────────
DJANGO_APP_DIR = os.path.join(BUNDLE_DIR, "karaoke_app")
sys.path.insert(0, DJANGO_APP_DIR)

os.environ["DJANGO_SETTINGS_MODULE"] = "karaoke.settings"
os.environ["DB_DIR"]      = APP_DATA_DIR
os.environ["STATIC_ROOT"] = os.path.join(BUNDLE_DIR, "karaoke_app", "staticfiles")
os.environ["DJANGO_DEBUG"] = "true"

PORT       = 8000
LOCAL_URL  = f"http://127.0.0.1:{PORT}"      # trình duyệt trên máy chủ


def get_local_ip():
    """Lấy địa chỉ IP LAN của máy này."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


# ─── Kiểm tra port ───────────────────────────────────────────────────────────
def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


# ─── Khởi tạo database ───────────────────────────────────────────────────────
def setup_django():
    import django
    django.setup()
    from django.core.management import call_command
    print("[KaraokeManager] Kiểm tra cơ sở dữ liệu...")
    call_command("migrate", "--noinput", verbosity=0)
    call_command(
        "create_admin",
        "--username", os.environ.get("ADMIN_USER", "admin"),
        "--password", os.environ.get("ADMIN_PASS", "admin123"),
    )


# ─── Mở trình duyệt ──────────────────────────────────────────────────────────
def open_browser():
    time.sleep(1.8)
    webbrowser.open(LOCAL_URL)


# ─── Chạy server ─────────────────────────────────────────────────────────────
def run_server():
    from django.core.management import call_command
    # 0.0.0.0 = lắng nghe trên tất cả network interfaces (LAN + localhost)
    call_command("runserver", f"0.0.0.0:{PORT}", "--noreload")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not is_port_free(PORT):
        print(f"[KaraokeManager] Port {PORT} đang được dùng — mở trình duyệt.")
        webbrowser.open(LOCAL_URL)
        sys.exit(0)

    lan_ip   = get_local_ip()
    lan_url  = f"http://{lan_ip}:{PORT}"

    print("=" * 55)
    print("   KARAOKE MANAGER")
    print("=" * 55)
    print(f"  Máy chủ này  : {LOCAL_URL}")
    print(f"  Máy khác LAN : {lan_url}")
    print("=" * 55)
    print("  Lần đầu đăng nhập: admin / admin123")
    print("  Đóng cửa sổ này để tắt server.")
    print("=" * 55)
    print()
    print("  LƯU Ý: Nếu máy khác không vào được, hãy cho phép")
    print("  KaraokeManager qua Windows Firewall khi được hỏi.")
    print()

    setup_django()

    threading.Thread(target=open_browser, daemon=True).start()
    run_server()
