import shutil
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import GenerationJob, RecipientCertificate

@override_settings(MEDIA_ROOT="/tmp/certificate-generator-tests")
class CertificateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "course_name": "Django Fundamentals",
            "completion_date": "2026-10-08",
            "issuer_name": "Acme Academy",
            "recipients": [
                {"name": "Ada Lovelace", "email": "ada@example.com"},
                {"name": "Grace Hopper", "email": "grace@example.com"},
            ],
        }

    def tearDown(self):
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            shutil.rmtree(media_root)

    def test_create_job_generates_all_certificates_and_reports_progress(self):
        response = self.client.post("/api/jobs/", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(response.data["progress_percent"], 100)
        self.assertEqual(response.data["success_count"], 2)
        self.assertEqual(len(response.data["recipients"]), 2)
        self.assertTrue(response.data["recipients"][0]["download_url"])

    def test_input_validation(self):
        invalid = {**self.payload, "recipients": [{"name": ""}]}
        response = self.client.post("/api/jobs/", invalid, format="json")
        self.assertEqual(response.status_code, 400)

    def test_certificate_file_is_generated(self):
        response = self.client.post("/api/jobs/", self.payload, format="json")

        self.assertEqual(response.status_code, 201)

        recipient = RecipientCertificate.objects.get(
            id=response.data["recipients"][0]["id"]
        )

        self.assertTrue(recipient.file)
        self.assertTrue(Path(recipient.file.path).exists())
        
    @patch("certificates.services.render_certificate")
    def test_one_generation_failure_does_not_stop_other_recipients(self, render):
        def fail_for_first(job, recipient):
            if recipient.name == "Ada Lovelace":
                raise ValueError("template rendering failed")
            return b"%PDF-1.4 generated"

        render.side_effect = fail_for_first
        response = self.client.post("/api/jobs/", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "completed_with_errors")
        self.assertEqual(response.data["success_count"], 1)
        self.assertEqual(response.data["failure_count"], 1)
        failed = next(r for r in response.data["recipients"] if r["name"] == "Ada Lovelace")
        self.assertEqual(failed["status"], "failed")
        self.assertIn("template rendering failed", failed["error_message"])

    def test_retrieve_job_and_certificate(self):
        create_response = self.client.post("/api/jobs/", self.payload, format="json")
        job_id = create_response.data["id"]
        recipient_id = create_response.data["recipients"][0]["id"]
        detail = self.client.get("/api/jobs/%s/" % job_id)
        self.assertEqual(detail.status_code, 200)
        download = self.client.get(
            "/api/jobs/%s/certificates/%s/download/" % (job_id, recipient_id)
        )
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/pdf")
        content = b"".join(download.streaming_content)
        self.assertTrue(content)
        self.assertTrue(content.startswith(b"%PDF"))

    def test_job_status_counts_are_persisted(self):
        response = self.client.post("/api/jobs/", self.payload, format="json")
        job = GenerationJob.objects.get(pk=response.data["id"])
        self.assertEqual(job.total_count, 2)
        self.assertEqual(job.recipients.filter(status="generated").count(), 2)
