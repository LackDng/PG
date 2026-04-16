# Hướng dẫn triển khai Karaoke Manager

## Yêu cầu duy nhất: Docker Desktop

Tải Docker tại: https://www.docker.com/products/docker-desktop/

---

## Triển khai lần đầu

```bash
# 1. Clone hoặc copy thư mục project về máy
cd /path/to/PG

# 2. Build và chạy (chỉ cần 1 lệnh)
docker compose up -d --build

# 3. Mở trình duyệt tại
http://localhost:8000

# Tài khoản mặc định: admin / admin123
```

---

## Cấu hình (tuỳ chọn)

Sửa file `docker-compose.yml` trước khi chạy:

```yaml
environment:
  DJANGO_ADMIN_USERNAME: admin          # Tên đăng nhập admin
  DJANGO_ADMIN_PASSWORD: matkhau_manh  # Đổi mật khẩu này!
  DJANGO_SECRET_KEY: "chuoi-bi-mat-dai" # Đổi key này trong production!
  TZ: Asia/Ho_Chi_Minh
```

---

## Các lệnh hữu ích

```bash
# Xem logs
docker compose logs -f

# Dừng ứng dụng
docker compose down

# Dừng và XÓA dữ liệu (cẩn thận!)
docker compose down -v

# Cập nhật sau khi thay đổi code
docker compose up -d --build

# Backup database
docker compose exec karaoke cat /data/db/db.sqlite3 > backup.sqlite3
```

---

## Dữ liệu bền vững

Dữ liệu được lưu trong Docker volumes:
- `karaoke_db` — SQLite database
- `karaoke_static` — Static files

Khi `docker compose down` (không có `-v`), dữ liệu vẫn được giữ nguyên.

---

## Triển khai nhiều máy / nhiều quán

Mỗi máy chỉ cần:
1. Cài Docker Desktop
2. Copy thư mục project
3. Chạy `docker compose up -d --build`

Dữ liệu của mỗi nơi độc lập với nhau.
