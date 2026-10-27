from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Application, ApplicationHistory


class WorkflowEngine:
    """
    Automates and enforces valid state transitions in the AICTE Approval Workflow.
    Valid transitions:
    DRAFT -> SUBMITTED
    SUBMITTED -> IN_SCRUTINY
    IN_SCRUTINY -> DEFICIENCY_FLAGGED, APPROVED, REJECTED
    DEFICIENCY_FLAGGED -> IN_SCRUTINY
    APPROVED -> Terminal
    REJECTED -> Terminal
    """

    ALLOWED_TRANSITIONS = {
        'DRAFT': ['SUBMITTED'],
        'SUBMITTED': ['IN_SCRUTINY'],
        'IN_SCRUTINY': ['DEFICIENCY_FLAGGED', 'APPROVED', 'REJECTED'],
        'DEFICIENCY_FLAGGED': ['IN_SCRUTINY'],
        'APPROVED': [],
        'REJECTED': [],
    }

    @classmethod
    def can_transition(cls, current_status, new_status, user):
        """Validate if the user and current status permit the transition."""
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            return False, f"Transition from {current_status} to {new_status} is not allowed."

        role = getattr(getattr(user, 'profile', None), 'role', '')
        is_reviewer = user.is_superuser or role in ['OFFICER', 'DIRECTOR', 'ADMIN']

        if current_status == 'DRAFT' and new_status == 'SUBMITTED':
            return role == 'INSTITUTION', (
                'Only institution users can submit draft applications.'
                if role != 'INSTITUTION' else 'Valid transition'
            )

        if current_status == 'DEFICIENCY_FLAGGED' and new_status == 'IN_SCRUTINY':
            return is_reviewer or role == 'INSTITUTION', (
                'Only the applicant or an authorized reviewer can resume scrutiny.'
                if not (is_reviewer or role == 'INSTITUTION') else 'Valid transition'
            )

        if not is_reviewer:
            return False, "Only authorized scrutiny officers and administrators can make review decisions."

        return True, "Valid transition"

    @classmethod
    @transaction.atomic
    def transition(cls, application, new_status, user, comments='', action_type='STATUS_CHANGE'):
        """Executes the state transition with audit history and notification dispatch."""
        current_status = application.status

        is_valid, reason = cls.can_transition(current_status, new_status, user)
        if not is_valid:
            raise ValidationError(reason)
        if current_status == 'DRAFT' and new_status == 'SUBMITTED' and application.applicant_id != user.id:
            raise ValidationError("Only the applicant can submit this draft.")
        if current_status == 'DEFICIENCY_FLAGGED' and new_status == 'IN_SCRUTINY':
            role = getattr(getattr(user, 'profile', None), 'role', '')
            if role == 'INSTITUTION' and application.applicant_id != user.id:
                raise ValidationError("Only the applicant can submit a clarification response.")
            is_applicant = application.applicant_id == user.id
            if is_applicant and not application.clarification_response.strip():
                raise ValidationError("Submit a clarification response before resuming scrutiny.")

        previous_status = current_status
        application.status = new_status

        now = timezone.now()
        if new_status == 'SUBMITTED':
            application.submitted_at = now
        elif new_status == 'IN_SCRUTINY':
            if not application.scrutiny_started_at:
                application.scrutiny_started_at = now
            if not application.assigned_officer and user.is_authenticated and not user.is_superuser:
                # Assign to reviewing officer if not assigned
                profile = getattr(user, 'profile', None)
                if profile and profile.role == 'OFFICER':
                    application.assigned_officer = user
        elif new_status == 'DEFICIENCY_FLAGGED':
            application.deficiency_notes = comments
            application.clarification_requested = comments
        elif new_status == 'APPROVED':
            application.approval_remarks = comments
            application.completed_at = now
        elif new_status == 'REJECTED':
            application.rejection_reason = comments
            application.completed_at = now

        application.save()

        # Record Application History
        history = ApplicationHistory.objects.create(
            application=application,
            previous_status=previous_status,
            new_status=new_status,
            action_by=user,
            action_type=action_type,
            comments=comments
        )

        from notifications.services import notify_application_status_change
        notify_application_status_change(application, previous_status, new_status, comments)

        from audit.services import log_activity
        log_activity(
            actor=user,
            action='STATUS_CHANGE',
            target_model='Application',
            target_id=application.application_number,
            summary=f'Application status changed from {previous_status} to {new_status}',
            details={'previous': previous_status, 'new': new_status, 'comments': comments}
        )

        return history
