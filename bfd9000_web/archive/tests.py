from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Collection, Coding, Encounter, Record, Subject


class ArchiveViewTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.staff = User.objects.create_user(
			username="staff", password="pass", is_staff=True
		)
		self.user = User.objects.create_user(
			username="user", password="pass", is_staff=False
		)

		self.collection = Collection.objects.create(
			short_name="BBC", full_name="Bolton-Brush Collection"
		)
		self.procedure = Coding.objects.create(
			system="http://example.com/procedure", code="PROC", display="Proc"
		)
		self.record_type = Coding.objects.create(
			system="http://example.com/record", code="REC", display="Record"
		)

		self.subject = Subject.objects.create(
			gender="male",
			birth_date="2000-01-01",
			humanname_family="Doe",
			humanname_given="John",
		)
		self.encounter = Encounter.objects.create(
			subject=self.subject,
			actual_period_start="2020-01-01",
			procedure_code=self.procedure,
		)

		self.client = Client()

	def test_subject_list_requires_login(self):
		response = self.client.get(reverse("archive:home"))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("login"), response.headers.get("Location", ""))

	def test_subject_list_requires_staff(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse("archive:home"))
		self.assertEqual(response.status_code, 403)

	def test_staff_can_view_subject_list(self):
		self.client.force_login(self.staff)
		response = self.client.get(reverse("archive:subjects"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Doe")

	def test_staff_can_view_subject_detail(self):
		self.client.force_login(self.staff)
		response = self.client.get(
			reverse("archive:subject-detail", args=[self.subject.pk])
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Add record")

	def test_staff_can_create_record(self):
		self.client.force_login(self.staff)
		url = reverse("archive:record-add", args=[self.subject.pk])
		payload = {
			"encounter": self.encounter.pk,
			"collection": self.collection.pk,
			"record_type": self.record_type.pk,
			"ingestion_mode": "upload",
			"physical_location_box": "Box 1",
		}
		file_payload = {
			"upload": SimpleUploadedFile("test.txt", b"hello"),
		}
		response = self.client.post(url, {**payload, **file_payload})
		self.assertEqual(response.status_code, 302)
		self.assertTrue(Record.objects.filter(encounter=self.encounter).exists())
		self.assertIn(
			reverse("archive:subject-detail", args=[self.subject.pk]),
			response.headers.get("Location", ""),
		)
