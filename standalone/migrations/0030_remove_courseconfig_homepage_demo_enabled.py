from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("standalone", "0029_learningobjective_symbol_heuristics"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="courseconfig",
            name="homepage_demo_enabled",
        ),
    ]
