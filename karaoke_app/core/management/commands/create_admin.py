from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import User


class Command(BaseCommand):
    help = "Tạo tài khoản admin mặc định"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="admin123")

    def _write(self, msg):
        try:
            self.stdout.write(msg)
        except Exception:
            pass

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        if User.objects.filter(username=username).exists():
            self._write(self.style.WARNING(f"Tai khoan '{username}' da ton tai."))
            return

        User.objects.create(
            username=username,
            display_name="Quan tri vien",
            password=make_password(password),
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self._write(self.style.SUCCESS(
            f"Da tao tai khoan admin: {username} / {password}"
        ))
