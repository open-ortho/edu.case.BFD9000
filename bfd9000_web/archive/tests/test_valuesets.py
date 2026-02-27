"""API tests for valueset endpoints."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from archive.models import Collection, Coding
from archive.constants import SYSTEM_RECORD_TYPE, SYSTEM_ORIENTATION, SYSTEM_MODALITY, SYSTEM_PROCEDURE
from .base import CleanupAPITestCase

class ValuesetTests(CleanupAPITestCase):
    """Validate valueset responses and filtering."""
    def setUp(self):
        # Create user for authentication
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

        # Create test data with multiple codings per system for better testing
        self.collection, _ = Collection.objects.get_or_create(
            short_name="TEST",
            defaults={"full_name": "Test Collection"},
        )
        self.collection2, _ = Collection.objects.get_or_create(
            short_name="TEST2",
            defaults={"full_name": "Test Collection 2"},
        )

        # Record types (using SNOMED codes from migration)
        self.rt_lateral, _ = Coding.objects.get_or_create(
            system=SYSTEM_RECORD_TYPE,
            code='201456002',
            defaults={'display': 'Cephalogram'},
        )
        self.rt_pa, _ = Coding.objects.get_or_create(
            system=SYSTEM_RECORD_TYPE,
            code='268425006',
            defaults={'display': 'Pelvis X-ray'},
        )

        # Orientations (using SNOMED codes from migration)
        self.orient_left, _ = Coding.objects.get_or_create(
            system=SYSTEM_ORIENTATION,
            code='399173006',
            defaults={'display': 'Left lateral projection'},
        )
        self.orient_right, _ = Coding.objects.get_or_create(
            system=SYSTEM_ORIENTATION,
            code='399198007',
            defaults={'display': 'Right lateral projection'},
        )

        # Modalities
        self.mod_rg, _ = Coding.objects.get_or_create(
            system=SYSTEM_MODALITY,
            code='RG',
            defaults={'display': 'Radiography'},
        )
        self.mod_m3d, _ = Coding.objects.get_or_create(
            system=SYSTEM_MODALITY,
            code='M3D',
            defaults={'display': '3D Model'},
        )

        # Procedures
        self.proc_visit, _ = Coding.objects.get_or_create(
            system=SYSTEM_PROCEDURE,
            code='ortho-visit',
            defaults={'display': 'Orthodontic Visit'},
        )

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
        """Should return sex options with correct structure"""
        url = reverse('archive:valuesets-list') + '?type=sex_options'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

        # Verify structure
        for item in response.data:
            self.assertIn('id', item)
            self.assertIn('display', item)
            self.assertEqual(len(item), 2, "Should only have 'id' and 'display' fields")
            self.assertIsInstance(item['id'], str)
            self.assertIsInstance(item['display'], str)

        # Verify expected values exist
        ids = [item['id'] for item in response.data]
        self.assertIn('male', ids)
        self.assertIn('female', ids)

    def test_collections(self):
        """Should return collections with correct structure"""
        url = reverse('archive:valuesets-list') + '?type=collections'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify structure
        for item in response.data:
            self.assertIn('id', item)
            self.assertIn('display', item)
            self.assertEqual(len(item), 2, "Should only have 'id' and 'display' fields")

        # Should find our test collections
        ids = [item['id'] for item in response.data]
        self.assertIn('TEST', ids)
        self.assertIn('TEST2', ids)

        # Verify display names
        test_item = next(item for item in response.data if item['id'] == 'TEST')
        self.assertEqual(test_item['display'], 'Test Collection')

    def test_record_types(self):
        """Should return record types with correct structure"""
        url = reverse('archive:valuesets-list') + '?type=record_types'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify structure
        for item in response.data:
            self.assertIn('id', item)
            self.assertIn('display', item)
            self.assertEqual(len(item), 2, "Should only have 'id' and 'display' fields")

        # Verify expected values (SNOMED codes)
        ids = [item['id'] for item in response.data]
        self.assertIn('201456002', ids)  # Cephalogram
        self.assertIn('268425006', ids)  # Pelvis X-ray

    def test_orientations(self):
        """Should return orientations with correct structure"""
        url = reverse('archive:valuesets-list') + '?type=orientations'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify structure
        for item in response.data:
            self.assertIn('id', item)
            self.assertIn('display', item)
            self.assertEqual(len(item), 2, "Should only have 'id' and 'display' fields")

        # Verify expected values (SNOMED codes)
        ids = [item['id'] for item in response.data]
        self.assertIn('399173006', ids)  # Left lateral projection
        self.assertIn('399198007', ids)  # Right lateral projection

    def test_modalities(self):
        """Should return modalities with correct structure"""
        url = reverse('archive:valuesets-list') + '?type=modalities'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify structure
        for item in response.data:
            self.assertIn('id', item)
            self.assertIn('display', item)
            self.assertEqual(len(item), 2, "Should only have 'id' and 'display' fields")

        # Verify expected values
        ids = [item['id'] for item in response.data]
        self.assertIn('RG', ids)
        self.assertIn('M3D', ids)

    def test_procedures(self):
        """Should return procedures with correct structure"""
        url = reverse('archive:valuesets-list') + '?type=procedures'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify structure
        for item in response.data:
            self.assertIn('id', item)
            self.assertIn('display', item)
            self.assertEqual(len(item), 2, "Should only have 'id' and 'display' fields")

        # Verify expected values
        ids = [item['id'] for item in response.data]
        self.assertIn('ortho-visit', ids)

    def test_cross_contamination_orientations_vs_collections(self):
        """Orientations should not contain collection codes"""
        url_orient = reverse('archive:valuesets-list') + '?type=orientations'
        url_coll = reverse('archive:valuesets-list') + '?type=collections'

        response_orient = self.client.get(url_orient)
        response_coll = self.client.get(url_coll)

        orient_ids = {item['id'] for item in response_orient.data}
        coll_ids = {item['id'] for item in response_coll.data}

        # No overlap should exist
        overlap = orient_ids.intersection(coll_ids)
        self.assertEqual(len(overlap), 0, f"Found overlap between orientations and collections: {overlap}")

    def test_cross_contamination_orientations_vs_modalities(self):
        """Orientations should not contain modality codes"""
        url_orient = reverse('archive:valuesets-list') + '?type=orientations'
        url_mod = reverse('archive:valuesets-list') + '?type=modalities'

        response_orient = self.client.get(url_orient)
        response_mod = self.client.get(url_mod)

        orient_ids = {item['id'] for item in response_orient.data}
        mod_ids = {item['id'] for item in response_mod.data}

        # No overlap should exist
        overlap = orient_ids.intersection(mod_ids)
        self.assertEqual(len(overlap), 0, f"Found overlap between orientations and modalities: {overlap}")

    def test_cross_contamination_modalities_vs_collections(self):
        """Modalities should not contain collection codes"""
        url_mod = reverse('archive:valuesets-list') + '?type=modalities'
        url_coll = reverse('archive:valuesets-list') + '?type=collections'

        response_mod = self.client.get(url_mod)
        response_coll = self.client.get(url_coll)

        mod_ids = {item['id'] for item in response_mod.data}
        coll_ids = {item['id'] for item in response_coll.data}

        # No overlap should exist - modalities use DICOM codes, collections use custom IDs
        overlap = mod_ids.intersection(coll_ids)
        self.assertEqual(len(overlap), 0, f"Found overlap between modalities and collections: {overlap}")

    def test_unauthenticated_access(self):
        """Should return 401/403 if not authenticated"""
        self.client.logout()
        url = reverse('archive:valuesets-list') + '?type=sex_options'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
