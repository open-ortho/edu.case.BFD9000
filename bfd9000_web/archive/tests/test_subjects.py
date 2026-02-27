"""API tests for subject endpoints."""

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from archive.models import Subject, Collection, Identifier
from archive.constants import SYSTEM_IDENTIFIER_BOLTON_SUBJECT
from .base import CleanupAPITestCase

class SubjectTests(CleanupAPITestCase):
    """Validate subject CRUD and search behavior."""
    def setUp(self):
        # Create user for authentication
        self.user = User.objects.create_user(username='testuser', password='testpassword')

        # Add necessary permissions
        content_type = ContentType.objects.get_for_model(Subject)
        permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*permissions)

        self.client.force_authenticate(user=self.user)

        # Create test data
        self.collection, _ = Collection.objects.get_or_create(
            short_name="BBC",
            defaults={"full_name": "Bolton-Brush Collection"}
        )

    def test_create_subject_minimal(self):
        """Should create subject with minimal required fields"""
        url = reverse('archive:subject-list')
        data = {
            "humanname_family": "Doe",
            "humanname_given": "John",
            "gender": "male",
            "birth_date": "2000-01-01"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['humanname_family'], 'Doe')
        self.assertEqual(response.data['humanname_given'], 'John')
        self.assertEqual(response.data['gender'], 'male')
        self.assertEqual(response.data['birth_date'], '2000-01-01')

    def test_create_subject_full(self):
        """Should create subject with all optional fields"""
        url = reverse('archive:subject-list')
        data = {
            "humanname_family": "Smith",
            "humanname_given": "Jane",
            "gender": "female",
            "birth_date": "1995-05-15",
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

    def test_create_subject_with_identifier(self):
        """Should attach identifier when identifier fields are provided."""
        url = reverse('archive:subject-list')
        data = {
            "humanname_family": "Doe",
            "humanname_given": "John",
            "gender": "male",
            "birth_date": "2000-01-01",
            "identifier_value": "B0001",
            "identifier_system": SYSTEM_IDENTIFIER_BOLTON_SUBJECT,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        subject = Subject.objects.get(pk=response.data['id'])
        self.assertEqual(subject.identifiers.count(), 1)
        identifier = Identifier.objects.get(pk=subject.identifiers.first().pk)
        self.assertEqual(identifier.value, "B0001")
        self.assertEqual(identifier.system, SYSTEM_IDENTIFIER_BOLTON_SUBJECT)

    def test_create_subject_missing_required_field(self):
        """Should return 400 if required fields are missing"""
        url = reverse('archive:subject-list')
        data = {
            "humanname_family": "Doe",
            # Missing humanname_given, gender, birth_date
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_subject_invalid_gender(self):
        """Should return 400 for invalid gender value"""
        url = reverse('archive:subject-list')
        data = {
            "humanname_family": "Doe",
            "humanname_given": "John",
            "gender": "invalid_gender",
            "birth_date": "2000-01-01"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_subjects(self):
        """Should list all subjects"""
        # Create test subjects
        Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )
        Subject.objects.create(
            humanname_family="Smith",
            humanname_given="Jane",
            gender="female",
            birth_date="1995-05-15"
        )

        url = reverse('archive:subject-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_get_subject_detail(self):
        """Should retrieve specific subject details"""
        subject = Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )

        url = reverse('archive:subject-detail', kwargs={'pk': subject.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], subject.id)
        self.assertEqual(response.data['humanname_family'], 'Doe')
        self.assertEqual(response.data['humanname_given'], 'John')

    def test_get_subject_not_found(self):
        """Should return 404 for non-existent subject"""
        url = reverse('archive:subject-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_subject(self):
        """Should update subject details"""
        subject = Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )

        url = reverse('archive:subject-detail', kwargs={'pk': subject.id})
        data = {
            "humanname_family": "Updated",
            "humanname_given": "John",
            "gender": "male",
            "birth_date": "2000-01-01"
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['humanname_family'], 'Updated')

    def test_delete_subject(self):
        """Should delete subject"""
        subject = Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )

        url = reverse('archive:subject-detail', kwargs={'pk': subject.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify deletion
        self.assertFalse(Subject.objects.filter(pk=subject.id).exists())

    def test_search_subjects(self):
        """Should search subjects by query parameter"""
        Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )
        Subject.objects.create(
            humanname_family="Smith",
            humanname_given="Jane",
            gender="female",
            birth_date="1995-05-15"
        )

        url = reverse('archive:subject-list') + '?search=Doe'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify we got results
        self.assertGreater(len(response.data['results']), 0)

    def test_filter_subjects_by_gender(self):
        """Should filter subjects by gender"""
        Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )
        Subject.objects.create(
            humanname_family="Smith",
            humanname_given="Jane",
            gender="female",
            birth_date="1995-05-15"
        )

        url = reverse('archive:subject-list') + '?gender=male'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # All results should be male
        for item in response.data['results']:
            self.assertEqual(item['gender'], 'male')

    def test_unauthenticated_access(self):
        """Should return 401/403 if not authenticated"""
        self.client.logout()
        url = reverse('archive:subject-list')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_subject_with_encounters_count(self):
        """Should return encounter count in list view"""
        subject = Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )

        url = reverse('archive:subject-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find our subject in results
        subject_data = next(
            (item for item in response.data['results'] if item['id'] == subject.id),
            None
        )
        self.assertIsNotNone(subject_data)
        self.assertIn('encounter_count', subject_data)
        self.assertIn('record_count', subject_data)
