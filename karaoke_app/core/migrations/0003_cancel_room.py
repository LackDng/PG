from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_activitylog"),
    ]

    operations = [
        # Add "cancelled" choice to RoomSession.status
        migrations.AlterField(
            model_name="roomsession",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Đang mở"),
                    ("paid", "Đã thanh toán"),
                    ("cancelled", "Đã hủy"),
                ],
                default="open",
                max_length=20,
            ),
        ),
        # Add "cancel_room" choice to ActivityLog.action
        migrations.AlterField(
            model_name="activitylog",
            name="action",
            field=models.CharField(
                choices=[
                    ("open_room", "Mở phòng"),
                    ("cancel_room", "Hủy phòng"),
                    ("add_service", "Thêm dịch vụ"),
                    ("stop_service", "Dừng dịch vụ"),
                    ("add_food", "Gọi đồ ăn/uống"),
                    ("add_outside", "Thêm mua ngoài"),
                    ("remove_item", "Xóa món"),
                    ("merge_table", "Gộp bàn"),
                    ("unmerge_table", "Hủy gộp bàn"),
                    ("checkout", "Thanh toán"),
                    ("delete_revenue", "Xóa doanh thu"),
                ],
                max_length=30,
            ),
        ),
    ]
