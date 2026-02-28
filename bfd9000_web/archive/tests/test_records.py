"""API tests for record endpoints and uploads."""

import datetime
import io

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from archive.models import Subject, Encounter, Record, Coding, Collection, ImagingStudy
from archive.constants import (
    SYSTEM_RECORD_TYPE,
    SYSTEM_ORIENTATION,
    SYSTEM_MODALITY,
    SYSTEM_PROCEDURE,
    SYSTEM_BODY_SITE,
    SYSTEM_IDENTIFIER_IMAGE_TYPE,
)
from .base import CleanupAPITestCase


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
        for model in [Subject, Encounter, Record, ImagingStudy]:
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
            code='201456002',
            defaults={'display': 'Cephalogram'}
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
        self.image_type_lateral, _ = Coding.objects.get_or_create(
            system=SYSTEM_IDENTIFIER_IMAGE_TYPE,
            code='L',
            defaults={'display': 'Lateral'},
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

    def test_create_record_with_file(self):
        """Should create record with file upload"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")

        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
            "operator": "TestOp"
        }

        response = self.client.post(url, data, format='multipart')
        if response.status_code != status.HTTP_201_CREATED:
            print(
                f"Record creation failed: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        # Verify record was created successfully
        self.assertIn('record_type', response.data)

    def test_create_record_with_tiff_file(self):
        """Should create record with TIFF upload."""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.tiff", self.tiff_content, content_type="image/tiff")

        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

    def test_create_record_missing_file(self):
        """Should return 400 if file is missing"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        data = {
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
            "operator": "TestOp"
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_record_missing_required_metadata(self):
        """Should return 400 if required metadata is missing"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")

        data = {
            "file": file,
            # Missing record_type, orientation, modality
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_record_invalid_encounter(self):
        """Should return 404 for non-existent encounter"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': 99999})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")

        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_records_for_encounter(self):
        """Should list all records for an encounter"""
        # Create records
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        for i in range(2):
            file = SimpleUploadedFile(
                f"test{i}.png", self.image_content, content_type="image/png")
            data = {
                "file": file,
                "record_type": self.rt_lateral.code,
                "orientation": "left",
                "modality": "RG",
            }
            self.client.post(url, data, format='multipart')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_record_detail(self):
        """Should retrieve specific record details"""
        # Create a record
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        create_response = self.client.post(url, data, format='multipart')
        record_id = create_response.data['id']

        # Get record detail
        url = reverse('archive:record-detail', kwargs={'pk': record_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], record_id)
        self.assertIn('encounter', response.data)

    def test_get_record_not_found(self):
        """Should return 404 for non-existent record"""
        url = reverse('archive:record-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_record_metadata(self):
        """Should update record metadata"""
        # Create a record
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        create_response = self.client.post(url, data, format='multipart')
        record_id = create_response.data['id']

        # Update record - use device field which exists on Record model
        url = reverse('archive:record-detail', kwargs={'pk': record_id})
        update_data = {
            "device": "NewScanner"
        }
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['device'], 'NewScanner')

    def test_delete_record(self):
        """Should delete record"""
        # Create a record
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        create_response = self.client.post(url, data, format='multipart')
        record_id = create_response.data['id']

        # Delete record
        url = reverse('archive:record-detail', kwargs={'pk': record_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify deletion
        self.assertFalse(Record.objects.filter(pk=record_id).exists())

    def test_get_record_image(self):
        """Should serve full record image"""
        # Create a record
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        create_response = self.client.post(url, data, format='multipart')
        record_id = create_response.data['id']

        # Get image
        url = reverse('archive:record-image', kwargs={'pk': record_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image/', response['Content-Type'])

    def test_get_record_image_converts_tiff_to_png(self):
        """Record image endpoint should return browser-friendly PNG for TIFF source."""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.tiff", self.tiff_content, content_type="image/tiff")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        create_response = self.client.post(url, data, format='multipart')
        record_id = create_response.data['id']

        image_url = reverse('archive:record-image', kwargs={'pk': record_id})
        response = self.client.get(image_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_create_record_sets_default_patient_orientation_for_lateral_image_type(self):
        """Lateral image type should default PatientOrientation to A\\F."""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.tiff", self.tiff_content, content_type="image/tiff")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
            "image_type": "L",
        }

        create_response = self.client.post(url, data, format='multipart')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            create_response.data['patient_orientation'], ['A', 'F'])

        record = Record.objects.get(pk=create_response.data['id'])
        self.assertEqual(record.patient_orientation, 'A\\F')

    def test_record_image_applies_saved_transform_ops(self):
        """Image endpoint should apply persisted transform operations."""
        img = Image.new('RGB', (2, 1), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        png_content = buf.getvalue()

        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", png_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
            "image_transform_ops": '[{"rotation":90,"flip":false}]',
        }

        create_response = self.client.post(url, data, format='multipart')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        image_url = reverse('archive:record-image',
                            kwargs={'pk': create_response.data['id']})
        response = self.client.get(image_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')

        transformed = Image.open(io.BytesIO(response.content))
        self.assertEqual(transformed.size, (1, 2))

    def test_get_record_thumbnail(self):
        """Should serve record thumbnail (raster image)"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        create_response = self.client.post(url, data, format='multipart')
        record_id = create_response.data['id']
        url = reverse('archive:record-thumbnail', kwargs={'pk': record_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        payload = b''.join(response.streaming_content) if hasattr(
            response, 'streaming_content') else response.content
        self.assertTrue(payload.startswith(b'\xff\xd8'))  # JPEG SOI

    def test_get_record_thumbnail_for_3d_file(self):
        """Should serve static fallback JPEG for 3D file (e.g., STL)"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        stl_content = b"solid ascii\nendsolid"
        file = SimpleUploadedFile(
            "test.stl", stl_content, content_type="application/octet-stream")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        create_response = self.client.post(url, data, format='multipart')
        record_id = create_response.data['id']
        url = reverse('archive:record-thumbnail', kwargs={'pk': record_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertTrue(response.content.startswith(b'\xff\xd8'))

        # 3D inputs should not generate a persisted thumbnail yet
        record = Record.objects.get(pk=record_id)
        self.assertFalse(bool(record.thumbnail))

    def test_filter_records_by_record_type(self):
        """Should filter records by record type"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})

        # Create records with different types
        file1 = SimpleUploadedFile(
            "test1.png", self.image_content, content_type="image/png")
        data1 = {
            "file": file1,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }
        self.client.post(url, data1, format='multipart')

        # Filter by record type (using ID since it's a foreign key)
        filter_url = url + f'?record_type={self.rt_lateral.id}'
        response = self.client.get(filter_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify at least one record was returned
        self.assertGreater(len(response.data['results']), 0)
        for record in response.data['results']:
            # record_type is a nested object with code field
            self.assertEqual(record['record_type']
                             ['code'], self.rt_lateral.code)

    def test_unauthenticated_access(self):
        """Should return 401/403 if not authenticated"""
        self.client.logout()
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        response = self.client.get(url)
        self.assertIn(response.status_code, [
                      status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_record_response_structure(self):
        """Should return record with expected fields"""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }

        response = self.client.post(url, data, format='multipart')
        if response.status_code != status.HTTP_201_CREATED:
            print(
                f"Record creation failed: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check for expected fields (fields that exist on Record model)
        expected_fields = ['id', 'record_type', 'encounter', 'imaging_study']
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_record_includes_encounter_date(self):
        """Should expose encounter date in record response."""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data['encounter_date']), '2020-01-01')

    def test_record_age_falls_back_to_birthdate_when_duration_missing(self):
        """Should derive record age from encounter date and subject birth date."""
        encounter = Encounter.objects.create(
            subject=self.subject,
            actual_period_start="2020-06-15",
            procedure_code=self.procedure,
            procedure_occurrence_age=None,
        )
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }

        create_response = self.client.post(url, data, format='multipart')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertAlmostEqual(
            create_response.data['age_at_encounter'], 20.45, delta=0.05)

        detail_url = reverse('archive:record-detail',
                             kwargs={'pk': create_response.data['id']})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(
            detail_response.data['age_at_encounter'], 20.45, delta=0.05)

    def test_upload_preserves_acquisition_date(self):
        """Should return the same acquisition date submitted on upload."""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")

        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
            "acquisition_date": "2026-02-27",
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data['acquisition_date']), '2026-02-27')

    def test_create_record_rejects_body_site_code_as_record_type(self):
        """Should reject body-site coding when submitted as record_type."""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        body_site, _ = Coding.objects.get_or_create(
            system=SYSTEM_BODY_SITE,
            code='69536005',
            defaults={'display': 'Head'},
        )

        data = {
            "file": file,
            "record_type": body_site.code,
            "orientation": "left",
            "modality": "RG",
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('record_type', response.data['error']['details'])

    def test_imaging_study_operator_display_fields(self):
        """Imaging study API should expose username and full display for operator."""
        url = reverse('archive:encounter-records-list',
                      kwargs={'encounter_pk': self.encounter.id})
        file = SimpleUploadedFile(
            "test.png", self.image_content, content_type="image/png")
        data = {
            "file": file,
            "record_type": self.rt_lateral.code,
            "orientation": "left",
            "modality": "RG",
        }

        create_response = self.client.post(url, data, format='multipart')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        study_url = reverse('archive:imagingstudy-detail',
                            kwargs={'pk': create_response.data['imaging_study']})
        study_response = self.client.get(study_url)
        self.assertEqual(study_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            study_response.data['scan_operator_username'], 'testuser')
        self.assertEqual(
            study_response.data['scan_operator_display'], 'Test User (testuser)')
