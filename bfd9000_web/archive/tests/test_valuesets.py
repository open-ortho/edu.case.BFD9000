from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from archive.models import Collection, Coding
from archive.constants import SYSTEM_RECORD_TYPE, SYSTEM_ORIENTATION, SYSTEM_MODALITY

class ValuesetTests(APITestCase):
    def setUp(self):
        # Create user for authentication
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.collection = Collection.objects.create(short_name="TEST", full_name="Test Collection")
        self.rt = Coding.objects.create(system=SYSTEM_RECORD_TYPE, code='lateral', display='Lateral')
        self.orient = Coding.objects.create(system=SYSTEM_ORIENTATION, code='left', display='Left')
        self.mod = Coding.objects.create(system=SYSTEM_MODALITY, code='RG', display='Radiography')

    def test_missing_type_parameter(self):
        """Should return 400 if 'type' parameter is missing"""
        url = reverse('archive:valuesets-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Missing 'type' parameter")

    def test_unknown_valueset_type(self):
        """Should return 404 if 'type' parameter is unknown"""
        url = reverse('archive:valuesets-list') + '?type=unknown_type'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sex_options(self):
        """Should return sex options"""
        url = reverse('archive:valuesets-list') + '?type=sex_options'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        self.assertIn('id', response.data[0])
        self.assertIn('display', response.data[0])

    def test_collections(self):
        """Should return collections"""
        url = reverse('archive:valuesets-list') + '?type=collections'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should find our test collection
        found = any(item['id'] == 'TEST' for item in response.data)
        self.assertTrue(found)
        self.assertIn('id', response.data[0])
        self.assertIn('display', response.data[0])

    def test_record_types(self):
        """Should return record types"""
        url = reverse('archive:valuesets-list') + '?type=record_types'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found = any(item['id'] == 'lateral' for item in response.data)
        self.assertTrue(found)

    def test_orientations(self):
        """Should return orientations"""
        url = reverse('archive:valuesets-list') + '?type=orientations'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found = any(item['id'] == 'left' for item in response.data)
        self.assertTrue(found)

    def test_modalities(self):
        """Should return modalities"""
        url = reverse('archive:valuesets-list') + '?type=modalities'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found = any(item['id'] == 'RG' for item in response.data)
        self.assertTrue(found)

    def test_unauthenticated_access(self):
        """Should return 401/403 if not authenticated"""
        self.client.logout()
        url = reverse('archive:valuesets-list') + '?type=sex_options'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
