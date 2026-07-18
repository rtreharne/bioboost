from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0038_courseconfig_calculator_enabled"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlockResource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("citation", models.CharField(max_length=500)),
                ("hyperlink", models.URLField(max_length=1000)),
                (
                    "block",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resources", to="standalone.courseblock"),
                ),
            ],
            options={
                "ordering": ["created_at", "pk"],
            },
        ),
    ]
