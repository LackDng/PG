"""
Launcher cho Karaoke Manager Windows EXE.
Duoc dong goi bang PyInstaller voi console=False (an cua so CMD).
"""
import sys
import os
import threading
import webbrowser
import time
import socket
import traceback
import ctypes

# ── Xac dinh duong dan ────────────────────────────────────────────────────────
IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    BUNDLE_DIR = sys._MEIPASS
    EXE_DIR    = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR    = BUNDLE_DIR

# Luu DB + log vao %APPDATA%\KaraokeManager\
APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "KaraokeManager"
)
os.makedirs(APP_DATA_DIR, exist_ok=True)

LOG_FILE = os.path.join(APP_DATA_DIR, "startup.log")

# ── Redirect stdout/stderr sang log file khi chay o windowed mode ────────────
# console=False khien sys.stdout/stderr = None, Django se crash khi ghi output.
# Mo log file va gan vao sys.stdout/stderr de moi output deu vao file log.
try:
    _log_stream = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
    sys.stdout = _log_stream
    sys.stderr = _log_stream
except Exception:
    pass


def log(msg):
    """Ghi dong thong bao vao file log."""
    try:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def _msgbox(title, msg, icon=0x10):
    """Hien thi hop thoai Windows (MB_OK | icon). Khong can console."""
    try:
        ctypes.windll.user32.MessageBoxW(0, msg, title, icon | 0x0)
    except Exception:
        pass


def fatal(msg, exc=None):
    """Hien thi loi qua hop thoai Windows, ghi log, thoat."""
    full_log = "\n".join([
        "",
        "=" * 60,
        "  LOI KHOI DONG - STARTUP ERROR",
        "=" * 60,
        msg,
    ])
    if exc:
        full_log += "\n\n" + traceback.format_exc()
    full_log += f"\n\n  Chi tiet loi duoc luu tai:\n  {LOG_FILE}"
    log(full_log)
    _msgbox(
        "KaraokeManager - Loi khoi dong",
        f"{msg}\n\nXem chi tiet tai:\n{LOG_FILE}",
        icon=0x10,   # MB_ICONERROR
    )
    sys.exit(1)


# ── Ghi thong tin mo dau vao log ─────────────────────────────────────────────
log(f"KaraokeManager startup — Python {sys.version}")
log(f"IS_FROZEN={IS_FROZEN}")
log(f"BUNDLE_DIR={BUNDLE_DIR}")
log(f"EXE_DIR={EXE_DIR}")
log(f"APP_DATA_DIR={APP_DATA_DIR}")
log("")

# ── Cau hinh Django ───────────────────────────────────────────────────────────
DJANGO_APP_DIR = os.path.join(BUNDLE_DIR, "karaoke_app")

if not os.path.isdir(DJANGO_APP_DIR):
    fatal(
        f"Khong tim thay thu muc Django app:\n  {DJANGO_APP_DIR}\n\n"
        "Hay dam bao chay dung file KaraokeManager.exe trong thu muc goc."
    )

sys.path.insert(0, DJANGO_APP_DIR)

os.environ["DJANGO_SETTINGS_MODULE"] = "karaoke.settings"
os.environ["DB_DIR"]      = APP_DATA_DIR
os.environ["STATIC_ROOT"] = os.path.join(BUNDLE_DIR, "karaoke_app", "staticfiles")
os.environ["DJANGO_DEBUG"] = "false"

PORT      = 8000
LOCAL_URL = f"http://127.0.0.1:{PORT}"


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _call(cmd, *args, **kwargs):
    """Goi management command, output duoc ghi vao log file."""
    from django.core.management import call_command
    call_command(cmd, *args, **kwargs)


def setup_django():
    log("[1/3] Khoi tao Django...")
    try:
        import django
        django.setup()
    except Exception as e:
        fatal("Khong the khoi tao Django. Kiem tra cai dat.", e)

    log("[2/3] Chay migrations...")
    try:
        _call("migrate", "--noinput", verbosity=0)
    except Exception as e:
        fatal("Migration that bai.", e)

    log("[3/3] Kiem tra tai khoan admin...")
    try:
        _call(
            "create_admin",
            "--username", os.environ.get("ADMIN_USER", "admin"),
            "--password", os.environ.get("ADMIN_PASS", "admin123"),
        )
    except Exception as e:
        fatal("Tao admin that bai.", e)


def open_browser():
    time.sleep(2.0)
    try:
        webbrowser.open(LOCAL_URL)
    except Exception:
        pass


def run_server():
    try:
        from django.core.management import call_command
        call_command("runserver", f"0.0.0.0:{PORT}", "--noreload")
    except Exception as e:
        fatal("Server dung bat ngo.", e)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not is_port_free(PORT):
        log(f"[KaraokeManager] Port {PORT} da duoc dung — mo trinh duyet.")
        webbrowser.open(LOCAL_URL)
        sys.exit(0)

    lan_ip  = get_local_ip()
    lan_url = f"http://{lan_ip}:{PORT}"

    log("=" * 55)
    log("   KARAOKE MANAGER")
    log("=" * 55)
    log(f"  May chu nay  : {LOCAL_URL}")
    log(f"  May khac LAN : {lan_url}")
    log("=" * 55)
    log("  Lan dau dang nhap: admin / admin123")
    log("=" * 55)
    log(f"  Log file: {LOG_FILE}")
    log("")

    setup_django()

    threading.Thread(target=open_browser, daemon=True).start()
    log("Server dang chay. Mo trinh duyet tai " + LOCAL_URL)
    run_server()
