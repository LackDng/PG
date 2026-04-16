import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Frozen (PyInstaller exe) hay development? ────────────────────────────────
IS_FROZEN = getattr(sys, "frozen", False)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-karaoke-app-change-in-production"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() not in ("false", "0", "no")

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "karaoke.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]

WSGI_APPLICATION = "karaoke.wsgi.application"

# ─── Database ─────────────────────────────────────────────────────────────────
# Ưu tiên: biến môi trường DB_DIR > thư mục project
_db_dir = Path(os.environ.get("DB_DIR", str(BASE_DIR)))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _db_dir / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "core.User"
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

# ─── Static files ─────────────────────────────────────────────────────────────
STATIC_URL = "/static/"

if IS_FROZEN:
    # Khi chạy từ exe: serve từ staticfiles/ đã được collectstatic
    STATIC_ROOT = os.environ.get("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
    STATICFILES_DIRS = []
else:
    # Development: serve từ static/ source
    STATICFILES_DIRS = [BASE_DIR / "static"]
    STATIC_ROOT = os.environ.get("STATIC_ROOT", str(BASE_DIR / "staticfiles"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
