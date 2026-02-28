from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0008_seed_skeletal_and_race_codings"),
    ]

    operations = [
        migrations.CreateModel(
            name="ValueSet",
            fields=[
                ("id", models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who created this record",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="valueset_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who last modified this record",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="valueset_modified",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("slug", models.SlugField(max_length=128, unique=True)),
                ("url", models.URLField(
                    help_text="Canonical URL", max_length=255, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("version", models.CharField(blank=True, max_length=64)),
                ("status", models.CharField(blank=True, max_length=32)),
                ("publisher", models.CharField(blank=True, max_length=255)),
                ("publication_url", models.URLField(blank=True, max_length=255)),
                ("code_system_url", models.URLField(blank=True, max_length=255)),
                ("code_system_publication_url",
                 models.URLField(blank=True, max_length=255)),
                ("code_system_status", models.CharField(blank=True, max_length=32)),
            ],
            options={
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="ValueSetConcept",
            fields=[
                ("id", models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who created this record",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="valuesetconcept_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who last modified this record",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="valuesetconcept_modified",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "coding",
                    models.ForeignKey(on_delete=models.CASCADE,
                                      to="archive.coding"),
                ),
                (
                    "valueset",
                    models.ForeignKey(on_delete=models.CASCADE,
                                      to="archive.valueset"),
                ),
            ],
        ),
        migrations.AddField(
            model_name="valueset",
            name="codings",
            field=models.ManyToManyField(
                blank=True, related_name="value_sets", through="archive.ValueSetConcept", to="archive.coding"),
        ),
        migrations.AddConstraint(
            model_name="valuesetconcept",
            constraint=models.UniqueConstraint(
                fields=("valueset", "coding"), name="unique_valueset_coding"),
        ),
        migrations.AddIndex(
            model_name="valueset",
            index=models.Index(
                fields=["slug"], name="archive_val_slug_1b6e46_idx"),
        ),
        migrations.AddIndex(
            model_name="valuesetconcept",
            index=models.Index(
                fields=["valueset", "coding"], name="archive_val_values_22c99f_idx"),
        ),
    ]
