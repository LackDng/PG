from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import User


class Command(BaseCommand):
    help = "Tạo tài khoản admin mặc định"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="admin123")

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Tài khoản '{username}' đã tồn tại."))
            return

        User.objects.create(
            username=username,
            display_name="Quản trị viên",
            password=make_password(password),
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Đã tạo tài khoản admin: {username} / {password}"
        ))
