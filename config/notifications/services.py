from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

from .models import Notification


def send_notification(recipient, title, message, notification_type='SYSTEM', application=None, action_url='', deduplicate_hours=None):
    """
    Creates an in-app notification and dispatches an email.
    If deduplicate_hours is specified, avoids creating duplicate alerts of the same type
    for the same application within that time window.
    """
    if deduplicate_hours and application:
        cutoff = timezone.now() - timedelta(hours=deduplicate_hours)
        existing = Notification.objects.filter(
            recipient=recipient,
            application=application,
            notification_type=notification_type,
            created_at__gte=cutoff
        ).exists()
        if existing:
            return None

    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        application=application,
        action_url=action_url
    )

    # Dispatch email notification safely
    if recipient.email:
        try:
            subject = f"[AICTE SmartFlow] {title}"
            email_body = f"""Dear {recipient.first_name or recipient.username},

{message}

Application Reference: {application.application_number if application else 'N/A'}
Date & Time: {notification.created_at.strftime('%d-%b-%Y %H:%M UTC')}

You can view the details directly on the AICTE SmartFlow portal:
http://localhost:8000{action_url or '/'}

---
AICTE SmartFlow Automated Notification Service
Note: This is an automated email. Please do not reply directly to this message.
"""
            send_mail(
                subject=subject,
                message=email_body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@aicte-smartflow.gov.in'),
                recipient_list=[recipient.email],
                fail_silently=True
            )
        except Exception:
            pass

    return notification


def notify_application_submitted(application):
    # Notify applicant
    send_notification(
        recipient=application.applicant,
        title="Application Successfully Submitted",
        message=f"Your application {application.application_number} for {application.institution_name} has been submitted for scrutiny.",
        notification_type='SUBMISSION',
        application=application,
        action_url=f"/applications/{application.id}/"
    )

    # Notify Scrutiny Officers / Admins
    officers = User.objects.filter(profile__role__in=['OFFICER', 'DIRECTOR', 'ADMIN']) | User.objects.filter(is_superuser=True)
    for officer in set(officers):
        send_notification(
            recipient=officer,
            title="New Application Submitted for Scrutiny",
            message=f"Application {application.application_number} ({application.institution_name}) has been submitted and is awaiting assignment.",
            notification_type='SUBMISSION',
            application=application,
            action_url=f"/officer/review/{application.id}/"
        )


def notify_application_status_change(application, previous_status, new_status, comments=""):
    title = f"Application Status Updated: {application.get_status_display()}"
    msg = f"Application {application.application_number} status changed from {previous_status} to {new_status}."
    if comments:
        msg += f"\nReviewer remarks: {comments}"

    # Notify Applicant
    send_notification(
        recipient=application.applicant,
        title=title,
        message=msg,
        notification_type='STATUS_CHANGE',
        application=application,
        action_url=f"/applications/{application.id}/"
    )

    # If assigned officer exists and wasn't the actor, notify them too
    if application.assigned_officer and application.assigned_officer != application.applicant:
        send_notification(
            recipient=application.assigned_officer,
            title=title,
            message=msg,
            notification_type='STATUS_CHANGE',
            application=application,
            action_url=f"/officer/review/{application.id}/"
        )
