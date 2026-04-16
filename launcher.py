"""
Launcher cho Karaoke Manager Windows EXE.
Được đóng gói bằng PyInstaller.
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
    # Chạy từ exe — sys._MEIPASS là thư mục giải nén tạm
    BUNDLE_DIR = sys._MEIPASS
    # Thư mục chứa exe (có thể ghi được)
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BUNDLE_DIR

# Lưu DB vào %APPDATA%\KaraokeManager\ (luôn có quyền ghi)
APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "KaraokeManager"
)
os.makedirs(APP_DATA_DIR, exist_ok=True)

# ─── Cấu hình Django ─────────────────────────────────────────────────────────
DJANGO_APP_DIR = os.path.join(BUNDLE_DIR, "karaoke_app")
sys.path.insert(0, DJANGO_APP_DIR)

os.environ["DJANGO_SETTINGS_MODULE"] = "karaoke.settings"
os.environ["DB_DIR"]      = APP_DATA_DIR        # database.sqlite3 ở AppData
os.environ["STATIC_ROOT"] = os.path.join(BUNDLE_DIR, "karaoke_app", "staticfiles")
os.environ["DJANGO_DEBUG"] = "true"             # Cần để serve static files

PORT = 8000
URL  = f"http://127.0.0.1:{PORT}"

# ─── Kiểm tra port đã dùng chưa ──────────────────────────────────────────────
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
    print(f"[KaraokeManager] Mở trình duyệt: {URL}")
    webbrowser.open(URL)

# ─── Chạy server ─────────────────────────────────────────────────────────────
def run_server():
    from django.core.management import call_command
    print(f"[KaraokeManager] Khởi động server tại {URL}")
    print("[KaraokeManager] Nhấn Ctrl+C hoặc đóng cửa sổ này để thoát.\n")
    call_command("runserver", f"127.0.0.1:{PORT}", "--noreload")

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not is_port_free(PORT):
        print(f"[KaraokeManager] Port {PORT} đang được sử dụng.")
        print(f"[KaraokeManager] Mở trình duyệt: {URL}")
        webbrowser.open(URL)
        sys.exit(0)

    print("=" * 50)
    print("   KARAOKE MANAGER")
    print("=" * 50)

    setup_django()

    threading.Thread(target=open_browser, daemon=True).start()
    run_server()
