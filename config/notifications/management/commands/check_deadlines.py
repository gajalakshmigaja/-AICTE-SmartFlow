import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User

from applications.models import Application
from documents.models import ApplicationDocument
from notifications.services import send_notification


class Command(BaseCommand):
    help = 'Checks application deadlines and document expiry dates, creating deduplicated in-app and email alerts.'

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()
        self.stdout.write(self.style.NOTICE(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Starting AICTE SmartFlow deadline checker..."))

        alerts_created = 0

        # 1. Overdue Scrutiny Alerts (>7 days in SUBMITTED or IN_SCRUTINY)
        cutoff_date = now - datetime.timedelta(days=7)
        overdue_apps = Application.objects.filter(
            status__in=['SUBMITTED', 'IN_SCRUTINY'],
            created_at__lte=cutoff_date
        )

        officers = User.objects.filter(profile__role__in=['OFFICER', 'DIRECTOR', 'ADMIN']) | User.objects.filter(is_superuser=True)
        distinct_officers = set(officers)

        for app in overdue_apps:
            days_pending = (now - (app.submitted_at or app.created_at)).days
            title = f"OVERDUE ALERT: {app.application_number} pending for {days_pending} days"
            message = (
                f"Application {app.application_number} ({app.institution_name}) has been in '{app.get_status_display()}' "
                f"status for {days_pending} days, exceeding the 7-day scrutiny processing window. Immediate action required."
            )

            # Notify assigned officer or all officers
            recipients = [app.assigned_officer] if app.assigned_officer else distinct_officers
            for officer in recipients:
                if officer:
                    res = send_notification(
                        recipient=officer,
                        title=title,
                        message=message,
                        notification_type='DEADLINE_ALERT',
                        application=app,
                        action_url=f"/officer/review/{app.id}/",
                        deduplicate_hours=24  # Avoid duplicates within 24 hours!
                    )
                    if res:
                        alerts_created += 1

        # 2. Document Expiry Alerts (expiring in <= 30 days or already expired)
        warning_window = today + datetime.timedelta(days=30)
        expiring_docs = ApplicationDocument.objects.filter(
            expiry_date__isnull=False,
            expiry_date__lte=warning_window,
            application__status__in=['DRAFT', 'SUBMITTED', 'IN_SCRUTINY', 'DEFICIENCY_FLAGGED']
        )

        for doc in expiring_docs:
            days_left = (doc.expiry_date - today).days
            app = doc.application

            if days_left < 0:
                title = f"EXPIRED CERTIFICATE: {doc.title}"
                message = f"The regulatory certificate '{doc.title}' for application {app.application_number} expired on {doc.expiry_date}. Please upload a renewed valid document immediately."
            else:
                title = f"UPCOMING EXPIRY: {doc.title} expires in {days_left} days"
                message = f"The regulatory certificate '{doc.title}' for application {app.application_number} is scheduled to expire on {doc.expiry_date} ({days_left} days remaining)."

            # Notify applicant
            res = send_notification(
                recipient=app.applicant,
                title=title,
                message=message,
                notification_type='DOCUMENT_EXPIRY',
                application=app,
                action_url=f"/applications/{app.id}/",
                deduplicate_hours=24
            )
            if res:
                alerts_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Deadline check complete. Evaluated {overdue_apps.count()} overdue applications and {expiring_docs.count()} expiring documents. Created {alerts_created} new alerts."
        ))
