from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from institutions.models import Institution


class AccountWorkflowTests(TestCase):
    def test_institution_registration_creates_linked_profile(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'registered_institution',
                'email': 'registrar@example.test',
                'first_name': 'Principal',
                'last_name': 'Example',
                'institution_name': 'Registered College',
                'contact_phone': '+91 9876543210',
                'regional_office': 'SOUTH',
                'password': 'StrongPass123!',
                'confirm_password': 'StrongPass123!',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='registered_institution')
        self.assertEqual(user.profile.role, 'INSTITUTION')
        self.assertEqual(user.institution_profile.name, 'Registered College')
        self.assertTrue(Institution.objects.filter(user=user).exists())

    def test_logout_requires_post(self):
        user = User.objects.create_user(
            username='logout_user',
            password='SecurePass123!',
        )
        self.client.force_login(user)

        get_response = self.client.get(reverse('logout'))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse('logout'))
        self.assertRedirects(post_response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)
