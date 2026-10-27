from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('SUBMISSION', 'Application Submission'),
        ('ASSIGNMENT', 'Application Assigned for Scrutiny'),
        ('DEFICIENCY', 'Deficiency Flagged'),
        ('CLARIFICATION', 'Clarification Response Received'),
        ('STATUS_CHANGE', 'Status Change'),
        ('DEADLINE_ALERT', 'Upcoming / Overdue Review Deadline'),
        ('DOCUMENT_EXPIRY', 'Document Expiry Warning'),
        ('SYSTEM', 'System Alert'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default='SYSTEM'
    )
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    action_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title} -> {self.recipient.username}"
