from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db import transaction
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Application, ApplicationHistory
from .forms import ApplicationCreateForm, DeficiencyResponseForm, OfficerReviewActionForm
from .services import WorkflowEngine
from .chatbot_service import search_faq, FAQ_KNOWLEDGE_BASE
from institutions.models import Institution
from compliance.services import ComplianceEngine
from accounts.decorators import (
    institution_required,
    role_required,
    scrutiny_officer_required,
    regional_director_required,
)


@login_required
def dashboard(request):
    """Role-aware dashboard landing router."""
    profile = getattr(request.user, 'profile', None)
    role = getattr(profile, 'role', '')

    if role == 'OFFICER':
        return redirect('officer_dashboard')
    elif role in ['DIRECTOR', 'ADMIN']:
        return redirect('director_dashboard')

    # Default to Institution User Dashboard
    user = request.user
    applications = Application.objects.filter(applicant=user).order_by('-created_at')

    # Fetch or associate institution profile
    institution = getattr(user, 'institution_profile', None)

    context = {
        'total': applications.count(),
        'draft': applications.filter(status='DRAFT').count(),
        'pending': applications.filter(status__in=['SUBMITTED', 'IN_SCRUTINY']).count(),
        'deficiencies': applications.filter(status='DEFICIENCY_FLAGGED').count(),
        'approved': applications.filter(status='APPROVED').count(),
        'rejected': applications.filter(status='REJECTED').count(),
        'applications': applications,
        'institution': institution,
        'faq_items': FAQ_KNOWLEDGE_BASE[:4],
    }

    return render(request, 'applications/dashboard.html', context)


@login_required
@institution_required
def create_application(request):
    user = request.user
    institution = getattr(user, 'institution_profile', None)

    if request.method == 'POST':
        form = ApplicationCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                app = form.save(commit=False)
                app.applicant = user
                if institution:
                    app.institution = institution
                    if not app.institution_name:
                        app.institution_name = institution.name
                app.status = 'DRAFT'
                app.save()

                ApplicationHistory.objects.create(
                    application=app,
                    previous_status='NEW',
                    new_status='DRAFT',
                    action_by=user,
                    action_type='CREATION',
                    comments='Application draft initialized by institution.'
                )
                ComplianceEngine.evaluate_application(app)

            messages.success(
                request,
                f"Application {app.application_number} created as Draft. Review applicable rules and officer requests for supporting records before submission."
            )
            return redirect('application_detail', pk=app.id)
    else:
        initial_data = {}
        if institution:
            initial_data['institution_name'] = institution.name
            initial_data['total_intake'] = institution.total_proposed_intake or 60
            initial_data['total_faculty'] = institution.total_faculty_count or 5

        form = ApplicationCreateForm(initial=initial_data)

    return render(request, 'applications/create_application.html', {
        'form': form,
        'institution': institution
    })


@login_required
@institution_required
def edit_application(request, pk):
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='DRAFT',
    )
    institution = getattr(request.user, 'institution_profile', None)

    if request.method == 'POST':
        form = ApplicationCreateForm(request.POST, instance=application)
        if form.is_valid():
            with transaction.atomic():
                application = form.save(commit=False)
                application.institution = institution
                application.save()
                ComplianceEngine.evaluate_application(application)
            messages.success(request, 'Draft application changes saved.')
            return redirect('application_detail', pk=application.pk)
    else:
        form = ApplicationCreateForm(instance=application)

    return render(request, 'applications/create_application.html', {
        'form': form,
        'institution': institution,
        'application': application,
        'is_edit': True,
    })


@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)

    # Permission check: applicant or staff/officer/director
    profile = getattr(request.user, 'profile', None)
    is_staff_user = request.user.is_superuser or (profile and profile.role in ['OFFICER', 'DIRECTOR', 'ADMIN'])
    if not (application.applicant == request.user or is_staff_user):
        messages.error(request, "Access Denied: You do not have permission to view this application.")
        return redirect('dashboard')

    documents = application.documents.all().order_by('-uploaded_at')
    compliance_results = application.compliance_results.all()
    history = application.history.all()
    institution = application.institution

    deficiency_form = DeficiencyResponseForm()

    context = {
        'application': application,
        'institution': institution,
        'documents': documents,
        'compliance_results': compliance_results,
        'history': history,
        'deficiency_form': deficiency_form,
        'is_staff_user': is_staff_user,
    }
    return render(request, 'applications/application_detail.html', context)


@login_required
@institution_required
@require_POST
def submit_application(request, pk):
    application = get_object_or_404(Application, pk=pk)

    if application.applicant != request.user:
        messages.error(request, "Only the applicant can submit this application.")
        return redirect('application_detail', pk=application.id)

    if application.status != 'DRAFT':
        messages.warning(request, f"Application is currently in '{application.get_status_display()}' and cannot be submitted as a new draft.")
        return redirect('application_detail', pk=application.id)

    try:
        WorkflowEngine.transition(
            application=application,
            new_status='SUBMITTED',
            user=request.user,
            comments='Application formally submitted by institution for regulatory scrutiny.',
            action_type='SUBMISSION'
        )

        ComplianceEngine.evaluate_application(application)

        from notifications.services import notify_application_submitted
        notify_application_submitted(application)

        messages.success(request, f"Application {application.application_number} has been submitted to the SmartFlow review workflow.")
    except ValidationError as e:
        messages.error(request, f"Error submitting application: {str(e)}")

    return redirect('application_detail', pk=application.id)


@login_required
@institution_required
@require_POST
def respond_deficiency(request, pk):
    application = get_object_or_404(Application, pk=pk)

    if application.applicant != request.user:
        messages.error(request, "Only the applicant can respond to deficiencies.")
        return redirect('application_detail', pk=application.id)

    if application.status != 'DEFICIENCY_FLAGGED':
        messages.warning(request, "This application does not currently have active flagged deficiencies.")
        return redirect('application_detail', pk=application.id)

    form = DeficiencyResponseForm(request.POST)
    if form.is_valid():
        clarification = form.cleaned_data['clarification_response']
        application.clarification_response = clarification
        application.save(update_fields=['clarification_response', 'updated_at'])

        WorkflowEngine.transition(
            application=application,
            new_status='IN_SCRUTINY',
            user=request.user,
            comments=f"Institution responded to deficiencies: {clarification[:150]}...",
            action_type='CLARIFICATION_SUBMITTED'
        )

        ComplianceEngine.evaluate_application(application)
        messages.success(request, "Your clarification and updated documents have been submitted to the scrutiny officer.")
        return redirect('application_detail', pk=application.id)

    messages.error(request, 'Please provide a clarification response before submitting.')
    return redirect('application_detail', pk=application.id)


@login_required
@scrutiny_officer_required
def officer_dashboard(request):
    """Dashboard view for Scrutiny Officers."""
    user = request.user

    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()
    queue_filter = request.GET.get('queue', 'all').strip()

    # Scrutiny queues
    seven_days_ago = timezone.now() - timedelta(days=7)
    awaiting_scrutiny = Application.objects.filter(status='SUBMITTED').order_by('submitted_at')
    assigned_to_me = Application.objects.filter(assigned_officer=user, status='IN_SCRUTINY').order_by('-submitted_at')
    deficiency_queue = Application.objects.filter(status='DEFICIENCY_FLAGGED').order_by('-updated_at')
    overdue_apps = Application.objects.filter(
        status__in=['SUBMITTED', 'IN_SCRUTINY'],
        created_at__lte=seven_days_ago
    ).order_by('created_at')

    # Base query based on selected queue
    if queue_filter == 'awaiting':
        all_apps = Application.objects.filter(status='SUBMITTED').order_by('submitted_at')
    elif queue_filter == 'assigned':
        all_apps = Application.objects.filter(assigned_officer=user, status='IN_SCRUTINY').order_by('-submitted_at')
    elif queue_filter == 'deficiency':
        all_apps = Application.objects.filter(status='DEFICIENCY_FLAGGED').order_by('-updated_at')
    elif queue_filter == 'overdue':
        all_apps = Application.objects.filter(
            status__in=['SUBMITTED', 'IN_SCRUTINY'],
            created_at__lte=seven_days_ago
        ).order_by('created_at')
    else:
        all_apps = Application.objects.all().order_by('-created_at')

    if status_filter:
        all_apps = all_apps.filter(status=status_filter)
    if search_query:
        all_apps = all_apps.filter(
            Q(application_number__icontains=search_query) |
            Q(institution_name__icontains=search_query)
        )

    total_filtered = all_apps.count()

    paginator = Paginator(all_apps, 10)
    page_number = request.GET.get('page', 1)
    try:
        applications_page = paginator.page(page_number)
    except PageNotAnInteger:
        applications_page = paginator.page(1)
    except EmptyPage:
        applications_page = paginator.page(paginator.num_pages)

    context = {
        'applications': applications_page,
        'page_obj': applications_page,
        'total_filtered': total_filtered,
        'awaiting_scrutiny': awaiting_scrutiny,
        'assigned_to_me': assigned_to_me,
        'deficiency_queue': deficiency_queue,
        'overdue_apps': overdue_apps,
        'total_awaiting': awaiting_scrutiny.count(),
        'total_assigned': assigned_to_me.count(),
        'total_deficiencies': deficiency_queue.count(),
        'total_overdue': overdue_apps.count(),
        'total_all': Application.objects.count(),
        'queue_filter': queue_filter,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'applications/officer_dashboard.html', context)


@login_required
@scrutiny_officer_required
def officer_review(request, pk):
    """Detailed scrutiny review console for officers."""
    application = get_object_or_404(Application, pk=pk)
    allowed_actions = WorkflowEngine.ALLOWED_TRANSITIONS.get(application.status, [])

    if request.method == 'POST':
        form = OfficerReviewActionForm(request.POST, allowed_actions=allowed_actions)
        if form.is_valid():
            new_status = form.cleaned_data['action']
            comments = form.cleaned_data['comments']

            try:
                WorkflowEngine.transition(
                    application=application,
                    new_status=new_status,
                    user=request.user,
                    comments=comments,
                    action_type='OFFICER_REVIEW_DECISION'
                )
                messages.success(request, f"Application {application.application_number} transitioned to {application.get_status_display()}.")
                return redirect('officer_dashboard')
            except Exception as e:
                messages.error(request, f"Error updating status: {str(e)}")
    else:
        form = OfficerReviewActionForm(allowed_actions=allowed_actions)

    documents = application.documents.all().order_by('-uploaded_at')
    compliance_results = application.compliance_results.all()
    history = application.history.all()
    institution = application.institution

    context = {
        'application': application,
        'institution': institution,
        'documents': documents,
        'compliance_results': compliance_results,
        'history': history,
        'form': form,
    }
    return render(request, 'applications/officer_review.html', context)


@login_required
@regional_director_required
def director_dashboard(request):
    """Executive Analytics Dashboard for Regional Directors and System Administrators."""
    all_apps = Application.objects.all()

    total_apps = all_apps.count()
    draft_count = all_apps.filter(status='DRAFT').count()
    submitted_count = all_apps.filter(status='SUBMITTED').count()
    in_scrutiny_count = all_apps.filter(status='IN_SCRUTINY').count()
    deficiency_count = all_apps.filter(status='DEFICIENCY_FLAGGED').count()
    approved_count = all_apps.filter(status='APPROVED').count()
    rejected_count = all_apps.filter(status='REJECTED').count()

    seven_days_ago = timezone.now() - timedelta(days=7)
    overdue_count = all_apps.filter(status__in=['SUBMITTED', 'IN_SCRUTINY'], created_at__lte=seven_days_ago).count()

    # Officer Workload Distribution
    officers = User.objects.filter(profile__role='OFFICER')
    officer_workloads = []
    for off in officers:
        assigned = Application.objects.filter(assigned_officer=off).count()
        in_progress = Application.objects.filter(assigned_officer=off, status='IN_SCRUTINY').count()
        completed = Application.objects.filter(assigned_officer=off, status__in=['APPROVED', 'REJECTED']).count()
        officer_workloads.append({
            'officer': off,
            'assigned': assigned,
            'in_progress': in_progress,
            'completed': completed,
        })

    # Recent applications list
    recent_apps = all_apps.order_by('-created_at')[:10]

    context = {
        'total_apps': total_apps,
        'draft_count': draft_count,
        'submitted_count': submitted_count,
        'in_scrutiny_count': in_scrutiny_count,
        'deficiency_count': deficiency_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'overdue_count': overdue_count,
        'officer_workloads': officer_workloads,
        'recent_apps': recent_apps,
    }
    return render(request, 'applications/director_dashboard.html', context)


def chatbot_api_view(request):
    """REST API endpoint for the AICTE Help Centre Chatbot."""
    query = request.GET.get('q', '').strip() or request.POST.get('q', '').strip()
    if not query:
        return JsonResponse({
            'found': False,
            'answer': 'Please enter a question regarding AICTE application procedures, required documents, or status meanings.'
        })

    result = search_faq(query)
    return JsonResponse(result)