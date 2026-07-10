from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0033_questionbankitem_math_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseconfig",
            name="math_symbolic_ratio_percent",
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="blockconfig",
            name="math_symbolic_ratio_percent",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
            ),
        ),
    ]
