from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_serviceorder_cancel"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="note",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
    ]
