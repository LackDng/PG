# ── Stage build ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=karaoke.settings

WORKDIR /app

# Cài dependencies hệ thống (cần cho python-escpos và Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libusb-1.0-0 \
    libcups2 \
    && rm -rf /var/lib/apt/lists/*

# Cài Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code
COPY karaoke_app/ .

# Tạo thư mục data (SQLite DB và static files)
RUN mkdir -p /data/static /data/db

# Script khởi động
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
