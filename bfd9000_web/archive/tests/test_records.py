"""API tests for record endpoints and uploads."""

import datetime
import io
from django.test import override_settings
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from archive.models import (
    ArchiveLocation,
    Collection,
    Coding,
    Device,
    DigitalRecord,
    Encounter,
    Endpoint,
    ImagingStudy,
    PhysicalRecord,
    Subject,
)
from archive.constants import (
    SYSTEM_RECORD_TYPE,
    SYSTEM_ORIENTATION,
    SYSTEM_MODALITY,
    SYSTEM_PROCEDURE,
    SYSTEM_BODY_SITE,
)
from .base import CleanupAPITestCase

# A valid Fernet key for use in tests that need ENDPOINT_CREDENTIALS_KEY.
_TEST_FERNET_KEY = "pszJ39pBGFbjGZk8cM-MOzccZh0T0M8MTmVVitw4_8Y="


class RecordTests(CleanupAPITestCase):
    """Validate record creation, upload, and retrieval behavior."""

    def setUp(self):
        # Create user for authentication
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            first_name='Test',
            last_name='User',
        )

        # Add necessary permissions
        for model in [Subject, Encounter, DigitalRecord, ImagingStudy]:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            self.user.user_permissions.add(*permissions)

        self.client.force_authenticate(user=self.user)

        # Create collection (required for record creation)
        self.collection, _ = Collection.objects.get_or_create(
            short_name="TEST",
            defaults={"full_name": "Test Collection"}
        )

        # Create test subject and encounter
        self.subject = Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01",
            collection=self.collection,
        )

        self.procedure, _ = Coding.objects.get_or_create(
            system=SYSTEM_PROCEDURE,
            code='ortho-visit',
            defaults={'display': 'Orthodontic Visit'}
        )

        # Create encounter via API
        self.encounter = Encounter.objects.create(
            subject=self.subject,
            actual_period_start="2020-01-01",
            procedure_occurrence_age=datetime.timedelta(days=20 * 365.25),
            procedure_code=self.procedure
        )

        # Create codings
        self.rt_lateral, _ = Coding.objects.get_or_create(
            system=SYSTEM_RECORD_TYPE,
            code='L',
            defaults={'display': 'Lateral Cephalogram'}
        )
        self.orient_left, _ = Coding.objects.get_or_create(
            system=SYSTEM_ORIENTATION,
            code='left',
            defaults={'display': 'Left'}
        )
        self.mod_rg, _ = Coding.objects.get_or_create(
            system=SYSTEM_MODALITY,
            code='RG',
            defaults={'display': 'Radiography'}
        )

        # Create a valid PNG image
        self.image_content = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        tiff_buf = io.BytesIO()
        Image.new('RGB', (1, 1), color=(255, 255, 255)
                  ).save(tiff_buf, format='TIFF')
        self.tiff_content = tiff_buf.getvalue()

    @override_settings(ENDPOINT_CREDENTIALS_KEY=_TEST_FERNET_KEY)
    def test_endpoint_credentials_round_trip(self):
        """Endpoint credentials should encrypt and decrypt through model helpers."""
        endpoint = Endpoint.objects.create(
            name='Drive-A',
            status=Endpoint.Status.ACTIVE,
            connection_type=Endpoint.ConnectionType.DRIVE,
            address='https://drive.example.org',
        )
        payload = {'token': 'secret-token', 'user': 'archive-bot'}
        endpoint.set_credentials(payload)
        endpoint.save()

        endpoint.refresh_from_db()
        self.assertNotEqual(endpoint.credentials_encrypted, '')
        self.assertNotIn('secret-token', endpoint.credentials_encrypted)
        self.assertEqual(endpoint.get_credentials(), payload)

    def _upload_png(self, extra_fields: dict) -> 'rest_framework.response.Response':  # type: ignore[name-defined]
        """Helper: POST a minimal valid PNG record upload, merging extra_fields."""
        upload = SimpleUploadedFile('test.png', self.image_content, content_type='image/png')
        data = {
            'file': upload,
            'record_type': self.rt_lateral.code,
            'encounter': self.encounter.pk,
        }
        data.update(extra_fields)
        url = reverse('archive:digitalrecord-list')
        return self.client.post(url, data, format='multipart')

    def test_upload_with_device_creates_device_and_links_records(self):
        """Uploading with device fields creates a Device and links it to DigitalRecord and PhysicalRecord."""
        response = self._upload_png({
            'device_serial': 'SN-001',
            'device_manufacturer': 'Acme',
            'device_model': 'XRay3000',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Device should have been created
        self.assertEqual(Device.objects.filter(identifier='SN-001', model_number='XRay3000').count(), 1)
        device = Device.objects.get(identifier='SN-001', model_number='XRay3000')
        self.assertEqual(device.manufacturer, 'Acme')
        self.assertEqual(device.display_name, 'Acme XRay3000')

        # DigitalRecord should reference the device
        record_id = response.data['id']
        digital_record = DigitalRecord.objects.get(pk=record_id)
        self.assertEqual(digital_record.device_id, device.pk)

        # PhysicalRecord should also reference the device
        self.assertIsNotNone(digital_record.physical_record)
        physical_record: PhysicalRecord = digital_record.physical_record  # type: ignore[assignment]
        self.assertEqual(physical_record.device_id, device.pk)

    def test_upload_with_same_device_serial_reuses_device(self):
        """Uploading twice with the same serial+model reuses the existing Device (no duplicates)."""
        for _ in range(2):
            upload = SimpleUploadedFile('test.png', self.image_content, content_type='image/png')
            self.client.post(
                reverse('archive:digitalrecord-list'),
                {
                    'file': upload,
                    'record_type': self.rt_lateral.code,
                    'encounter': self.encounter.pk,
                    'device_serial': 'SN-REUSE',
                    'device_manufacturer': 'Acme',
                    'device_model': 'XRay3000',
                },
                format='multipart',
            )

        self.assertEqual(
            Device.objects.filter(identifier='SN-REUSE', model_number='XRay3000').count(),
            1,
            "Expected only one Device row for the same serial+model combination.",
        )

    def test_upload_without_device_fields_succeeds_with_null_device(self):
        """Uploading without device fields succeeds and leaves device null on both records."""
        response = self._upload_png({})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        record_id = response.data['id']
        digital_record = DigitalRecord.objects.get(pk=record_id)
        self.assertIsNone(digital_record.device_id)

        self.assertIsNotNone(digital_record.physical_record)
        physical_record: PhysicalRecord = digital_record.physical_record  # type: ignore[assignment]
        self.assertIsNone(physical_record.device_id)
