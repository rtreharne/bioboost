from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):

    dependencies = [
        ("standalone", "0034_courseconfig_math_symbolic_ratio_percent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseimport",
            name="use_structured_maths_generation",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="MathsGeneratorSpec",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("generator_id", models.CharField(max_length=120)),
                ("subject", models.CharField(default="maths", max_length=80)),
                ("exam_level", models.CharField(blank=True, max_length=80)),
                ("topic", models.CharField(blank=True, max_length=255)),
                ("chapter", models.CharField(blank=True, max_length=255)),
                ("learning_objective_text", models.TextField()),
                ("question_archetype", models.CharField(max_length=120)),
                ("difficulty", models.CharField(default="core", max_length=40)),
                ("parameter_ranges", models.JSONField(blank=True, default=dict)),
                ("constraints", models.JSONField(blank=True, default=dict)),
                ("question_template_latex", models.TextField(blank=True)),
                ("answer_logic", models.JSONField(blank=True, default=dict)),
                ("distractor_models", models.JSONField(blank=True, default=list)),
                ("validation_rules", models.JSONField(blank=True, default=list)),
                ("worked_solution_style", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("validated", "Validated"),
                            ("rejected", "Rejected"),
                            ("unsupported", "Unsupported"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("validation_errors", models.JSONField(blank=True, default=list)),
                (
                    "block",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="maths_generator_specs", to="standalone.courseblock"),
                ),
                (
                    "course",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="maths_generator_specs", to="standalone.course"),
                ),
                (
                    "learning_objective",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="maths_generator_specs", to="standalone.learningobjective"),
                ),
                (
                    "source_import",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="maths_generator_specs", to="standalone.courseimport"),
                ),
            ],
            options={
                "ordering": ["block__order", "learning_objective__position", "pk"],
                "unique_together": {("block", "learning_objective", "generator_id")},
            },
        ),
    ]
