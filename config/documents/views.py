import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_POST

from applications.models import Application
from .models import ApplicationDocument, AIDocumentAnalysis
from .forms import DocumentUploadForm, DocumentReplacementForm, DocumentVerificationForm
from .ai_service import analyze_document_content


def can_access_document(user, document):
    """
    Checks if a user is allowed to access/download a document.
    Allowed: Document's application applicant, assigned officer, scrutiny officer, regional director, admin.
    """
    if user.is_superuser:
        return True
    if document.application.applicant == user:
        return True
    profile = getattr(user, 'profile', None)
    if profile and profile.role in ['OFFICER', 'DIRECTOR', 'ADMIN']:
        return True
    return False


@login_required
def upload_document_view(request, app_id):
    application = get_object_or_404(Application, pk=app_id)

    # Permission check: applicant or admin
    if not (request.user == application.applicant or request.user.is_superuser):
        messages.error(request, "You are not authorized to upload documents for this application.")
        return redirect('application_detail', pk=application.id)

    if not application.can_edit:
        messages.error(request, "Documents cannot be added while the application is in scrutiny or finalized.")
        return redirect('application_detail', pk=application.id)

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.application = application
            doc.uploaded_by = request.user
            doc.save()

            analyze_document_content(doc)

            from audit.services import log_activity
            log_activity(
                actor=request.user,
                action='DOCUMENT_UPLOAD',
                target_model='ApplicationDocument',
                target_id=str(doc.id),
                summary=f"Uploaded {doc.get_document_type_display()} for {application.application_number}",
                request=request
            )

            messages.success(request, f"Document '{doc.title}' uploaded successfully.")
            return redirect('application_detail', pk=application.id)
    else:
        form = DocumentUploadForm()

    return render(request, 'documents/upload_document.html', {
        'form': form,
        'application': application,
    })


@login_required
def replace_document_view(request, doc_id):
    document = get_object_or_404(ApplicationDocument, pk=doc_id)
    application = document.application

    if not (request.user == application.applicant or request.user.is_superuser):
        messages.error(request, "You are not authorized to replace this document.")
        return redirect('application_detail', pk=application.id)

    if not application.can_edit:
        messages.error(request, "Documents can only be replaced while the application is a draft or has flagged deficiencies.")
        return redirect('application_detail', pk=application.id)

    if request.method == 'POST':
        form = DocumentReplacementForm(request.POST, request.FILES)
        if form.is_valid():
            new_file = form.cleaned_data['file']
            expiry = form.cleaned_data.get('expiry_date')

            document.file = new_file
            document.expiry_date = expiry
            document.version += 1
            document.verification_status = 'PENDING'
            document.reviewer_comments = ''
            document.uploaded_at = timezone.now()
            document.uploaded_by = request.user
            document.file_hash = ''
            document.file_size = 0
            document.verified_by = None
            document.verified_at = None
            document.save()

            analysis = getattr(document, 'ai_analysis', None)
            if analysis:
                analysis.human_verified = False
                analysis.human_verdict = ''
                analysis.reviewer_notes = ''
                analysis.save(update_fields=['human_verified', 'human_verdict', 'reviewer_notes'])
            analyze_document_content(document)

            from audit.services import log_activity
            log_activity(
                actor=request.user,
                action='DOCUMENT_REPLACE',
                target_model='ApplicationDocument',
                target_id=str(document.id),
                summary=f"Replaced {document.get_document_type_display()} (v{document.version})",
                request=request
            )

            messages.success(request, f"Replacement document for '{document.title}' uploaded (Version {document.version}).")
            return redirect('application_detail', pk=application.id)
    else:
        form = DocumentReplacementForm(instance=document)

    return render(request, 'documents/replace_document.html', {
        'form': form,
        'document': document,
        'application': application,
    })


@login_required
@require_POST
def verify_document_view(request, doc_id):
    document = get_object_or_404(ApplicationDocument, pk=doc_id)
    profile = getattr(request.user, 'profile', None)

    is_reviewer = request.user.is_superuser or (profile and profile.role in ['OFFICER', 'DIRECTOR', 'ADMIN'])
    if not is_reviewer:
        messages.error(request, "Only authorized scrutiny officers can verify documents.")
        return redirect('application_detail', pk=document.application.id)

    if request.method == 'POST':
        form = DocumentVerificationForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['verification_status']
            comments = form.cleaned_data['reviewer_comments']

            document.verification_status = status
            document.reviewer_comments = comments
            document.verified_by = request.user
            document.verified_at = timezone.now()
            document.save()

            from audit.services import log_activity
            log_activity(
                actor=request.user,
                action='DOCUMENT_VERIFIED',
                target_model='ApplicationDocument',
                target_id=str(document.id),
                summary=f"Verified {document.title} as {status}",
                details={'status': status, 'comments': comments},
                request=request
            )

            messages.success(request, f"Verification recorded for {document.title}: {document.get_verification_status_display()}.")
            return redirect('officer_review', pk=document.application.id)

    return redirect('officer_review', pk=document.application.id)


@login_required
def download_document_view(request, doc_id):
    document = get_object_or_404(ApplicationDocument, pk=doc_id)

    if not can_access_document(request.user, document):
        return HttpResponseForbidden("Access Denied: You do not have permission to view or download this document.")

    if not document.file:
        raise Http404("Document file not found on server storage.")

    try:
        file_handle = document.file.open('rb')
    except FileNotFoundError as error:
        raise Http404("Document file not found on server storage.") from error
    return FileResponse(file_handle, as_attachment=False, filename=os.path.basename(document.file.name))


@login_required
@require_POST
def run_ai_analysis_view(request, doc_id):
    document = get_object_or_404(ApplicationDocument, pk=doc_id)
    profile = getattr(request.user, 'profile', None)

    is_reviewer = request.user.is_superuser or (profile and profile.role in ['OFFICER', 'DIRECTOR', 'ADMIN']) or (document.application.applicant == request.user)
    if not is_reviewer:
        messages.error(request, "Permission denied.")
        return redirect('application_detail', pk=document.application.id)

    analyze_document_content(document)
    messages.success(request, f"AI-assisted analysis completed for '{document.title}'.")

    if request.user == document.application.applicant:
        return redirect('application_detail', pk=document.application.id)
    return redirect('officer_review', pk=document.application.id)


@login_required
@require_POST
def verify_ai_finding_view(request, doc_id):
    document = get_object_or_404(ApplicationDocument, pk=doc_id)
    profile = getattr(request.user, 'profile', None)
    is_reviewer = request.user.is_superuser or (
        profile and profile.role in ['OFFICER', 'DIRECTOR', 'ADMIN']
    )
    if not is_reviewer:
        messages.error(request, "Only authorized scrutiny officers can verify AI findings.")
        return redirect('application_detail', pk=document.application.id)

    analysis = getattr(document, 'ai_analysis', None)

    if not analysis:
        messages.error(request, "No AI analysis found for this document.")
        return redirect('officer_review', pk=document.application.id)

    verdict = request.POST.get('verdict', '')
    allowed_verdicts = {'CONFIRMED', 'REJECTED', 'MODIFIED'}
    if verdict not in allowed_verdicts:
        messages.error(request, "Select a valid human review verdict.")
        return redirect('officer_review', pk=document.application.id)

    notes = request.POST.get('reviewer_notes', '').strip()
    if len(notes) > 5000:
        messages.error(request, "Reviewer notes must be 5,000 characters or fewer.")
        return redirect('officer_review', pk=document.application.id)

    if verdict:
        analysis.human_verified = True
        analysis.human_verdict = verdict
        analysis.reviewer_notes = notes
        analysis.save()

        messages.success(request, f"Human verification saved for AI finding: {verdict}.")

    return redirect('officer_review', pk=document.application.id)
