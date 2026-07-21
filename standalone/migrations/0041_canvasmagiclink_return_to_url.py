from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0040_canvasuseridentity_canvascourselink_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="canvasmagiclink",
            name="return_to_url",
            field=models.URLField(blank=True, max_length=2000),
        ),
    ]
