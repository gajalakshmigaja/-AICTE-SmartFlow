from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Notification


@login_required
def notification_list_view(request):
    notifications = request.user.notifications.all()
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications
    })


@login_required
@require_POST
def mark_read_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()

    if notif.action_url and url_has_allowed_host_and_scheme(
        notif.action_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(notif.action_url)
    return redirect('notifications_list')


@login_required
@require_POST
def mark_all_read_view(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications_list')
