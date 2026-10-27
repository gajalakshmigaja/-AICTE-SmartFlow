import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from applications.models import Application
from compliance.models import ComplianceRule
from compliance.services import ComplianceEngine, seed_default_compliance_rules
from institutions.models import Institution, ProgrammeCourse


class ComplianceRuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='compliance_director',
            password='SecurePass123!',
        )
        self.user.profile.role = 'DIRECTOR'
        self.user.profile.save()
        self.institution = Institution.objects.create(
            user=self.user,
            name='Compliance Test Institution',
            state='Tamil Nadu',
            district='Chennai',
        )
        self.application = Application.objects.create(
            applicant=self.user,
            institution=self.institution,
            institution_name=self.institution.name,
            total_intake=120,
            total_faculty=8,
            status='SUBMITTED',
        )
        self.client.force_login(self.user)

    def test_admin_can_create_and_edit_configured_rule(self):
        response = self.client.post(
            reverse('create_compliance_rule'),
            {
                'rule_code': 'CONFIGURED_LAND_THRESHOLD',
                'name': 'Configured land threshold',
                'category': 'LAND_BUILDING',
                'programme_category': 'All',
                'regulatory_reference': 'Verified source test citation',
                'effective_date': datetime.date.today().isoformat(),
                'parameter_name': 'min_land_acres',
                'threshold_value': '3.0',
                'is_mandatory': 'on',
                'is_active': 'on',
                'is_source_verified': 'on',
                'description': 'Test rule.',
            },
        )
        self.assertRedirects(response, reverse('compliance_rules'))
        rule = ComplianceRule.objects.get(rule_code='CONFIGURED_LAND_THRESHOLD')
        self.assertTrue(rule.is_source_verified)
        self.assertEqual(rule.threshold_value, 3.0)
        self.assertEqual(
            ComplianceEngine._active_rule('min_land_acres', self.application),
            rule,
        )

        edit_response = self.client.post(
            reverse('edit_compliance_rule', kwargs={'pk': rule.pk}),
            {
                'rule_code': rule.rule_code,
                'name': 'Updated land threshold',
                'category': 'LAND_BUILDING',
                'programme_category': 'All',
                'regulatory_reference': 'Updated verified source citation',
                'effective_date': datetime.date.today().isoformat(),
                'parameter_name': 'min_land_acres',
                'threshold_value': '3.5',
                'is_mandatory': 'on',
                'is_active': 'on',
                'is_source_verified': 'on',
                'description': 'Updated test rule.',
            },
        )
        self.assertRedirects(edit_response, reverse('compliance_rules'))
        rule.refresh_from_db()
        self.assertEqual(rule.name, 'Updated land threshold')
        self.assertEqual(rule.threshold_value, 3.5)

    def test_future_or_unverified_rules_are_not_applied(self):
        rule = ComplianceRule.objects.create(
            rule_code='FUTURE_TEST_RULE',
            name='Future test rule',
            category='LAND_BUILDING',
            programme_category='All',
            regulatory_reference='Test source citation',
            effective_date=datetime.date.today() + datetime.timedelta(days=1),
            parameter_name='min_land_acres',
            threshold_value=100.0,
            is_source_verified=True,
        )
        self.assertIsNone(
            ComplianceEngine._active_rule('min_land_acres', self.application)
        )

        rule.effective_date = datetime.date.today()
        rule.is_source_verified = False
        rule.save()
        self.assertIsNone(
            ComplianceEngine._active_rule('min_land_acres', self.application)
        )

    def test_programme_specific_rule_takes_precedence_over_general_rule(self):
        general_rule = ComplianceRule.objects.create(
            rule_code='GENERAL_LAND_THRESHOLD',
            name='General land threshold',
            category='LAND_BUILDING',
            programme_category='All',
            regulatory_reference='General test source',
            effective_date=datetime.date.today(),
            parameter_name='min_land_acres',
            threshold_value=2.0,
            is_source_verified=True,
        )
        specific_rule = ComplianceRule.objects.create(
            rule_code='ENGINEERING_LAND_THRESHOLD',
            name='Engineering land threshold',
            category='LAND_BUILDING',
            programme_category='Engineering & Technology',
            regulatory_reference='Programme-specific test source',
            effective_date=datetime.date.today(),
            parameter_name='min_land_acres',
            threshold_value=4.0,
            is_source_verified=True,
        )
        ProgrammeCourse.objects.create(
            institution=self.institution,
            programme='ENGG_TECH',
            course_name='Engineering',
        )

        selected_rule = ComplianceEngine._active_rule(
            'min_land_acres',
            self.application,
        )
        self.assertEqual(selected_rule, specific_rule)
        self.assertNotEqual(selected_rule, general_rule)

    def test_verified_fire_safety_rule_requires_verified_document(self):
        ComplianceRule.objects.create(
            rule_code='FIRE_SAFETY_VALIDITY',
            name='Fire safety validity',
            category='ADMINISTRATIVE',
            programme_category='All',
            regulatory_reference='Fire safety test source',
            effective_date=datetime.date.today(),
            parameter_name='fire_safety_active',
            threshold_value=1,
            is_source_verified=True,
        )

        ComplianceEngine.evaluate_application(self.application)
        result = self.application.compliance_results.get(
            check_name='Certificate Expiry & Statutory Validity'
        )
        self.assertEqual(result.status, 'MANUAL_REVIEW_REQUIRED')

    def test_default_seed_does_not_create_unverified_regulatory_claims(self):
        seed_default_compliance_rules()
        self.assertFalse(ComplianceRule.objects.exists())

        ComplianceEngine.evaluate_application(self.application)
        result = self.application.compliance_results.get(
            check_name='Land Area Verification'
        )
        self.assertEqual(result.status, 'MANUAL_REVIEW_REQUIRED')
        self.assertEqual(result.regulatory_reference, '')
