"""
Data migration: split the single bolton-record-id identifier system into
separate systems for physical and digital records.

Before this migration, both PhysicalRecord and DigitalRecord shared
SYSTEM_IDENTIFIER_BOLTON_RECORD = '.../bolton-record-id'.

After this migration:
  - Identifiers linked to DigitalRecord.identifiers use '.../bolton-digital-record-id'
  - Identifiers linked to PhysicalRecord.identifiers use '.../bolton-physical-record-id'

Since this is a first-deploy environment, any existing rows with the old system
came only from DigitalRecord._assign_bolton_record_identifier (the only path that
existed before this PR). We therefore migrate all old-system rows to the digital
system. PhysicalRecord identifiers will be assigned the new physical system going
forward from their first save.
"""

from django.db import migrations

OLD_SYSTEM = 'https://orthodontics.case.edu/fhir/identifier-system/bolton-record-id'
NEW_DIGITAL_SYSTEM = 'https://orthodontics.case.edu/fhir/identifier-system/bolton-digital-record-id'


def migrate_bolton_record_identifiers(apps, schema_editor):
    Identifier = apps.get_model('archive', 'Identifier')
    Identifier.objects.filter(system=OLD_SYSTEM).update(system=NEW_DIGITAL_SYSTEM)


def reverse_bolton_record_identifiers(apps, schema_editor):
    Identifier = apps.get_model('archive', 'Identifier')
    Identifier.objects.filter(system=NEW_DIGITAL_SYSTEM).update(system=OLD_SYSTEM)


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0006_add_physicallocation_sequence_number'),
    ]

    operations = [
        migrations.RunPython(
            migrate_bolton_record_identifiers,
            reverse_bolton_record_identifiers,
        ),
    ]
