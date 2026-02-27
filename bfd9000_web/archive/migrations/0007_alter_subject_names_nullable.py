from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0006_remove_record_collection_subject_collection"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subject",
            name="humanname_family",
            field=models.CharField(blank=True, help_text="Family name", max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name="subject",
            name="humanname_given",
            field=models.CharField(blank=True, help_text="Given name", max_length=128, null=True),
        ),
    ]
