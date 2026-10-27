import io
import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import UserProfile
from institutions.models import Institution, ProgrammeCourse, FacultyMember
from applications.models import Application, ApplicationHistory
from applications.services import WorkflowEngine
from documents.models import ApplicationDocument, validate_file_security
from compliance.models import ComplianceRule, ComplianceResult
from compliance.services import ComplianceEngine, seed_default_compliance_rules
from notifications.services import send_notification
from notifications.models import Notification
from audit.models import AuditLog
from audit.services import log_activity, sanitize_audit_details


class AICTEWorkflowFullTestSuite(TestCase):

    def setUp(self):
        # 1. Create Institution User A
        self.user_a = User.objects.create_user(
            username='college_a',
            email='principal@college-a.edu',
            password='Password@123'
        )
        self.profile_a, _ = UserProfile.objects.get_or_create(user=self.user_a)
        self.profile_a.role = 'INSTITUTION'
        self.profile_a.save()

        self.inst_a = Institution.objects.create(
            user=self.user_a,
            name='College of Engineering Alpha',
            land_area_acres=3.0,
            built_up_area_sqm=5000.0,
            library_volumes=8000
        )

        # 2. Create Institution User B
        self.user_b = User.objects.create_user(
            username='college_b',
            email='director@college-b.edu',
            password='Password@123'
        )
        self.profile_b, _ = UserProfile.objects.get_or_create(user=self.user_b)
        self.profile_b.role = 'INSTITUTION'
        self.profile_b.save()

        self.inst_b = Institution.objects.create(
            user=self.user_b,
            name='Polytechnic Institute Beta',
            land_area_acres=2.0,
            built_up_area_sqm=3000.0,
            library_volumes=3000
        )

        # 3. Create Scrutiny Officer
        self.officer = User.objects.create_user(
            username='officer_sharma',
            email='sharma@aicte.gov.in',
            password='Password@123',
            is_staff=True
        )
        self.officer_profile, _ = UserProfile.objects.get_or_create(user=self.officer)
        self.officer_profile.role = 'OFFICER'
        self.officer_profile.save()
        self.officer.refresh_from_db()

        # Seed compliance rules
        seed_default_compliance_rules()

    def test_login_and_role_redirect(self):
        """Tests login and role-based redirect for institution users vs scrutiny officers."""
        client = Client()

        # Institution login
        login_res = client.login(username='college_a', password='Password@123')
        self.assertTrue(login_res)

        response = client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Institution Application Portal')
        client.logout()

        # Scrutiny officer login
        client.login(username='officer_sharma', password='Password@123')
        officer_res = client.get(reverse('dashboard'))
        self.assertEqual(officer_res.status_code, 302)
        self.assertEqual(officer_res.url, reverse('officer_dashboard'))

    def test_institution_data_isolation(self):
        """Institution User B MUST NOT be able to view or edit Institution User A's application."""
        app_a = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            status='DRAFT'
        )

        client = Client()
        client.login(username='college_b', password='Password@123')

        # Try to access application detail of College A
        response = client.get(reverse('application_detail', kwargs={'pk': app_a.id}))
        # Must be redirected with access denied error
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

    def test_application_creation_and_submission_workflow(self):
        """Tests full lifecycle: Draft -> Submitted -> In Scrutiny -> Approved."""
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            total_intake=120,
            total_faculty=8,
            status='DRAFT'
        )
        self.assertEqual(app.status, 'DRAFT')

        # 1. Institution submits draft
        WorkflowEngine.transition(
            application=app,
            new_status='SUBMITTED',
            user=self.user_a,
            comments='Submitted by applicant'
        )
        app.refresh_from_db()
        self.assertEqual(app.status, 'SUBMITTED')
        self.assertIsNotNone(app.submitted_at)

        # 2. Officer takes into scrutiny
        WorkflowEngine.transition(
            application=app,
            new_status='IN_SCRUTINY',
            user=self.officer,
            comments='Scrutiny started'
        )
        app.refresh_from_db()
        self.assertEqual(app.status, 'IN_SCRUTINY')

        # 3. Officer recommends approval
        WorkflowEngine.transition(
            application=app,
            new_status='APPROVED',
            user=self.officer,
            comments='Full compliance verified'
        )
        app.refresh_from_db()
        self.assertEqual(app.status, 'APPROVED')
        self.assertIsNotNone(app.completed_at)

        # Verify application history records
        history_count = ApplicationHistory.objects.filter(application=app).count()
        self.assertEqual(history_count, 3)

    def test_unauthorized_approval_attempt_blocked(self):
        """An institution applicant must NOT be allowed to approve their own application."""
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            status='IN_SCRUTINY'
        )

        with self.assertRaises(ValidationError):
            WorkflowEngine.transition(
                application=app,
                new_status='APPROVED',
                user=self.user_a,  # Institution user attempting approval!
                comments='Self approval'
            )

    def test_invalid_transition_blocked(self):
        """Cannot jump from DRAFT directly to APPROVED."""
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            status='DRAFT'
        )

        with self.assertRaises(ValidationError):
            WorkflowEngine.transition(
                application=app,
                new_status='APPROVED',
                user=self.officer,
                comments='Invalid jump'
            )

    def test_document_security_and_extension_validation(self):
        """Prohibits dangerous executable uploads and verifies file validator."""
        fake_exe = SimpleUploadedFile("malicious.exe", b"binarycontent", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_file_security(fake_exe)

        fake_pdf = SimpleUploadedFile("valid_deed.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        # Should not raise
        validate_file_security(fake_pdf)

    def test_compliance_engine_faculty_student_ratio(self):
        """Tests that only an explicitly verified configured ratio is automated."""
        ComplianceRule.objects.create(
            rule_code='TEST_STUDENT_FACULTY_RATIO',
            name='Test student-to-faculty ratio',
            category='FACULTY',
            programme_category='All',
            regulatory_reference='Test fixture source citation',
            effective_date=datetime.date.today(),
            parameter_name='student_faculty_ratio',
            threshold_value=20.0,
            is_source_verified=True,
        )
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            total_intake=120,
            total_faculty=8,  # ratio is 120/8 = 15 <= 20 -> PASS
            status='SUBMITTED'
        )

        results = ComplianceEngine.evaluate_application(app)
        sfr_result = app.compliance_results.filter(check_name__icontains='Ratio').first()
        self.assertIsNotNone(sfr_result)
        self.assertEqual(sfr_result.status, 'PASS')

    def test_unverified_rules_remain_manual_review(self):
        ComplianceRule.objects.create(
            rule_code='TEST_UNVERIFIED_RATIO',
            name='Unverified ratio',
            category='FACULTY',
            programme_category='All',
            regulatory_reference='Unverified test source',
            effective_date=datetime.date.today(),
            parameter_name='student_faculty_ratio',
            threshold_value=1.0,
            is_active=True,
        )
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            total_intake=120,
            total_faculty=8,
            status='SUBMITTED'
        )

        ComplianceEngine.evaluate_application(app)
        ratio_result = app.compliance_results.get(check_name='Student-to-Faculty Ratio (SFR)')
        self.assertEqual(ratio_result.status, 'MANUAL_REVIEW_REQUIRED')
        self.assertIsNone(ratio_result.rule)

    def test_draft_edit_persists_and_preserves_application_number(self):
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            total_intake=120,
            total_faculty=8,
        )
        application_number = app.application_number
        client = Client()
        client.force_login(self.user_a)

        response = client.post(
            reverse('edit_application', kwargs={'pk': app.pk}),
            {
                'institution_name': 'College of Engineering Alpha Updated',
                'application_type': 'EOA',
                'academic_year': '2027-2028',
                'total_intake': 180,
                'total_faculty': 12,
            },
        )

        self.assertRedirects(response, reverse('application_detail', kwargs={'pk': app.pk}))
        app.refresh_from_db()
        self.assertEqual(app.status, 'DRAFT')
        self.assertEqual(app.application_number, application_number)
        self.assertEqual(app.institution_name, 'College of Engineering Alpha Updated')
        self.assertEqual(app.total_intake, 180)
        self.assertEqual(app.academic_year, '2027-2028')

    def test_institution_cannot_skip_required_review_transitions(self):
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            status='DEFICIENCY_FLAGGED',
        )

        with self.assertRaises(ValidationError):
            WorkflowEngine.transition(
                application=app,
                new_status='IN_SCRUTINY',
                user=self.user_a,
                comments='No clarification response was submitted',
            )
        with self.assertRaises(ValidationError):
            WorkflowEngine.transition(
                application=app,
                new_status='SUBMITTED',
                user=self.user_a,
                comments='Attempt to skip scrutiny',
            )

    def test_other_institution_cannot_resume_flagged_application(self):
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            status='DEFICIENCY_FLAGGED',
            clarification_response='Clarification saved by the applicant.',
        )

        with self.assertRaises(ValidationError):
            WorkflowEngine.transition(
                application=app,
                new_status='IN_SCRUTINY',
                user=self.user_b,
                comments='Attempt to resume another institution application',
            )

    def test_application_number_is_unique_for_separate_drafts(self):
        first = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
        )
        second = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
        )
        self.assertNotEqual(first.application_number, second.application_number)

    def test_notification_deduplication(self):
        """Verifies deadline notifications are deduplicated within 24 hours."""
        app = Application.objects.create(
            applicant=self.user_a,
            institution=self.inst_a,
            institution_name=self.inst_a.name,
            status='SUBMITTED'
        )

        # First alert created
        n1 = send_notification(
            recipient=self.user_a,
            title='Deadline Alert',
            message='Please review documents',
            notification_type='DEADLINE_ALERT',
            application=app,
            deduplicate_hours=24
        )
        self.assertIsNotNone(n1)

        # Immediate second alert for same application is suppressed
        n2 = send_notification(
            recipient=self.user_a,
            title='Deadline Alert',
            message='Please review documents',
            notification_type='DEADLINE_ALERT',
            application=app,
            deduplicate_hours=24
        )
        self.assertIsNone(n2)

    def test_audit_log_security_sanitization(self):
        """Ensures audit service records events and redacts sensitive passwords."""
        details = {
            'username': 'test_user',
            'password': 'SuperSecretPassword123!',
            'action': 'sample_test'
        }
        sanitized = sanitize_audit_details(details)
        self.assertEqual(sanitized['password'], '[REDACTED]')

        log = log_activity(
            actor=self.user_a,
            action='LOGIN',
            target_model='User',
            target_id=str(self.user_a.id),
            summary='User login test',
            details=details
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.details['password'], '[REDACTED]')
