from django.core.management.base import BaseCommand
from archive.models import Coding
from archive.constants import SYSTEM_RECORD_TYPE, SYSTEM_ORIENTATION, SYSTEM_MODALITY, SYSTEM_PROCEDURE

class Command(BaseCommand):
    help = 'Initialize default coding values'

    def handle(self, *args, **options):
        self.stdout.write('Initializing codings...')

        # Record Types
        record_types = [
            ('lateral', 'Lateral Cephalogram'),
            ('pa', 'PA Cephalogram'),
            ('hand', 'Hand Wrist'),
            ('pano', 'Panoramic'),
            ('photo', 'Photograph'),
            ('model', 'Dental Model'),
            ('cbct', 'CBCT'),
        ]
        for code, display in record_types:
            Coding.objects.get_or_create(
                system=SYSTEM_RECORD_TYPE,
                code=code,
                defaults={'display': display}
            )

        # Orientations
        orientations = [
            ('left', 'Left'),
            ('right', 'Right'),
            ('center', 'Center'),
            ('frontal', 'Frontal'),
            ('profile', 'Profile'),
            ('upper', 'Upper'),
            ('lower', 'Lower'),
        ]
        for code, display in orientations:
            Coding.objects.get_or_create(
                system=SYSTEM_ORIENTATION,
                code=code,
                defaults={'display': display}
            )

        # Modalities (DICOM)
        modalities = [
            ('RG', 'Radiographic Imaging'), # Conventional X-Ray
            ('DX', 'Digital X-Ray'),
            ('PX', 'Panoramic X-Ray'), # Often used for Pano
            ('XC', 'External-camera Photography'), # Photos
            ('M3D', '3D Model'), # STL/PLY
            ('CT', 'Computed Tomography'),
        ]
        for code, display in modalities:
            Coding.objects.get_or_create(
                system=SYSTEM_MODALITY,
                code=code,
                defaults={'display': display}
            )

        # Procedures
        procedures = [
            ('ortho-visit', 'Orthodontic Visit'),
        ]
        for code, display in procedures:
            Coding.objects.get_or_create(
                system=SYSTEM_PROCEDURE,
                code=code,
                defaults={'display': display}
            )

        self.stdout.write(self.style.SUCCESS('Successfully initialized codings'))
