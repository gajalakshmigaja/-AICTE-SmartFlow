from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import AuditLog
from accounts.decorators import role_required


@login_required
@role_required(['DIRECTOR', 'ADMIN'])
def audit_log_list_view(request):
    action_filter = request.GET.get('action', '')
    search_query = request.GET.get('q', '')

    logs = AuditLog.objects.all()
    if action_filter:
        logs = logs.filter(action=action_filter)
    if search_query:
        logs = logs.filter(summary__icontains=search_query) | logs.filter(target_id__icontains=search_query)

    logs = logs[:100]

    return render(request, 'audit/audit_log.html', {
        'logs': logs,
        'action_choices': AuditLog.ACTION_CHOICES,
        'selected_action': action_filter,
        'search_query': search_query,
    })
