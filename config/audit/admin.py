from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'target_model', 'target_id', 'ip_address', 'timestamp')
    list_filter = ('action', 'target_model', 'timestamp')
    search_fields = ('summary', 'target_id', 'actor__username', 'ip_address')
    readonly_fields = ('actor', 'action', 'target_model', 'target_id', 'summary', 'ip_address', 'details', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
