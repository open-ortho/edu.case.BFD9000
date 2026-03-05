from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0002_seed_codings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name='device',
            old_name='identifier',
            new_name='serial_number',
        ),
        migrations.AlterField(
            model_name='device',
            name='serial_number',
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text='Manufacturer-assigned serial number for this specific device unit (FHIR Device.serialNumber)',
            ),
        ),
        migrations.AddField(
            model_name='device',
            name='identifiers',
            field=models.ManyToManyField(
                blank=True,
                related_name='devices',
                to='archive.identifier',
                help_text='Institutional or business identifiers for this device (FHIR Device.identifier)',
            ),
        ),
        migrations.AddConstraint(
            model_name='device',
            constraint=models.UniqueConstraint(
                condition=models.Q(serial_number__gt=''),
                fields=('serial_number', 'manufacturer', 'model_number'),
                name='unique_device_serial_manufacturer_model',
            ),
        ),
    ]
