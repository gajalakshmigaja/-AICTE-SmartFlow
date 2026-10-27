from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('APPLICATION_CREATED', 'Application Created'),
        ('APPLICATION_SUBMITTED', 'Application Submitted'),
        ('STATUS_CHANGE', 'Application Status Transition'),
        ('DOCUMENT_UPLOAD', 'Document Uploaded'),
        ('DOCUMENT_REPLACE', 'Document Replaced'),
        ('DOCUMENT_VERIFIED', 'Document Verified'),
        ('COMPLIANCE_RUN', 'Compliance Evaluation Executed'),
        ('ROLE_CHANGED', 'User Role / Permissions Modified'),
        ('SYSTEM_EVENT', 'System / Administrative Event'),
    ]

    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_actions'
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    summary = models.TextField()
    ip_address = models.CharField(max_length=50, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {actor_name} - {self.action} ({self.target_id})"
