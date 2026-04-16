from django.urls import path
from core.views import auth, rooms, payment, reports, admin_views

urlpatterns = [
    # Auth
    path("login/", auth.login_view, name="login"),
    path("logout/", auth.logout_view, name="logout"),

    # Dashboard
    path("", rooms.dashboard, name="dashboard"),

    # Rooms
    path("rooms/<int:room_id>/", rooms.room_detail, name="room_detail"),
    path("rooms/<int:room_id>/open/", rooms.open_room, name="open_room"),
    path("rooms/<int:room_id>/cleaning/", rooms.set_room_cleaning, name="set_room_cleaning"),
    path("rooms/<int:room_id>/available/", rooms.set_room_available, name="set_room_available"),
    path("rooms/<int:room_id>/status-api/", rooms.api_room_status, name="api_room_status"),

    # Services
    path("sessions/<int:session_id>/add-service/", rooms.add_service_order, name="add_service_order"),
    path("service-orders/<int:order_id>/stop/", rooms.stop_service_order, name="stop_service_order"),

    # Order items
    path("sessions/<int:session_id>/add-menu/", rooms.add_menu_item, name="add_menu_item"),
    path("sessions/<int:session_id>/add-outside/", rooms.add_outside_item, name="add_outside_item"),
    path("order-items/<int:item_id>/remove/", rooms.remove_order_item, name="remove_order_item"),

    # Table management
    path("merge-table/", rooms.merge_table, name="merge_table"),
    path("sessions/<int:session_id>/unmerge/", rooms.unmerge_table, name="unmerge_table"),

    # Payment
    path("sessions/<int:session_id>/checkout/", payment.checkout_view, name="checkout"),
    path("invoices/<int:invoice_id>/", payment.invoice_detail, name="invoice_detail"),
    path("invoices/<int:invoice_id>/reprint/", payment.reprint_invoice, name="reprint_invoice"),

    # Reports
    path("reports/daily/", reports.daily_report, name="daily_report"),

    # Admin panel
    path("admin-panel/rooms/", admin_views.manage_rooms, name="manage_rooms"),
    path("admin-panel/rooms/add/", admin_views.add_room, name="add_room"),
    path("admin-panel/rooms/<int:room_id>/edit/", admin_views.edit_room, name="edit_room"),

    path("admin-panel/services/", admin_views.manage_services, name="manage_services"),
    path("admin-panel/services/add/", admin_views.add_service, name="add_service"),
    path("admin-panel/services/<int:service_id>/edit/", admin_views.edit_service, name="edit_service"),

    path("admin-panel/menu/", admin_views.manage_menu, name="manage_menu"),
    path("admin-panel/menu/add-category/", admin_views.add_category, name="add_category"),
    path("admin-panel/menu/add-item/", admin_views.add_menu_item_admin, name="add_menu_item_admin"),
    path("admin-panel/menu/<int:item_id>/edit/", admin_views.edit_menu_item, name="edit_menu_item"),

    path("admin-panel/users/", admin_views.manage_users, name="manage_users"),
    path("admin-panel/users/add/", admin_views.add_user, name="add_user"),
    path("admin-panel/users/<int:user_id>/edit/", admin_views.edit_user, name="edit_user"),

    path("admin-panel/config/", admin_views.system_config, name="system_config"),
]
