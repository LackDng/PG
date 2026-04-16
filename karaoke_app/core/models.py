from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_STAFF = "staff"
    ROLE_CASHIER = "cashier"
    ROLE_ACCOUNTANT = "accountant"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Quản trị viên"),
        (ROLE_STAFF, "Nhân viên"),
        (ROLE_CASHIER, "Thu ngân"),
        (ROLE_ACCOUNTANT, "Kế toán"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF)
    display_name = models.CharField(max_length=100, blank=True)

    def get_display_name(self):
        return self.display_name or self.get_full_name() or self.username

    def can_apply_discount(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_CASHIER)

    def can_view_reports(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_ACCOUNTANT)

    def can_manage_admin(self):
        return self.role == self.ROLE_ADMIN

    def can_checkout(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_CASHIER)

    def __str__(self):
        return f"{self.get_display_name()} ({self.get_role_display()})"


class Room(models.Model):
    STATUS_AVAILABLE = "available"
    STATUS_OCCUPIED = "occupied"
    STATUS_CLEANING = "cleaning"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Trống"),
        (STATUS_OCCUPIED, "Đang sử dụng"),
        (STATUS_CLEANING, "Đang dọn"),
    ]

    name = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def get_active_session(self):
        return self.sessions.filter(status="open").first()


class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    base_price = models.IntegerField(default=500000, help_text="Giá gói chuẩn (VND)")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class MenuCategory(models.Model):
    name = models.CharField(max_length=50)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    category = models.ForeignKey(MenuCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.price:,}đ)"


class RoomSession(models.Model):
    STATUS_OPEN = "open"
    STATUS_PAID = "paid"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Đang mở"),
        (STATUS_PAID, "Đã thanh toán"),
    ]

    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="sessions")
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    opened_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="opened_sessions")
    note = models.TextField(blank=True)

    # Merge tracking: if this session is merged INTO another, record it here
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="merged_sessions"
    )

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.room.name} - {self.opened_at.strftime('%d/%m/%Y %H:%M')}"

    def _all_session_ids(self):
        """Return list of this session's id + all merged session ids."""
        ids = [self.pk]
        ids.extend(self.merged_sessions.values_list("pk", flat=True))
        return ids

    def get_all_service_orders(self):
        """Get service orders from this session and any merged sessions."""
        return ServiceOrder.objects.filter(session_id__in=self._all_session_ids())

    def get_all_order_items(self):
        """Get order items from this session and any merged sessions."""
        return OrderItem.objects.filter(session_id__in=self._all_session_ids())

    def calculate_total(self):
        from core.pricing import calculate_session_total
        return calculate_session_total(self)


class ServiceOrder(models.Model):
    STATUS_RUNNING = "running"
    STATUS_STOPPED = "stopped"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Đang chạy"),
        (STATUS_STOPPED, "Đã dừng"),
    ]

    session = models.ForeignKey(RoomSession, on_delete=models.CASCADE, related_name="service_orders")
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    service_name = models.CharField(max_length=100)  # snapshot name at order time
    base_price = models.IntegerField()  # snapshot price at order time
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="started_service_orders")

    class Meta:
        ordering = ["started_at"]

    def __str__(self):
        return f"{self.service_name} - {self.session}"

    def calculate_cost(self, at_time=None):
        from core.pricing import calculate_service_cost
        end = self.ended_at or at_time or timezone.now()
        return calculate_service_cost(self.started_at, end, self.base_price)

    def get_duration_minutes(self, at_time=None):
        end = self.ended_at or at_time or timezone.now()
        return int((end - self.started_at).total_seconds() / 60)


class OrderItem(models.Model):
    TYPE_MENU = "menu"
    TYPE_OUTSIDE = "outside"

    TYPE_CHOICES = [
        (TYPE_MENU, "Menu"),
        (TYPE_OUTSIDE, "Mua ngoài"),
    ]

    session = models.ForeignKey(RoomSession, on_delete=models.CASCADE, related_name="order_items")
    item_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=1)
    unit_price = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_order_items")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Invoice(models.Model):
    PAYMENT_CASH = "cash"
    PAYMENT_TRANSFER = "transfer"
    PAYMENT_MIXED = "mixed"

    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Tiền mặt"),
        (PAYMENT_TRANSFER, "Chuyển khoản"),
        (PAYMENT_MIXED, "Kết hợp"),
    ]

    DISCOUNT_CHOICES = [
        (0, "Không giảm giá"),
        (5, "5%"),
        (10, "10%"),
        (20, "20%"),
        (50, "50%"),
        (100, "100% (Miễn phí)"),
    ]

    session = models.OneToOneField(RoomSession, on_delete=models.PROTECT, related_name="invoice")
    total_service = models.IntegerField(default=0)
    total_food = models.IntegerField(default=0)
    total_outside = models.IntegerField(default=0)
    subtotal = models.IntegerField(default=0)
    discount_percent = models.IntegerField(default=0, choices=DISCOUNT_CHOICES)
    discount_amount = models.IntegerField(default=0)
    total_after_discount = models.IntegerField(default=0)
    tip = models.IntegerField(default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    cash_amount = models.IntegerField(default=0)
    transfer_amount = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_invoices")
    printer_ip = models.GenericIPAddressField(null=True, blank=True)
    printer_port = models.IntegerField(null=True, blank=True)
    printed = models.BooleanField(default=False)

    def __str__(self):
        return f"Hóa đơn #{self.pk} - {self.session}"


class Config(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        obj, _ = cls.objects.get_or_create(key=key)
        obj.value = str(value)
        obj.save()


class ActivityLog(models.Model):
    ACTION_OPEN_ROOM      = "open_room"
    ACTION_ADD_SERVICE    = "add_service"
    ACTION_STOP_SERVICE   = "stop_service"
    ACTION_ADD_FOOD       = "add_food"
    ACTION_ADD_OUTSIDE    = "add_outside"
    ACTION_REMOVE_ITEM    = "remove_item"
    ACTION_MERGE_TABLE    = "merge_table"
    ACTION_UNMERGE_TABLE  = "unmerge_table"
    ACTION_CHECKOUT       = "checkout"
    ACTION_DELETE_REVENUE = "delete_revenue"

    ACTION_CHOICES = [
        (ACTION_OPEN_ROOM,      "Mở phòng"),
        (ACTION_ADD_SERVICE,    "Thêm dịch vụ"),
        (ACTION_STOP_SERVICE,   "Dừng dịch vụ"),
        (ACTION_ADD_FOOD,       "Gọi đồ ăn/uống"),
        (ACTION_ADD_OUTSIDE,    "Thêm mua ngoài"),
        (ACTION_REMOVE_ITEM,    "Xóa món"),
        (ACTION_MERGE_TABLE,    "Gộp bàn"),
        (ACTION_UNMERGE_TABLE,  "Hủy gộp bàn"),
        (ACTION_CHECKOUT,       "Thanh toán"),
        (ACTION_DELETE_REVENUE, "Xóa doanh thu"),
    ]

    session     = models.ForeignKey(RoomSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action      = models.CharField(max_length=30, choices=ACTION_CHOICES)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="activity_logs")
    description = models.TextField()
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_action_display()}] {self.user} — {self.created_at:%d/%m %H:%M}"

    @classmethod
    def log(cls, action, user, description, session=None):
        cls.objects.create(action=action, user=user, description=description, session=session)
