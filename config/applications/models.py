import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Application(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('IN_SCRUTINY', 'In Scrutiny'),
        ('DEFICIENCY_FLAGGED', 'Deficiency Flagged'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    APPLICATION_TYPES = [
        ('EOA', 'Extension of Approval (EOA)'),
        ('NEW_INSTITUTION', 'Setting up New Technical Institution'),
        ('INCREASE_INTAKE', 'Increase in Intake / Additional Course'),
        ('NEW_PROGRAMME', 'Introduction of New Programme'),
    ]

    institution = models.ForeignKey(
        'institutions.Institution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications'
    )
    institution_name = models.CharField(max_length=200)
    application_number = models.CharField(
        max_length=30, unique=True, blank=True
    )
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    application_type = models.CharField(
        max_length=50,
        choices=APPLICATION_TYPES,
        default='EOA'
    )
    academic_year = models.CharField(max_length=20, default='2026-2027')

    total_intake = models.PositiveIntegerField(default=0)
    total_faculty = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    assigned_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_scrutiny_apps'
    )

    deficiency_notes = models.TextField(blank=True)
    clarification_requested = models.TextField(blank=True)
    clarification_response = models.TextField(blank=True)
    approval_remarks = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    scrutiny_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.application_number:
            year = timezone.now().year
            code = uuid.uuid4().hex[:8].upper()
            self.application_number = f"AICTE-{year}-{code}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.application_number} - {self.institution_name} ({self.get_status_display()})"

    @property
    def can_edit(self):
        """Institution can edit draft or respond to deficiency notes."""
        return self.status in ['DRAFT', 'DEFICIENCY_FLAGGED']

    @property
    def is_terminal(self):
        return self.status in ['APPROVED', 'REJECTED']

    @property
    def is_overdue(self):
        """Flag application if awaiting review for more than 7 days."""
        if self.status in ['SUBMITTED', 'IN_SCRUTINY']:
            ref_date = self.submitted_at or self.created_at
            return (timezone.now() - ref_date).days >= 7
        return False


class ApplicationHistory(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='history'
    )
    previous_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)
    action_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='application_actions'
    )
    action_type = models.CharField(max_length=50, default='STATUS_CHANGE')
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application.application_number}: {self.previous_status} -> {self.new_status} by {self.action_by}"