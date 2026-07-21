from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0041_canvasmagiclink_return_to_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="canvascourselink",
            name="canvas_page_url",
            field=models.URLField(blank=True, max_length=2000),
        ),
    ]
