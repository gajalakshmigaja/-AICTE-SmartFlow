from .models import AuditLog


def get_client_ip(request):
    if not request:
        return ""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def sanitize_audit_details(details):
    """Prevents logging passwords, tokens, or security keys."""
    if not isinstance(details, dict):
        return {}

    sanitized = {}
    sensitive_keys = {'password', 'confirm_password', 'token', 'secret', 'secret_key', 'csrfmiddlewaretoken'}
    for k, v in details.items():
        if k.lower() in sensitive_keys:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_details(v)
        else:
            sanitized[k] = str(v)[:255]
    return sanitized


def log_activity(actor, action, target_model='', target_id='', summary='', details=None, request=None):
    """Records an immutable audit trail entry."""
    ip_addr = get_client_ip(request)
    cleaned_details = sanitize_audit_details(details or {})

    # If actor is anonymous, set to None
    actor_user = actor if (actor and actor.is_authenticated) else None

    return AuditLog.objects.create(
        actor=actor_user,
        action=action,
        target_model=target_model,
        target_id=str(target_id),
        summary=summary,
        ip_address=ip_addr,
        details=cleaned_details
    )
