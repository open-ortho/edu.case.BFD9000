from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from archive.models import Subject, Encounter, Coding
from archive.constants import SYSTEM_PROCEDURE

class EncounterTests(APITestCase):
    def setUp(self):
        # Create user for authentication
        self.user = User.objects.create_user(username='testuser', password='testpassword')

        # Add necessary permissions
        for model in [Subject, Encounter]:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            self.user.user_permissions.add(*permissions)

        self.client.force_authenticate(user=self.user)

        # Create test subject
        self.subject = Subject.objects.create(
            humanname_family="Doe",
            humanname_given="John",
            gender="male",
            birth_date="2000-01-01"
        )

        # Create procedure coding
        self.procedure, _ = Coding.objects.get_or_create(
            system=SYSTEM_PROCEDURE,
            code='ortho-visit',
            defaults={'display': 'Orthodontic Visit'}
        )

    def test_create_encounter(self):
        """Should create encounter for subject"""
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        data = {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.procedure.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['actual_period_start'], '2020-01-01')
        self.assertIn('age_at_encounter', response.data)
        # Age should be approximately 20 years
        self.assertAlmostEqual(response.data['age_at_encounter'], 20.0, delta=1.0)

    def test_create_encounter_missing_procedure(self):
        """Should return 400 if procedure_code is missing"""
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        data = {
            "actual_period_start": "2020-01-01"
            # Missing procedure_code
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_encounter_invalid_subject(self):
        """Should return 404 for non-existent subject"""
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': 99999})
        data = {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.procedure.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_encounters_for_subject(self):
        """Should list all encounters for a subject"""
        # Create encounters using the API
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        self.client.post(url, {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.procedure.id
        }, format='json')
        self.client.post(url, {
            "actual_period_start": "2021-01-01",
            "procedure_code": self.procedure.id
        }, format='json')

        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_encounter_detail(self):
        """Should retrieve specific encounter details"""
        # Create encounter via API
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        create_response = self.client.post(url, {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.procedure.id
        }, format='json')
        encounter_id = create_response.data['id']

        url = reverse('archive:encounter-detail', kwargs={'pk': encounter_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], encounter_id)
        self.assertEqual(response.data['actual_period_start'], '2020-01-01')
        self.assertIn('subject', response.data)

    def test_get_encounter_not_found(self):
        """Should return 404 for non-existent encounter"""
        url = reverse('archive:encounter-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_encounter(self):
        """Should update encounter details"""
        # Create encounter via API
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        create_response = self.client.post(url, {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.procedure.id
        }, format='json')
        encounter_id = create_response.data['id']

        url = reverse('archive:encounter-detail', kwargs={'pk': encounter_id})
        data = {
            "actual_period_start": "2020-02-01"
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['actual_period_start'], '2020-02-01')

    def test_delete_encounter(self):
        """Should delete encounter"""
        # Create encounter via API
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        create_response = self.client.post(url, {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.procedure.id
        }, format='json')
        encounter_id = create_response.data['id']

        url = reverse('archive:encounter-detail', kwargs={'pk': encounter_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify deletion
        self.assertFalse(Encounter.objects.filter(pk=encounter_id).exists())

    def test_encounter_age_calculation(self):
        """Should automatically calculate age_at_encounter from subject birth_date"""
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        data = {
            "actual_period_start": "2015-06-15",
            "procedure_code": self.procedure.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Subject born 2000-01-01, encounter 2015-06-15 = ~15.5 years
        self.assertAlmostEqual(response.data['age_at_encounter'], 15.5, delta=1.0)

    def test_unauthenticated_access(self):
        """Should return 401/403 if not authenticated"""
        self.client.logout()
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_encounter_has_age_calculated(self):
        """Encounter detail should include calculated age"""
        # Create encounter via API
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        create_response = self.client.post(url, {
            "actual_period_start": "2020-01-01",
            "procedure_code": self.procedure.id
        }, format='json')
        encounter_id = create_response.data['id']

        url = reverse('archive:encounter-detail', kwargs={'pk': encounter_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if age_at_encounter is calculated
        self.assertIn('age_at_encounter', response.data)
        self.assertIsNotNone(response.data['age_at_encounter'])

    def test_list_encounters_pagination(self):
        """Should support pagination for encounter lists"""
        # Create multiple encounters via API
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        for i in range(25):
            # Use sequential dates across multiple months/years
            year = 2020 + (i // 12)
            month = (i % 12) + 1
            self.client.post(url, {
                "actual_period_start": f"{year}-{month:02d}-01",
                "procedure_code": self.procedure.id
            }, format='json')

        # Get first page
        url = reverse('archive:subject-encounters-list', kwargs={'subject_pk': self.subject.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 25)
        # Should have paginated results (max PAGE_SIZE=20)
        self.assertLessEqual(len(response.data['results']), 20)
