from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from archive.models import Encounter, Record, Subject

class Command(BaseCommand):
    help = "Create or update the Curator group with correct permissions. Safe to rerun."

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="Curator")
        subject_ct = ContentType.objects.get_for_model(Subject)
        encounter_ct = ContentType.objects.get_for_model(Encounter)
        record_ct = ContentType.objects.get_for_model(Record)

        subject_add = Permission.objects.get(codename="add_subject", content_type=subject_ct)
        subject_change = Permission.objects.get(codename="change_subject", content_type=subject_ct)
        encounter_add = Permission.objects.get(codename="add_encounter", content_type=encounter_ct)
        encounter_change = Permission.objects.get(codename="change_encounter", content_type=encounter_ct)

        required_perms = [subject_add, subject_change, encounter_add, encounter_change]
        for perm in required_perms:
            group.permissions.add(perm)

        forbidden_perms = Permission.objects.filter(
            content_type__in=[subject_ct, encounter_ct, record_ct],
            codename__startswith="delete_",
        )
        auth_management_perms = Permission.objects.filter(content_type__app_label="auth")
        forbidden_perms = forbidden_perms | auth_management_perms

        for perm in forbidden_perms:
            group.permissions.remove(perm)

        self.stdout.write(self.style.SUCCESS("Curator group permissions updated."))
