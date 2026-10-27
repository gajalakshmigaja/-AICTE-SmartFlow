from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from applications.models import Application
from .models import ComplianceRule, ComplianceResult
from .forms import ComplianceRuleForm
from .services import ComplianceEngine
from accounts.decorators import role_required


@login_required
@require_POST
def run_compliance_view(request, app_id):
    application = get_object_or_404(Application, pk=app_id)
    profile = getattr(request.user, 'profile', None)
    is_reviewer = request.user.is_superuser or (
        profile and profile.role in ['OFFICER', 'DIRECTOR', 'ADMIN']
    )
    if application.applicant_id != request.user.id and not is_reviewer:
        messages.error(request, "You are not authorized to evaluate this application.")
        return redirect('dashboard')

    results = ComplianceEngine.evaluate_application(application)

    from audit.services import log_activity
    log_activity(
        actor=request.user,
        action='COMPLIANCE_RUN',
        target_model='Application',
        target_id=application.application_number,
        summary=f"Automated compliance evaluation executed for {application.application_number}",
        details={'checks_count': len(results)},
        request=request
    )

    messages.success(request, f"Compliance evaluation completed for {application.application_number}. {len(results)} rules evaluated.")

    if request.user == application.applicant:
        return redirect('application_detail', pk=application.id)
    return redirect('officer_review', pk=application.id)


@login_required
@role_required(['DIRECTOR', 'ADMIN'])
def rules_list_view(request):
    rules = ComplianceRule.objects.all().order_by('category', 'rule_code')
    return render(request, 'compliance/rules_list.html', {'rules': rules})


@login_required
@role_required(['DIRECTOR', 'ADMIN'])
def rule_create_view(request):
    if request.method == 'POST':
        form = ComplianceRuleForm(request.POST)
        if form.is_valid():
            rule = form.save()
            messages.success(request, f"Compliance rule '{rule.name}' created.")
            return redirect('compliance_rules')
    else:
        form = ComplianceRuleForm()

    return render(request, 'compliance/rule_edit.html', {
        'form': form,
        'rule': None,
        'is_create': True,
    })


@login_required
@role_required(['DIRECTOR', 'ADMIN'])
def rule_edit_view(request, pk):
    rule = get_object_or_404(ComplianceRule, pk=pk)
    if request.method == 'POST':
        form = ComplianceRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, f"Compliance rule '{rule.name}' updated successfully.")
            return redirect('compliance_rules')
    else:
        form = ComplianceRuleForm(instance=rule)

    return render(request, 'compliance/rule_edit.html', {'form': form, 'rule': rule})


@login_required
@role_required(['ADMIN'])
@require_POST
def seed_rules_view(request):
    messages.info(
        request,
        "No regulatory defaults are preloaded. Add a rule with its verified source and effective date; "
        "unverified rules remain available for manual review only."
    )
    return redirect('compliance_rules')
