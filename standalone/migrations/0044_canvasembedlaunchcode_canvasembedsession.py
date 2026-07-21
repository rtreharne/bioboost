from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0043_canvasuseridentity_password_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="CanvasEmbedLaunchCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("canvas_page_url", models.URLField(max_length=2000)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "canvas_course_link",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="embed_launch_codes", to="standalone.canvascourselink"),
                ),
                (
                    "membership",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="embed_launch_codes", to="standalone.canvascoursemembership"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CanvasEmbedSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "canvas_course_link",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="embed_sessions", to="standalone.canvascourselink"),
                ),
                (
                    "membership",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="embed_sessions", to="standalone.canvascoursemembership"),
                ),
            ],
            options={
                "ordering": ["-updated_at", "-created_at"],
            },
        ),
    ]
