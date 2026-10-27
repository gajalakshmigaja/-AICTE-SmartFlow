import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from applications.models import Application
from documents.models import AIDocumentAnalysis, ApplicationDocument
from institutions.models import Institution


class DocumentWorkflowTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        media_override = override_settings(MEDIA_ROOT=self.temp_dir.name)
        media_override.enable()
        self.addCleanup(media_override.disable)

        self.applicant = User.objects.create_user(
            username='document_applicant',
            password='SecurePass123!',
        )
        self.institution = Institution.objects.create(
            user=self.applicant,
            name='Document Test Institution',
            state='Tamil Nadu',
            district='Chennai',
        )
        self.application = Application.objects.create(
            applicant=self.applicant,
            institution=self.institution,
            institution_name=self.institution.name,
            total_intake=60,
            total_faculty=5,
        )
        self.client.force_login(self.applicant)

    @staticmethod
    def pdf_upload(name, content=b'%PDF-1.4\nSmartFlow test file'):
        return SimpleUploadedFile(name, content, content_type='application/pdf')

    def test_upload_is_private_and_download_checks_ownership(self):
        response = self.client.post(
            reverse('upload_document', kwargs={'app_id': self.application.pk}),
            {
                'document_type': 'LAND_DEED',
                'title': 'Land deed',
                'file': self.pdf_upload('land-deed.pdf'),
                'expiry_date': '',
            },
        )
        self.assertRedirects(
            response,
            reverse('application_detail', kwargs={'pk': self.application.pk}),
        )
        document = ApplicationDocument.objects.get(application=self.application)
        self.assertEqual(document.file_size, len(b'%PDF-1.4\nSmartFlow test file'))
        self.assertTrue(document.file_hash)
        self.assertEqual(
            self.client.get(f'/media/{document.file.name}').status_code,
            404,
        )

        other_user = User.objects.create_user(
            username='unrelated_user',
            password='SecurePass123!',
        )
        self.client.force_login(other_user)
        denied = self.client.get(
            reverse('download_document', kwargs={'doc_id': document.pk})
        )
        self.assertEqual(denied.status_code, 403)

        self.client.force_login(self.applicant)
        allowed = self.client.get(
            reverse('download_document', kwargs={'doc_id': document.pk})
        )
        self.assertEqual(allowed.status_code, 200)
        allowed.close()

    def test_replacement_requires_editable_state_and_resets_review(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type='LAND_DEED',
            title='Land deed',
            file=self.pdf_upload('initial.pdf'),
            uploaded_by=self.applicant,
            verification_status='VERIFIED',
            verified_by=self.applicant,
        )
        analysis = AIDocumentAnalysis.objects.create(
            document=document,
            human_verified=True,
            human_verdict='CONFIRMED',
            reviewer_notes='Previously reviewed',
        )
        self.application.status = 'IN_SCRUTINY'
        self.application.save()

        rejected = self.client.post(
            reverse('replace_document', kwargs={'doc_id': document.pk}),
            {'file': self.pdf_upload('blocked.pdf'), 'expiry_date': ''},
        )
        self.assertRedirects(
            rejected,
            reverse('application_detail', kwargs={'pk': self.application.pk}),
        )
        document.refresh_from_db()
        self.assertEqual(document.version, 1)

        self.application.status = 'DEFICIENCY_FLAGGED'
        self.application.save()
        replaced = self.client.post(
            reverse('replace_document', kwargs={'doc_id': document.pk}),
            {'file': self.pdf_upload('replacement.pdf'), 'expiry_date': ''},
        )
        self.assertRedirects(
            replaced,
            reverse('application_detail', kwargs={'pk': self.application.pk}),
        )
        document.refresh_from_db()
        analysis.refresh_from_db()
        self.assertEqual(document.version, 2)
        self.assertEqual(document.verification_status, 'PENDING')
        self.assertIsNone(document.verified_by)
        self.assertIsNone(document.expiry_date)
        self.assertFalse(analysis.human_verified)
        self.assertEqual(analysis.human_verdict, '')
        self.assertEqual(analysis.reviewer_notes, '')

    def test_only_reviewers_can_save_ai_verdicts(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type='LAND_DEED',
            title='Land deed',
            file=self.pdf_upload('review.pdf'),
            uploaded_by=self.applicant,
        )
        analysis = AIDocumentAnalysis.objects.create(document=document)
        response = self.client.post(
            reverse('verify_ai_finding', kwargs={'doc_id': document.pk}),
            {'verdict': 'CONFIRMED', 'reviewer_notes': 'Not authorized'},
        )
        self.assertEqual(response.status_code, 302)
        analysis.refresh_from_db()
        self.assertFalse(analysis.human_verified)

        officer = User.objects.create_user(
            username='document_officer',
            password='SecurePass123!',
        )
        officer.profile.role = 'OFFICER'
        officer.profile.save()
        self.client.force_login(officer)
        invalid = self.client.post(
            reverse('verify_ai_finding', kwargs={'doc_id': document.pk}),
            {'verdict': 'UNRECOGNIZED', 'reviewer_notes': ''},
        )
        self.assertEqual(invalid.status_code, 302)
        analysis.refresh_from_db()
        self.assertFalse(analysis.human_verified)

        saved = self.client.post(
            reverse('verify_ai_finding', kwargs={'doc_id': document.pk}),
            {'verdict': 'CONFIRMED', 'reviewer_notes': 'Reviewed by officer'},
        )
        self.assertEqual(saved.status_code, 302)
        analysis.refresh_from_db()
        self.assertTrue(analysis.human_verified)
        self.assertEqual(analysis.reviewer_notes, 'Reviewed by officer')

    def test_document_verification_is_post_only(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type='LAND_DEED',
            title='Land deed',
            file=self.pdf_upload('post-only.pdf'),
            uploaded_by=self.applicant,
        )
        response = self.client.get(
            reverse('verify_document', kwargs={'doc_id': document.pk})
        )
        self.assertEqual(response.status_code, 405)
