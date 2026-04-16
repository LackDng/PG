#!/bin/sh
set -e

export DB_DIR="${DB_DIR:-/data/db}"
export STATIC_ROOT="${STATIC_ROOT:-/data/static}"

echo "==> Chạy migrations..."
python manage.py migrate --noinput

echo "==> Thu thập static files..."
python manage.py collectstatic --noinput --clear

# Tạo admin nếu chưa có
ADMIN_USER="${DJANGO_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${DJANGO_ADMIN_PASSWORD:-admin123}"
echo "==> Kiểm tra tài khoản admin '$ADMIN_USER'..."
python manage.py create_admin --username "$ADMIN_USER" --password "$ADMIN_PASS" || true

echo "==> Khởi động server tại 0.0.0.0:8000..."
exec python manage.py runserver 0.0.0.0:8000
