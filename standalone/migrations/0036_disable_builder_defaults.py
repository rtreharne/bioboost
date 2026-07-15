from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0035_courseimport_structured_maths_and_specs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="courseconfig",
            name="question_bank_builder_auto_start",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="courseconfig",
            name="question_bank_builder_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
