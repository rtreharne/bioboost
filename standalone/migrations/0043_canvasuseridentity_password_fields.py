from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0042_canvascourselink_canvas_page_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="canvasuseridentity",
            name="password_hash",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="canvasuseridentity",
            name="password_set_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="canvasuseridentity",
            name="password_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
