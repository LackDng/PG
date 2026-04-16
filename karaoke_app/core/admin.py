from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Room, ServiceType, MenuItem, MenuCategory, RoomSession, ServiceOrder, OrderItem, Invoice, Config


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "display_name", "role", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Thông tin thêm", {"fields": ("role", "display_name")}),
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "is_active", "sort_order")


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "base_price", "is_active", "sort_order")


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active")


admin.site.register(MenuCategory)
admin.site.register(RoomSession)
admin.site.register(ServiceOrder)
admin.site.register(OrderItem)
admin.site.register(Invoice)
admin.site.register(Config)
