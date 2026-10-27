from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification


class NotificationActionTests(TestCase):
    def setUp(self):
        self.recipient = User.objects.create_user(
            username='notification_owner',
            password='SecurePass123!',
        )
        self.other_user = User.objects.create_user(
            username='notification_other',
            password='SecurePass123!',
        )
        self.notification = Notification.objects.create(
            recipient=self.recipient,
            title='Status update',
            message='Application status changed.',
            action_url='/',
        )

    def test_read_actions_require_post_and_are_recipient_scoped(self):
        self.client.force_login(self.other_user)
        wrong_recipient = self.client.post(
            reverse(
                'mark_notification_read',
                kwargs={'pk': self.notification.pk},
            )
        )
        self.assertEqual(wrong_recipient.status_code, 404)

        self.client.force_login(self.recipient)
        get_response = self.client.get(
            reverse(
                'mark_notification_read',
                kwargs={'pk': self.notification.pk},
            )
        )
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(
            reverse(
                'mark_notification_read',
                kwargs={'pk': self.notification.pk},
            )
        )
        self.assertRedirects(post_response, '/')
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
