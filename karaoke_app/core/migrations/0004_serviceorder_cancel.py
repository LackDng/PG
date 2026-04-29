from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_cancel_room"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceorder",
            name="cancel_reason",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="serviceorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("running", "Đang chạy"),
                    ("stopped", "Đã dừng"),
                    ("cancelled", "Đã hủy"),
                ],
                default="running",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="activitylog",
            name="action",
            field=models.CharField(
                choices=[
                    ("open_room", "Mở phòng"),
                    ("cancel_room", "Hủy phòng"),
                    ("add_service", "Thêm dịch vụ"),
                    ("stop_service", "Dừng dịch vụ"),
                    ("cancel_service", "Hủy dịch vụ"),
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
