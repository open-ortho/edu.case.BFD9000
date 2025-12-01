from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from archive.models import Record, Collection, Coding
from archive.constants import SYSTEM_RECORD_TYPE, SYSTEM_ORIENTATION, SYSTEM_MODALITY, SYSTEM_PROCEDURE

class ApiFlowTests(APITestCase):
    def setUp(self):
        # Create necessary data
        self.collection = Collection.objects.create(short_name="TEST", full_name="Test Collection")
        
        # Ensure codings exist
        self.rt = Coding.objects.create(system=SYSTEM_RECORD_TYPE, code='lateral', display='Lateral')
        self.orient = Coding.objects.create(system=SYSTEM_ORIENTATION, code='left', display='Left')
        self.mod = Coding.objects.create(system=SYSTEM_MODALITY, code='RG', display='Radiography')
        self.proc = Coding.objects.create(system=SYSTEM_PROCEDURE, code='ortho-visit', display='Orthodontic Visit')
        
        self.subject_data = {
            "humanname_family": "Doe",
            "humanname_given": "John",
            "gender": "male",
            "birth_date": "2000-01-01"
        }

    def test_full_flow(self):
        # 1. Create Subject
        url = reverse('archive:subject-list')
        response = self.client.post(url, self.subject_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subject_id = response.data['id']
        
        # 2. Create Encounter
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': subject_id})
        encounter_data = {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.proc.id
            # age_at_encounter should be calculated: 20 years
        }
        response = self.client.post(url, encounter_data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Encounter creation failed: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        encounter_id = response.data['id']
        self.assertAlmostEqual(response.data['age_at_encounter'], 20.0, delta=0.1)
        
        # 3. Upload Record
        url = reverse('archive:encounter-records-list', kwargs={'encounter_pk': encounter_id})
        
        # Create dummy PNG
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        file = SimpleUploadedFile("test.png", image_content, content_type="image/png")
        
        data = {
            "file": file,
            "record_type": "lateral",
            "orientation": "left",
            "modality": "RG",
            "operator": "TestOp"
        }
        
        response = self.client.post(url, data, format='multipart')
        if response.status_code != status.HTTP_201_CREATED:
            print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        record_id = response.data['id']
        
        # 4. Verify Record
        record = Record.objects.get(pk=record_id)
        self.assertTrue(record.imaging_study)
        self.assertTrue(record.imaging_study.source_file)
        self.assertEqual(record.record_type.code, 'lateral')
        
        # 5. Verify Image Download
        url = reverse('archive:record-image', kwargs={'pk': record_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 6. Verify Thumbnail
        url = reverse('archive:record-thumbnail', kwargs={'pk': record_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
